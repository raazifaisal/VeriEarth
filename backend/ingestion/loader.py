from typing import Dict, Any, List
from sqlalchemy.orm import Session
from services.supply_chain_service import SupplyChainService
from db.neo4j_service import Neo4jService
from db.supply_chain_schemas import FacilityCreate, RouteCreate, ShipmentCreate
from db.models import FacilityEnvironmentalData
from ingestion.transformers import enrich_facility_with_eo_data
from datetime import datetime


def load_facilities(rows: List[Dict[str, Any]], db: Session, neo4j: Neo4jService, org_id: str) -> int:
    svc = SupplyChainService(db=db, neo4j=neo4j, organization_id=org_id)
    created = 0
    for r in rows:
        # Infer facility type from name if not provided
        facility_type = r.get("type")
        if not facility_type:
            name_lower = r["name"].lower()
            
            # Retail/Outlet facilities
            if any(keyword in name_lower for keyword in [
                "restaurant", "outlet", "store", "shop", "showroom", "retail", 
                "branch", "franchise", "market", "mall", "center", "centre"
            ]):
                facility_type = "retail"
            
            # Distribution/Logistics facilities  
            elif any(keyword in name_lower for keyword in [
                "distribution", "hub", "logistics", "depot", "terminal", 
                "freight", "cargo", "shipping"
            ]):
                facility_type = "distribution_center"
            
            # Storage/Warehouse facilities
            elif any(keyword in name_lower for keyword in [
                "storage", "warehouse", "cold storage", "refrigerated", 
                "inventory", "stock", "depot"
            ]):
                facility_type = "warehouse"
            
            # Manufacturing/Production facilities
            elif any(keyword in name_lower for keyword in [
                "factory", "plant", "manufacturing", "production", "assembly", 
                "processing", "packaging", "kitchen", "central kitchen"
            ]):
                facility_type = "manufacturing"
            
            else:
                facility_type = "manufacturing"  # default for unknown
        
        payload = FacilityCreate(
            name=r["name"],
            facility_type=facility_type,
            latitude=float(r.get("latitude", 0) or 0),
            longitude=float(r.get("longitude", 0) or 0),
            address=r.get("address"),
            city=r.get("city"),
            country=r["country"],
            capacity_tons=float(r.get("capacity_tons") or 0) if r.get("capacity_tons") else None,
        )
        svc.create_facility(payload)
        created += 1
    return created


def load_routes(rows: List[Dict[str, Any]], db: Session, neo4j: Neo4jService, org_id: str) -> int:
    svc = SupplyChainService(db=db, neo4j=neo4j, organization_id=org_id)
    created = 0
    for r in rows:
        payload = RouteCreate(
            origin_facility_id=r["origin_facility_id"],
            destination_facility_id=r["destination_facility_id"],
            transport_mode=r["transport_mode"],
            distance_km=float(r.get("distance_km") or 0),
            duration_hours=float(r.get("duration_hours") or 0) if r.get("duration_hours") else None,
            intermediate_stops=None,
        )
        svc.create_route(payload)
        created += 1
    return created


def load_shipments(rows: List[Dict[str, Any]], db: Session, neo4j: Neo4jService, org_id: str) -> int:
    svc = SupplyChainService(db=db, neo4j=neo4j, organization_id=org_id)
    created = 0
    for r in rows:
        payload = ShipmentCreate(
            route_id=r.get("route_id", ""),
            weight_kg=float(r["weight_kg"]),
            volume_m3=float(r.get("volume_m3") or 0) if r.get("volume_m3") else None,
            total_cost=float(r.get("total_cost") or 0),
            emissions_per_kg=float(r.get("emissions_per_kg") or 0) if r.get("emissions_per_kg") else None,
            total_emissions_kg_co2=float(r.get("total_emissions_kg_co2") or 0),
            shipment_date=r.get("pickup_date"),
            planned_delivery_date=r.get("delivery_date"),
            carrier=r.get("carrier"),
        )
        svc.create_shipment(payload)
        created += 1
    return created


