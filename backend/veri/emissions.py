"""Freight emissions and cost per shipment leg, ISO 14083 style (tonne-km x intensity).

INDICATIVE factors: well-to-wheel kgCO2e per tonne-km in the range of published
defaults (GLEC Framework / national conversion factors). Replace with the GLEC
v3.x default table before any customer use. Costs are illustrative THB rates.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import Network, haversine_km

# kgCO2e per tonne-km, well-to-wheel (indicative).
WTW_FACTOR = {
    "road_truck": 0.11,
    "rail_freight": 0.03,
    "sea_container": 0.016,
    "air_cargo": 1.10,
}
# Illustrative freight cost, THB per tonne-km, plus fixed handling per tonne.
COST_PER_TKM = {"road_truck": 4.0, "rail_freight": 2.0, "sea_container": 0.8, "air_cargo": 60.0}
HANDLING_PER_T = {"road_truck": 150.0, "rail_freight": 300.0, "sea_container": 1200.0, "air_cargo": 6000.0}
# Network circuity: actual route distance / great-circle distance.
CIRCUITY = {"road_truck": 1.3, "rail_freight": 1.25, "sea_container": 1.0, "air_cargo": 1.05}
# Known sea distances that great-circle badly underestimates (around the Malay peninsula).
SEA_DISTANCE_KM = {  # approximate port-to-port sailing distances
    ("A-RESIN-PEN", "X-LCB-PORT"): 2050.0,
    ("A-SWITCH-PEN", "X-LCB-PORT"): 2050.0,
    ("A-FABRIC-BD", "X-LCB-PORT"): 1200.0,
}
FACTOR_SOURCE = "indicative WTW defaults (replace with GLEC v3 table)"


@dataclass
class Leg:
    origin: str
    dest: str
    mode: str
    distance_km: float

    def tonne_km(self, tonnes: float) -> float:
        return tonnes * self.distance_km


def leg(net: Network, origin: str, dest: str, mode: str) -> Leg:
    if mode == "sea_container" and (origin, dest) in SEA_DISTANCE_KM:
        d = SEA_DISTANCE_KM[(origin, dest)]
    else:
        d = haversine_km(net.sites[origin], net.sites[dest]) * CIRCUITY[mode]
    return Leg(origin, dest, mode, round(d, 1))


def route(net: Network, origin: str, plant: str, mode: str, via: str | None) -> list[Leg]:
    """Main-haul leg (via port/airport if given) plus road delivery to the plant."""
    if via:
        return [leg(net, origin, via, mode), leg(net, via, plant, "road_truck")]
    return [leg(net, origin, plant, mode)]


def co2_kg(legs: list[Leg], tonnes: float) -> float:
    return sum(l.tonne_km(tonnes) * WTW_FACTOR[l.mode] for l in legs)


def freight_cost_thb(legs: list[Leg], tonnes: float) -> float:
    return sum(l.tonne_km(tonnes) * COST_PER_TKM[l.mode] + tonnes * HANDLING_PER_T[l.mode] for l in legs)
