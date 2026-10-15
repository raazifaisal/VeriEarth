"""Supply network model: sites, parts, products, supplies, alternates, orders."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

DATA_DIR = Path(__file__).parent / "data"


@dataclass
class Site:
    id: str
    name: str
    kind: str  # own_plant | supplier | customer | port | airport
    lat: float
    lon: float
    estate: str = ""
    tier: int | None = None
    category: str = ""
    alternate: bool = False
    overseas: bool = False


@dataclass
class Part:
    id: str
    name: str
    unit: str
    unit_cost_thb: float
    unit_weight_kg: float


@dataclass
class Product:
    id: str
    name: str
    plant: str
    daily_rate: float
    unit_price_thb: float
    bom: dict[str, float]  # part id -> qty per product unit


@dataclass
class Supply:
    supplier: str
    part: str
    plant: str
    share: float
    inventory_days: float
    alternates: list[str] = field(default_factory=list)


@dataclass
class AlternateTerm:
    supplier: str
    part: str
    max_share_of_demand: float
    lead_days: float
    price_premium: float
    mode: str
    via: str | None = None


@dataclass
class Order:
    id: str
    customer: str
    product: str
    qty: float
    due_offset_days: int


@dataclass
class Network:
    meta: dict
    company: dict
    sites: dict[str, Site]
    parts: dict[str, Part]
    products: dict[str, Product]
    supplies: list[Supply]
    alternate_terms: list[AlternateTerm]
    orders: list[Order]

    @property
    def horizon_days(self) -> int:
        return int(self.meta.get("horizon_days", 28))

    def suppliers(self) -> list[Site]:
        return [s for s in self.sites.values() if s.kind == "supplier" and not s.alternate]

    def part_demand_per_day(self, plant: str, part: str) -> float:
        """Units of `part` consumed per day at `plant` at planned production rates."""
        return sum(p.daily_rate * p.bom.get(part, 0.0) for p in self.products.values() if p.plant == plant)

    def graph(self) -> nx.DiGraph:
        """Directed dependency graph: supplier -> plant -> customer, with part and product edges."""
        g = nx.DiGraph()
        for s in self.sites.values():
            g.add_node(s.id, kind=s.kind, name=s.name)
        for sp in self.supplies:
            g.add_edge(sp.supplier, sp.plant, part=sp.part, kind="supplies")
            for alt in sp.alternates:
                g.add_edge(alt, sp.plant, part=sp.part, kind="alternate")
        for o in self.orders:
            plant = self.products[o.product].plant
            g.add_edge(plant, o.customer, product=o.product, kind="delivers")
        return g


def haversine_km(a: Site, b: Site) -> float:
    r = 6371.0
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lon - a.lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def load_network(path: Path | str = DATA_DIR / "network_th.json") -> Network:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    sites = {s["id"]: Site(**{k: v for k, v in s.items() if k in Site.__dataclass_fields__}) for s in raw["sites"]}
    parts = {p["id"]: Part(**p) for p in raw["parts"]}
    products = {
        p["id"]: Product(
            id=p["id"], name=p["name"], plant=p["plant"], daily_rate=p["daily_rate"],
            unit_price_thb=p["unit_price_thb"], bom={b["part"]: b["qty"] for b in p["bom"]},
        )
        for p in raw["products"]
    }
    supplies = [Supply(**s) for s in raw["supplies"]]
    alts = [AlternateTerm(**a) for a in raw.get("alternate_terms", [])]
    orders = [Order(**o) for o in raw["orders"]]
    net = Network(raw["meta"], raw["company"], sites, parts, products, supplies, alts, orders)
    _validate(net)
    return net


def _validate(net: Network) -> None:
    for sp in net.supplies:
        assert sp.supplier in net.sites, sp.supplier
        assert sp.plant in net.sites, sp.plant
        assert sp.part in net.parts, sp.part
        for a in sp.alternates:
            assert a in net.sites, a
    for p in net.products.values():
        assert p.plant in net.sites, p.plant
        for part in p.bom:
            assert part in net.parts, part
            assert any(s.part == part and s.plant == p.plant for s in net.supplies), (p.id, part)
    for o in net.orders:
        assert o.product in net.products and o.customer in net.sites, o.id
