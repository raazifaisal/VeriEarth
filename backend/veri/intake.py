"""Gemini multimodal intake: read a shipping or supplier document (photo or PDF, any language)
into structured data, then link it to a site in the supply graph.

Gemini only extracts text into a schema. Matching to the graph is deterministic.
"""
from __future__ import annotations

import difflib
import os

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from .model import load_network

INTAKE_MODEL = os.getenv("VERI_INTAKE_MODEL", "gemini-3.8-flash")


class LineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit: str | None = None
    weight_kg: float | None = None


class SupplyDocument(BaseModel):
    document_type: str = Field(description="bill_of_lading | commercial_invoice | delivery_note | utility_bill | other")
    language: str = Field(description="ISO 639-1 code of the document's main language")
    issuer_name: str | None = Field(None, description="Shipper, seller or utility, in Latin script if possible")
    issuer_name_original: str | None = Field(None, description="Issuer name exactly as written")
    recipient_name: str | None = None
    origin: str | None = None
    destination: str | None = None
    document_date: str | None = Field(None, description="YYYY-MM-DD; convert Buddhist-era years (BE - 543)")
    transport_mode: str | None = Field(None, description="road_truck | sea_container | air_cargo | rail_freight | unknown")
    gross_weight_kg: float | None = None
    electricity_kwh: float | None = Field(None, description="Only for utility bills")
    items: list[LineItem] = []
    notes: str | None = Field(None, description="Anything ambiguous or unreadable")


PROMPT = (
    "Extract this supply-chain document into the schema. Copy values exactly; do not guess missing numbers "
    "(leave them null). Translate company names to Latin script in issuer_name but keep the original in "
    "issuer_name_original. Thai dates may use the Buddhist era: subtract 543 from the year."
)


def _client() -> genai.Client:
    return genai.Client()  # reads GEMINI_API_KEY / GOOGLE_API_KEY, or Vertex settings from env


def extract(data: bytes, mime_type: str) -> SupplyDocument:
    resp = _client().models.generate_content(
        model=INTAKE_MODEL,
        contents=[types.Part.from_bytes(data=data, mime_type=mime_type), PROMPT],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=SupplyDocument),
    )
    return resp.parsed if isinstance(resp.parsed, SupplyDocument) else SupplyDocument.model_validate_json(resp.text)


def link_to_graph(doc: SupplyDocument) -> dict:
    """Deterministically match the issuer to a supplier site by name similarity."""
    net = load_network()
    names = {s.id: s.name.lower() for s in net.sites.values() if s.kind == "supplier"}
    query = (doc.issuer_name or "").lower()
    best = max(names.items(), key=lambda kv: difflib.SequenceMatcher(None, query, kv[1]).ratio(), default=None)
    score = difflib.SequenceMatcher(None, query, best[1]).ratio() if best else 0.0
    return {"matched_site": best[0] if best and score >= 0.55 else None, "match_score": round(score, 2)}
