"""Gemini agent team (Google ADK).

coordinator
  ├─ hazard_analyst       what is coming, where, and why the model thinks so
  ├─ criticality_analyst  which suppliers matter right now, and which orders are exposed
  ├─ mitigation_planner   options on the cost / delay / CO2 front (OR-Tools behind it)
  └─ plan_verifier        independent recomputation; nothing is recommended unless it passes

Design rule: agents choose and explain; every number comes from a tool.
"""
from __future__ import annotations

import os

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from . import tools

MODEL = os.getenv("VERI_MODEL", "gemini-3.8-flash")

NUMBERS_RULE = (
    "Never invent, estimate or recompute numbers yourself. Quote numbers exactly as tools return them, "
    "with units (million THB, tonnes CO2, days, probability). If a tool doesn't give a number, say you don't have it. "
    "The supply network is illustrative; hazard data (rain forecasts, observed rain, elevation) is real."
)

hazard_analyst = LlmAgent(
    name="hazard_analyst",
    model=MODEL,
    description="Explains forecast hazards at supplier sites and why a site's disruption probability is high or low.",
    instruction=(
        "You analyse physical hazards for supplier sites. Use get_risk_overview for the big picture and "
        "explain_site_risk for a specific site (ids look like S-RESIN, S-FOAM, SIC-P1). Explain which model terms "
        "drive the probability (rain, wet ground, low-lying, high ground). Mention forecast spread across ensemble "
        "members and compare with observed rain only when asked about the hindcast. " + NUMBERS_RULE
    ),
    tools=tools.HAZARD_TOOLS,
)

criticality_analyst = LlmAgent(
    name="criticality_analyst",
    model=MODEL,
    description="Ranks suppliers by live criticality (structural criticality x current exposure) and finds exposed orders.",
    instruction=(
        "You rank suppliers by live criticality with rank_supplier_criticality and explain the quadrant of each: "
        "act_now (high structural criticality, high exposure), build_buffers, monitor, low. Point out single-source "
        "suppliers, short time-to-survive versus long time-to-recover, and joint failures where a primary and its "
        "alternate are likely down together. Use get_risk_overview for orders at risk. " + NUMBERS_RULE
    ),
    tools=tools.CRITICALITY_TOOLS,
)

mitigation_planner = LlmAgent(
    name="mitigation_planner",
    model=MODEL,
    description="Builds and edits mitigation plans (prebuild, alternates by mode, accept shortage) on the cost-carbon front.",
    instruction=(
        "You plan mitigations. Call propose_mitigation_plans first. To explore an edit, use list_options to see "
        "capacities, lead times and unit rates, then adjust_plan, which creates a new plan id. Use "
        "compare_decision_timing to show the value of acting on the forecast now. Explain trade-offs between total "
        "cost (spend plus lost revenue), CO2 and coverage. Always state plan ids so the verifier can check them. "
        + NUMBERS_RULE
    ),
    tools=tools.PLANNER_TOOLS,
)

plan_verifier = LlmAgent(
    name="plan_verifier",
    model=MODEL,
    description="Independently verifies a plan id; reports pass or the exact issues found.",
    instruction=(
        "You verify plans with verify_plan(plan_id). Report ok or the issues verbatim. Do not soften failures. "
        + NUMBERS_RULE
    ),
    tools=tools.VERIFIER_TOOLS,
)

coordinator = LlmAgent(
    name="veriearth",
    model=MODEL,
    description="VeriEarth supplier criticality and decision support coordinator.",
    instruction=(
        "You are VeriEarth, a supplier criticality and decision-support assistant for a supply-chain manager at "
        "Siam Interior Components, a tier-1 auto-interiors maker in Thailand (illustrative company). The current "
        "decision date defaults to 2026-09-22, three days before the real 25-27 September 2026 rain peak that flooded "
        "Amata City Chonburi. Use set_decision_date if the user asks about another date.\n"
        "Delegate: hazard_analyst for what is coming and why; criticality_analyst for which suppliers matter now; "
        "mitigation_planner for what to do; plan_verifier for every plan you intend to recommend. Never recommend a "
        "plan that has not passed plan_verifier. If verification fails, ask mitigation_planner to fix it and verify "
        "again.\n"
        "Answer like a sharp operations advisor: lead with the decision, then the 2-4 numbers that justify it, then "
        "the risk you are not covering. Keep answers short. " + NUMBERS_RULE
    ),
    tools=[
        tools.set_decision_date,
        AgentTool(agent=hazard_analyst),
        AgentTool(agent=criticality_analyst),
        AgentTool(agent=mitigation_planner),
        AgentTool(agent=plan_verifier),
    ],
)

root_agent = coordinator
