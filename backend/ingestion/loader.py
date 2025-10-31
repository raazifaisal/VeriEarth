from typing import Dict, Any, List
from sqlalchemy.orm import Session
from services.supply_chain_service import SupplyChainService
from db.neo4j_service import Neo4jService
from db.supply_chain_schemas import FacilityCreate, RouteCreate, ShipmentCreate
from db.models import FacilityEnvironmentalData
from ingestion.transformers import enrich_facility_with_eo_data
from datetime import datetime
import uuid


def load_facilities(rows: List[Dict[str, Any]], db: Session, neo4j: Neo4jService, org_id: str) -> int:
    svc = SupplyChainService(db=db, neo4j=neo4j, organization_id=org_id)
    created = 0
    print(f"Processing {len(rows)} facility rows")
    for r in rows:
        print(f"Processing facility: {r.get('name', 'Unknown')} (ID: {r.get('facility_id', 'No ID')})")
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
            supplier_id=r.get("supplier_id") if r.get("supplier_id") else None,  # Add supplier_id if present
        )
        # Use original facility_id if available, otherwise let database generate UUID
        original_id = r.get("facility_id")
        facility = svc.create_facility(payload, custom_id=original_id)
        created += 1
        print(f"Created facility: {facility.id}")
    print(f"Total facilities created: {created}")
    return created


def load_routes(rows: List[Dict[str, Any]], db: Session, neo4j: Neo4jService, org_id: str) -> int:
    from db.models import Route
    created = 0
    
    for r in rows:
        try:
            route = Route(
                id=r.get("route_id") or str(uuid.uuid4()),
                organization_id=org_id,
                origin_facility_id=r["origin_facility_id"],
                destination_facility_id=r["destination_facility_id"],
                transport_mode=r["transport_mode"],
                distance_km=float(r.get("distance_km") or 0),
                duration_hours=float(r.get("duration_hours") or 0) if r.get("duration_hours") else None,
                intermediate_stops=None,
            )
            db.add(route)
            db.commit()
            created += 1
            
        except Exception as e:
            db.rollback()
            print(f"Error loading route: {e}")
            continue
    
    return created


def load_shipments(rows: List[Dict[str, Any]], db: Session, neo4j: Neo4jService, org_id: str) -> int:
    from db.models import Route, Shipment
    created = 0
    
    for r in rows:
        try:
            # Parse weight
            weight = r.get("weight_kg")
            if not weight:
                continue  # Skip if no weight provided
            
            origin_id = r.get("origin_facility_id", "")
            dest_id = r.get("destination_facility_id", "")
            transport_mode = r.get("transport_mode", "road_truck")
            distance_km = float(r.get("distance_km") or 100) if r.get("distance_km") else 100.0
            
            # Check if facilities exist, if not skip
            from db.models import Facility
            origin_facility = db.query(Facility).filter(Facility.id == origin_id).first() if origin_id else None
            dest_facility = db.query(Facility).filter(Facility.id == dest_id).first() if dest_id else None
            
            if not origin_facility or not dest_facility:
                # Skip shipment if facilities don't exist
                continue
            
            # Check if route exists, if not create it
            route = db.query(Route).filter(
                Route.origin_facility_id == origin_id,
                Route.destination_facility_id == dest_id
            ).first()
            
            if not route:
                # Create route
                route = Route(
                    organization_id=org_id,
                    origin_facility_id=origin_id,
                    destination_facility_id=dest_id,
                    transport_mode=transport_mode,
                    distance_km=distance_km,
                    duration_hours=float(r.get("duration_hours") or 0) if r.get("duration_hours") else None,
                )
                db.add(route)
                db.commit()
                db.refresh(route)
            
            # Calculate emissions if not provided: weight (tonnes) × distance × emission_factor
            total_emissions = None
            emission_factor_per_ton_km = None
            if r.get("total_emissions_kg_co2"):
                total_emissions = float(r["total_emissions_kg_co2"])
            else:
                # Look up emission factor by transport mode (default fallback per mode)
                from db.models import EmissionFactor, TransportMode
                mode_enum = TransportMode(transport_mode) if transport_mode else None
                if mode_enum:
                    ef = db.query(EmissionFactor).filter(
                        EmissionFactor.transport_mode == mode_enum
                    ).first()
                    if ef:
                        emission_factor_per_ton_km = ef.emission_factor_kg_co2_per_ton_km
                    else:
                        # Fallback defaults if no DB factor
                        defaults = {
                            TransportMode.ROAD_TRUCK: 0.12,
                            TransportMode.ROAD_VAN: 0.15,
                            TransportMode.RAIL_FREIGHT: 0.03,
                            TransportMode.AIR_CARGO: 1.2,
                            TransportMode.SEA_CONTAINER: 0.01,
                            TransportMode.SEA_BULK: 0.008,
                            TransportMode.PIPELINE: 0.005,
                        }
                        emission_factor_per_ton_km = defaults.get(mode_enum, 0.1)
                
                if emission_factor_per_ton_km and weight and distance_km:
                    weight_tonnes = float(weight) / 1000.0
                    total_emissions = weight_tonnes * distance_km * emission_factor_per_ton_km
            
            # Create shipment
            shipment = Shipment(
                organization_id=org_id,
                route_id=route.id,
                weight_kg=float(weight),
                volume_m3=float(r.get("volume_m3") or 0) if r.get("volume_m3") else None,
                total_cost=float(r.get("total_cost") or 0) if r.get("total_cost") else 0.0,
                emission_factor_kg_co2_per_ton_km=emission_factor_per_ton_km,
                emissions_per_kg=(total_emissions / float(weight)) if total_emissions and weight else None,
                total_emissions_kg_co2=total_emissions or 0.0,
                shipment_date=r.get("pickup_date"),
                planned_delivery_date=r.get("delivery_date"),
                carrier=r.get("carrier"),
                tracking_number=r.get("tracking_number"),
            )
            db.add(shipment)
            db.commit()
            created += 1
            
        except Exception as e:
            db.rollback()
            print(f"Error loading shipment: {e}")
            continue
    
    return created


def load_suppliers(rows: List[Dict[str, Any]], db: Session, neo4j: Neo4jService, org_id: str) -> int:
    from db.models import Supplier
    created = 0
    
    for r in rows:
        try:
            if not r.get("name"):
                continue  # Skip if no name
            
            # Check if supplier already exists in this organization
            supplier_id = r.get("supplier_id") or str(uuid.uuid4())
            existing = db.query(Supplier).filter(
                Supplier.id == supplier_id,
                Supplier.organization_id == org_id
            ).first()
            
            if existing:
                # Supplier already exists for this org, skip
                continue
            
            # If ID exists in another org, generate a new UUID to avoid conflicts
            # (since supplier_id is globally unique)
            if supplier_id and db.query(Supplier).filter(Supplier.id == supplier_id).first():
                supplier_id = str(uuid.uuid4())
            
            supplier = Supplier(
                id=supplier_id,
                name=r["name"],
                address=r.get("address"),
                city=r.get("city"),
                region=r.get("region"),
                country=r.get("country"),
                postal_code=r.get("postal_code"),
                latitude=float(r.get("latitude") or 0) if r.get("latitude") else None,
                longitude=float(r.get("longitude") or 0) if r.get("longitude") else None,
                tier_level=r.get("tier_level"),
                certifications=r.get("certifications"),
                contact_email=r.get("contact_email"),
                contact_phone=r.get("contact_phone"),
                organization_id=org_id,
            )
            db.add(supplier)
            db.commit()
            created += 1
            
        except Exception as e:
            db.rollback()
            print(f"Error loading supplier: {e}")
            continue
    
    return created


def load_products(rows: List[Dict[str, Any]], db: Session, neo4j: Neo4jService, org_id: str) -> int:
    from db.models import Product
    created = 0
    
    for r in rows:
        try:
            if not r.get("name"):
                continue  # Skip if no name
            
            product = Product(
                id=r.get("product_id") or str(uuid.uuid4()),
                name=r["name"],
                category=r.get("category"),
                uom=r.get("uom", "EA"),
                weight_kg=float(r.get("weight_kg") or 0) if r.get("weight_kg") else None,
                volume_m3=float(r.get("volume_m3") or 0) if r.get("volume_m3") else None,
                carbon_intensity_per_unit=float(r.get("carbon_intensity_per_unit") or 0) if r.get("carbon_intensity_per_unit") else None,
                organization_id=org_id,
            )
            db.add(product)
            db.commit()
            created += 1
            
        except Exception as e:
            db.rollback()
            print(f"Error loading product: {e}")
            continue
    
    return created


def load_purchase_orders(rows: List[Dict[str, Any]], db: Session, neo4j: Neo4jService, org_id: str) -> int:
    from db.models import PurchaseOrder
    created = 0
    
    for r in rows:
        try:
            po_id = r.get("po_id") or str(uuid.uuid4())
            po_line_id = r.get("po_line_id") or "1"
            
            purchase_order = PurchaseOrder(
                id=f"{po_id}-{po_line_id}",
                po_id=po_id,
                po_line_id=po_line_id,
                supplier_id=r.get("supplier_id"),
                facility_id=r.get("facility_id"),
                product_id=r.get("product_id"),
                quantity=float(r.get("quantity") or 0),
                unit_price=float(r.get("unit_price") or 0),
                total_cost=float(r.get("total_cost") or 0),
                order_date=r.get("order_date"),
                expected_delivery_date=r.get("expected_delivery_date"),
                transport_mode=r.get("transport_mode"),
                currency=r.get("currency", "USD"),
                status=r.get("status", "pending"),
                organization_id=org_id,
            )
            db.add(purchase_order)
            db.commit()
            created += 1
            
        except Exception as e:
            db.rollback()
            print(f"Error loading purchase order: {e}")
            continue
    
    return created


