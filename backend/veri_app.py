"""VeriEarth API: supplier criticality and decision support.

Run locally:  uvicorn veri_app:app --reload --port 8080
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from veri import engine, planner, tools  # noqa: E402

app = FastAPI(title="VeriEarth API", version="0.2.0",
              description="Live supplier criticality and decision support from forecasts and satellites.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("VERI_CORS_ORIGINS", "http://localhost:3000").split(",")],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

AS_OF_RANGE = (date(2026, 9, 15), date(2026, 10, 10))


def _as_of(value: str | None) -> date:
    d = date.fromisoformat(value) if value else engine.DEFAULT_AS_OF
    if not AS_OF_RANGE[0] <= d <= AS_OF_RANGE[1]:
        raise HTTPException(400, f"as_of must be between {AS_OF_RANGE[0]} and {AS_OF_RANGE[1]} for the hindcast")
    return d


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "model": os.getenv("VERI_MODEL", "gemini-3.8-flash"),
            "gemini_configured": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                                      or os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))}


@app.get("/api/v1/assessment")
def assessment(as_of: str | None = None):
    a = engine.assess(_as_of(as_of))
    crit = {r["supplier"]: r for r in a.criticality()}
    sites = []
    for s in a.net.sites.values():
        h = a.snap.sites.get(s.id)
        sites.append({
            "id": s.id, "name": s.name, "kind": s.kind, "estate": s.estate, "lat": s.lat, "lon": s.lon,
            "alternate": s.alternate, "overseas": s.overseas, "category": s.category,
            "p_down": round(a.sim.site_p_down.get(s.id, 0.0), 3) if h else None,
            "elevation_m": h.elevation_m if h else None,
            "forecast_max3_mm": round(sorted(h.forecast_max3_by_member)[1]) if h else None,
            "quadrant": crit.get(s.id, {}).get("quadrant"),
        })
    edges = [{"from": sp.supplier, "to": sp.plant, "part": sp.part, "kind": "supplies"} for sp in a.net.supplies]
    edges += [{"from": alt, "to": sp.plant, "part": sp.part, "kind": "alternate"} for sp in a.net.supplies for alt in sp.alternates]
    edges += [{"from": a.net.products[o.product].plant, "to": o.customer, "product": o.product, "kind": "delivers"}
              for o in a.net.orders]
    return {"overview": engine.overview(a), "criticality": list(crit.values()), "sites": sites,
            "edges": [dict(t) for t in {tuple(sorted(e.items())) for e in edges}],
            "meta": a.net.meta, "hazard_source": a.snap.source}


@app.get("/api/v1/site/{site_id}")
def site(site_id: str, as_of: str | None = None):
    a = engine.assess(_as_of(as_of))
    if site_id not in a.snap.sites:
        raise HTTPException(404, "unknown or unmonitored site")
    return a.site_detail(site_id)


@app.get("/api/v1/plans")
def plans(as_of: str | None = None):
    d = _as_of(as_of)
    tools.set_decision_date(d.isoformat())
    out = tools.propose_mitigation_plans()
    for p in out["plans"]:
        p["verification"] = tools.verify_plan(p["plan_id"])
        p["detail"] = tools.get_plan(p["plan_id"])
    a = engine.assess(d)
    return {"plans": out["plans"], "timing": tools.compare_decision_timing(), "pareto": planner.pareto(a.net, a.sim)}


class VerifyRequest(BaseModel):
    plan_id: str


@app.post("/api/v1/plans/verify")
def verify(req: VerifyRequest):
    return tools.verify_plan(req.plan_id)


class AdjustRequest(BaseModel):
    plan_id: str
    part_at_plant: str
    option_key: str
    units: float


@app.post("/api/v1/plans/adjust")
def adjust(req: AdjustRequest):
    p = tools.adjust_plan(req.plan_id, req.part_at_plant, req.option_key, req.units)
    if "error" in p:
        raise HTTPException(400, p["error"])
    p["verification"] = tools.verify_plan(p["plan_id"])
    return p


# ---------- agents ----------
_runner = None
_sessions: set[str] = set()


def _get_runner():
    global _runner
    if _runner is None:
        from google.adk.runners import InMemoryRunner
        from veri.agents import root_agent
        _runner = InMemoryRunner(agent=root_agent, app_name="veriearth")
    return _runner


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    as_of: str | None = None


def _event_payloads(ev) -> list[dict]:
    out = []
    content = getattr(ev, "content", None)
    for part in (content.parts if content and content.parts else []):
        if getattr(part, "function_call", None):
            fc = part.function_call
            out.append({"type": "tool_call", "author": ev.author, "name": fc.name, "args": dict(fc.args or {})})
        elif getattr(part, "function_response", None):
            fr = part.function_response
            out.append({"type": "tool_result", "author": ev.author, "name": fr.name,
                        "result": json.loads(json.dumps(fr.response, default=str))})
        elif getattr(part, "text", None) and not getattr(part, "thought", False):
            out.append({"type": "text", "author": ev.author, "text": part.text,
                        "final": bool(ev.is_final_response())})
    return out


@app.post("/api/v1/agent/chat")
async def chat(req: ChatRequest):
    from google.genai import types

    runner = _get_runner()
    sid = req.session_id or uuid.uuid4().hex
    if sid not in _sessions:
        await runner.session_service.create_session(app_name="veriearth", user_id="demo", session_id=sid)
        _sessions.add(sid)
    tools.set_decision_date(_as_of(req.as_of).isoformat())
    msg = types.Content(role="user", parts=[types.Part(text=req.message)])

    async def stream():
        yield f"data: {json.dumps({'type': 'session', 'session_id': sid})}\n\n"
        try:
            async for ev in runner.run_async(user_id="demo", session_id=sid, new_message=msg):
                for p in _event_payloads(ev):
                    yield f"data: {json.dumps(p, default=str)}\n\n"
        except Exception as e:  # surface model/auth errors to the UI instead of hanging
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)[:500]})}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/v1/intake")
async def intake(file: UploadFile = File(...)):
    from veri import intake as ik

    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "file too large (max 8 MB)")
    mime = file.content_type or "application/octet-stream"
    if not (mime.startswith("image/") or mime == "application/pdf"):
        raise HTTPException(415, "upload an image or PDF")
    doc = ik.extract(data, mime)
    return {"document": doc.model_dump(), "link": ik.link_to_graph(doc)}
