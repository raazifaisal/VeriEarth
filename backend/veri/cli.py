"""Command line: run the hindcast and print what VeriEarth would have shown.

    python -m veri.cli hindcast --as-of 2026-09-22
"""
from __future__ import annotations

import argparse
from datetime import date

from . import engine


def _thb(x: float) -> str:
    return f"THB {x / 1e6:,.1f}M"


def hindcast(as_of: date) -> None:
    a = engine.assess(as_of)
    ov = engine.overview(a)
    rr = ov["revenue_at_risk"]
    print(f"\n== VeriEarth hindcast, decision date {a.as_of} ({ov['company']}, illustrative network) ==")
    print(f"Hazard source: {a.snap.source}")
    print(f"Revenue at risk over {ov['horizon_days']} days: expected {_thb(rr['expected_revenue_at_risk_thb'])}, "
          f"P90 {_thb(rr['p90_thb'])}, P(any loss) {rr['p_any_loss']:.0%}; warning ~{ov['warning_days']:.0f} days")

    print("\nSupplier criticality (live = structural x exposure):")
    print(f"  {'supplier':<26}{'quadrant':<15}{'P(down)':>8}{'TTR p50':>9}{'TTS':>5}{'structural':>14}{'live E[RaR]':>14}")
    for r in a.criticality():
        print(f"  {r['name'][:25]:<26}{r['quadrant']:<15}{r['exposure_p_down']:>8.2f}{r['median_downtime_days']:>8.1f}d"
              f"{r['time_to_survive_days']:>4.0f}d{_thb(r['structural_rar_thb']):>14}{_thb(r['live_expected_rar_thb']):>14}")

    print("\nOrders at risk:")
    for o in ov["orders"]:
        print(f"  {o['id']:<14} {o['customer']:<18} due {o['due']}  P(late) {o['p_late']:.0%}")
    for j in ov["joint_failure"]:
        print(f"  joint: P({j['primary']} and alternate {j['alternate']} both down) = {j['p_both_down']:.2f}")

    print("\nPlans:")
    for p in a.plans:
        v = engine.verify_plan(a, p.to_dict())
        print(f"  [{p.name}] total {_thb(p.total_cost_thb)} (spend {_thb(p.purchase_and_freight_thb)}, "
              f"lost revenue {_thb(p.lost_revenue_thb)}), CO2 {p.co2_kg / 1000:,.1f} t, coverage {p.coverage:.0%}, "
              f"verifier {'PASS' if v['ok'] else 'FAIL ' + '; '.join(v['issues'])}")
        for key, allocs in p.lines.items():
            parts = ", ".join(f"{al.kind}:{al.supplier}/{al.mode} {al.units:,.0f}u" for al in allocs)
            print(f"      {key:<16} {parts}")

    t = engine.compare_timing(as_of)
    if t["decide_now"] and t["decide_after_event"]:
        n, l = t["decide_now"], t["decide_after_event"]
        print(f"\nDecide now vs after the event ({t['warning_days']:.0f} days later):")
        print(f"  now:   total {_thb(n['total_cost_thb'])}, CO2 {n['co2_kg'] / 1000:,.1f} t, coverage {n['coverage']:.0%}")
        print(f"  later: total {_thb(l['total_cost_thb'])}, CO2 {l['co2_kg'] / 1000:,.1f} t, coverage {l['coverage']:.0%}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hindcast")
    h.add_argument("--as-of", default=engine.DEFAULT_AS_OF.isoformat())
    args = ap.parse_args()
    if args.cmd == "hindcast":
        hindcast(date.fromisoformat(args.as_of))


if __name__ == "__main__":
    main()
