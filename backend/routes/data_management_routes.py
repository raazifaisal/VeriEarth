from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, List
from geoalchemy2.shape import to_shape
from db.database import get_db
from db.neo4j_service import Neo4jService
from db.models import Facility, Shipment, Route
from services.supply_chain_service import SupplyChainService

router = APIRouter()
class ClearOrgRequest(BaseModel):
    password: str



def handle_foreign_key_error(error: IntegrityError, entity_type: str, entity_id: str) -> str:
    """Convert foreign key constraint errors to user-friendly messages"""
    error_msg = str(error.orig)
    
    # Map common foreign key constraint patterns to user-friendly messages
    if "purchase_orders_supplier_id_fkey" in error_msg:
        return f"Cannot delete supplier '{entity_id}' because it is referenced by purchase orders. Please delete the related purchase orders first."
    
    elif "purchase_orders_product_id_fkey" in error_msg:
        return f"Cannot delete product '{entity_id}' because it is referenced by purchase orders. Please delete the related purchase orders first."
    
    elif "purchase_orders_facility_id_fkey" in error_msg:
        return f"Cannot delete facility '{entity_id}' because it is referenced by purchase orders. Please delete the related purchase orders first."
    
    elif "shipments_route_id_fkey" in error_msg:
        return f"Cannot delete route '{entity_id}' because it is referenced by shipments. Please delete the related shipments first."
    
    elif "routes_origin_facility_id_fkey" in error_msg or "routes_destination_facility_id_fkey" in error_msg:
        return f"Cannot delete facility '{entity_id}' because it is referenced by routes. Please delete the related routes first."
    
    elif "facility_environmental_data_facility_id_fkey" in error_msg:
        return f"Cannot delete facility '{entity_id}' because it has environmental data. Please delete the environmental data first."
    
    else:
        # Generic message for other foreign key constraints
        return f"Cannot delete {entity_type} '{entity_id}' because it is referenced by other records. Please delete the related records first."


def get_neo4j():
    """Get Neo4j service instance"""
    neo4j = Neo4jService(
        uri="bolt://neo4j:7687",
        user="neo4j",
        password="12345678",
    )
    try:
        yield neo4j
    finally:
        neo4j.close()


@router.get("/stats")
async def get_stats(
    org_id: str = Query(...),
    db: Session = Depends(get_db),
    neo4j: Neo4jService = Depends(get_neo4j)
):
    """Get count statistics for all entity types"""
    # Count entities from PostgreSQL
    from db.models import Supplier, Product, PurchaseOrder
    
    facilities_count = db.query(Facility).filter(Facility.organization_id == org_id).count()
    suppliers_count = db.query(Supplier).filter(Supplier.organization_id == org_id).count()
    products_count = db.query(Product).filter(Product.organization_id == org_id).count()
    purchase_orders_count = db.query(PurchaseOrder).filter(PurchaseOrder.organization_id == org_id).count()
    shipments_count = db.query(Shipment).filter(Shipment.organization_id == org_id).count()
    routes_count = db.query(Route).filter(Route.organization_id == org_id).count()
    
    return {
        "facilities": facilities_count,
        "suppliers": suppliers_count,
        "products": products_count,
        "purchase_orders": purchase_orders_count,
        "shipments": shipments_count,
        "routes": routes_count,
    }


@router.get("/{entity_type}")
async def get_entity_data(
    entity_type: str,
    org_id: str = Query(...),
    db: Session = Depends(get_db),
    neo4j: Neo4jService = Depends(get_neo4j)
):
    """Get all records for a specific entity type"""
    if entity_type == "facilities":
        # Fetch facilities and include supplier info when present
        facilities = db.query(Facility).filter(Facility.organization_id == org_id).all()
        from db.models import Supplier as DbSupplier
        supplier_cache: dict[str, str] = {}
        result = []
        for f in facilities:
            lat, lon = None, None
            if f.location:
                point = to_shape(f.location)
                lat, lon = point.y, point.x

            supplier_name = None
            if getattr(f, "supplier_id", None):
                # Cache supplier lookups to minimize queries
                if f.supplier_id in supplier_cache:
                    supplier_name = supplier_cache[f.supplier_id]
                else:
                    sup = db.query(DbSupplier).filter(DbSupplier.id == f.supplier_id).first()
                    supplier_name = sup.name if sup else None
                    if supplier_name:
                        supplier_cache[f.supplier_id] = supplier_name

            result.append({
                "id": f.id,
                "name": f.name,
                "facility_type": f.facility_type.value if f.facility_type else None,
                "city": f.city,
                "country": f.country,
                "lat": lat,
                "lon": lon,
                "address": f.address,
                "capacity_tons": f.capacity_tons,
                # Ownership/supplier info
                "supplier_id": getattr(f, "supplier_id", None),
                "supplier_name": supplier_name,
            })
        return result
    elif entity_type == "shipments":
        # Fetch shipments from PostgreSQL with facility details
        shipments = db.query(Shipment).join(Route).filter(Shipment.organization_id == org_id).all()
        
        result = []
        for s in shipments:
            # Get route details
            route = db.query(Route).filter(Route.id == s.route_id).first()
            if route:
                # Get origin and destination facility names
                origin_facility = db.query(Facility).filter(Facility.id == route.origin_facility_id).first()
                dest_facility = db.query(Facility).filter(Facility.id == route.destination_facility_id).first()
                
                # Calculate ESG metrics based on available data
                total_weight_tonnes = s.weight_kg / 1000 if s.weight_kg else 0
                
                # Calculate emissions based on transport mode and distance
                # Emission factors (kg CO2 per tonne·km) - industry standards
                emission_factors = {
                    "road_truck": 0.12,      # 120g CO2 per tonne·km
                    "rail_freight": 0.03,    # 30g CO2 per tonne·km  
                    "sea_container": 0.01,   # 10g CO2 per tonne·km
                    "air_freight": 0.5       # 500g CO2 per tonne·km
                }
                
                emission_factor = emission_factors.get(route.transport_mode.value, 0.12)
                calculated_emissions = total_weight_tonnes * route.distance_km * emission_factor
                unit_emissions = emission_factor  # kg CO2 per tonne·km
                
                # Calculate cost if not provided (rough estimate)
                cost_per_km_per_tonne = {
                    "road_truck": 0.8,       # $0.8 per km per tonne
                    "rail_freight": 0.3,     # $0.3 per km per tonne
                    "sea_container": 0.1,   # $0.1 per km per tonne
                    "air_freight": 2.0      # $2.0 per km per tonne
                }
                
                estimated_cost = total_weight_tonnes * route.distance_km * cost_per_km_per_tonne.get(route.transport_mode.value, 0.8)
                final_cost = s.total_cost if s.total_cost and s.total_cost > 0 else estimated_cost
                
                result.append({
                    # Basic Route Info
                    "id": s.id,
                    "origin_facility_name": origin_facility.name if origin_facility else "Unknown",
                    "destination_facility_name": dest_facility.name if dest_facility else "Unknown",
                    "transport_mode": route.transport_mode.value if route.transport_mode else None,
                    
                    # Physical Goods Info
                    "weight_kg": s.weight_kg,
                    "weight_tonnes": round(total_weight_tonnes, 2),
                    "volume_m3": s.volume_m3,
                    
                    # ESG Environmental Metrics
                    "distance_km": route.distance_km,
                    "calculated_emissions_kg_co2": round(calculated_emissions, 2),
                    "unit_emissions_kg_per_tonne_km": round(unit_emissions, 3),
                    "emission_factor_used": emission_factor,
                    
                    # Cost & Financial
                    "calculated_cost": round(final_cost, 2),
                    "unit_transportation_cost": round(final_cost / (total_weight_tonnes * route.distance_km), 3) if (total_weight_tonnes > 0 and route.distance_km > 0) else 0,
                    
                    # Dates & Tracking
                    "pickup_date": s.shipment_date.isoformat() if s.shipment_date else None,
                    "delivery_date": s.planned_delivery_date.isoformat() if s.planned_delivery_date else None,
                    "carrier": s.carrier or "Unknown",
                    "tracking_number": s.tracking_number,
                    "status": s.status.value if s.status else "planned",
                    
                    # Additional Context
                    "route_id": s.route_id,
                    "origin_facility_id": route.origin_facility_id,
                    "destination_facility_id": route.destination_facility_id,
                })
        return result
    elif entity_type == "routes":
        # Fetch routes from PostgreSQL
        routes = db.query(Route).filter(Route.organization_id == org_id).all()
        result = []
        for r in routes:
            # Get origin and destination facility names
            origin_facility = db.query(Facility).filter(Facility.id == r.origin_facility_id).first()
            dest_facility = db.query(Facility).filter(Facility.id == r.destination_facility_id).first()
            
            result.append({
                "id": r.id,
                "origin_facility_id": r.origin_facility_id,
                "origin_facility_name": origin_facility.name if origin_facility else "Unknown",
                "origin_location": f"{origin_facility.city}, {origin_facility.country}" if origin_facility and origin_facility.city else "Unknown",
                "destination_facility_id": r.destination_facility_id,
                "destination_facility_name": dest_facility.name if dest_facility else "Unknown",
                "destination_location": f"{dest_facility.city}, {dest_facility.country}" if dest_facility and dest_facility.city else "Unknown",
                "transport_mode": r.transport_mode.value if r.transport_mode else None,
                "distance_km": r.distance_km,
                "duration_hours": r.duration_hours,
                "is_multi_leg": r.is_multi_leg,
                "intermediate_stops": r.intermediate_stops,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            })
        return result
    elif entity_type == "suppliers":
        from db.models import Supplier
        suppliers = db.query(Supplier).filter(Supplier.organization_id == org_id).all()
        result = []
        for s in suppliers:
            result.append({
                "id": s.id,
                "name": s.name,
                "address": s.address,
                "city": s.city,
                "region": s.region,
                "country": s.country,
                "postal_code": s.postal_code,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "tier_level": s.tier_level,
                "certifications": s.certifications,
                "contact_email": s.contact_email,
                "contact_phone": s.contact_phone,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            })
        return result
    
    elif entity_type == "products":
        from db.models import Product
        products = db.query(Product).filter(Product.organization_id == org_id).all()
        result = []
        for p in products:
            result.append({
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "uom": p.uom,
                "weight_kg": p.weight_kg,
                "volume_m3": p.volume_m3,
                "carbon_intensity_per_unit": p.carbon_intensity_per_unit,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            })
        return result
    
    elif entity_type == "purchase_orders":
        from db.models import PurchaseOrder
        purchase_orders = db.query(PurchaseOrder).filter(PurchaseOrder.organization_id == org_id).all()
        result = []
        for po in purchase_orders:
            result.append({
                "id": po.id,
                "po_id": po.po_id,
                "po_line_id": po.po_line_id,
                "supplier_id": po.supplier_id,
                "facility_id": po.facility_id,
                "product_id": po.product_id,
                "quantity": po.quantity,
                "unit_price": po.unit_price,
                "total_cost": po.total_cost,
                "order_date": po.order_date.isoformat() if po.order_date else None,
                "expected_delivery_date": po.expected_delivery_date.isoformat() if po.expected_delivery_date else None,
                "transport_mode": po.transport_mode,
                "currency": po.currency,
                "status": po.status,
                "created_at": po.created_at.isoformat() if po.created_at else None,
                "updated_at": po.updated_at.isoformat() if po.updated_at else None,
            })
        return result
    else:
        raise HTTPException(status_code=400, detail="Invalid entity type")


@router.post("/organizations/{org_id}/clear-all")
async def clear_entire_organization(
    org_id: str,
    body: ClearOrgRequest,
    db: Session = Depends(get_db),
    neo4j: Neo4jService = Depends(get_neo4j)
):
    """Dangerous: Clear ALL data for an organization in the correct dependency order.
    Requires sudo password if set for the organization.
    """
    # Verify sudo password if configured; else accept demo passwords for backward-compat
    pwd = (body.password or "").strip()
    from db.models import Organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    from auth.auth import verify_password
    if org.sudo_password_hash:
        if not verify_password(pwd, org.sudo_password_hash):
            raise HTTPException(status_code=403, detail="Invalid password")
    else:
        if pwd.lower() not in {"veriearth", "confirm"}:
            raise HTTPException(status_code=403, detail="Invalid password")

    from db.models import (
        Facility, Shipment, Route, Supplier, Product, PurchaseOrder, FacilityEnvironmentalData
    )

    # Collect IDs for facility-scoped deletes
    facilities = db.query(Facility).filter(Facility.organization_id == org_id).all()
    facility_ids = [f.id for f in facilities]

    try:
        # 1) EO timeseries (raw table) and environmental snapshots
        from sqlalchemy import text as sa_text
        db.execute(sa_text("DELETE FROM facility_eo_timeseries WHERE organization_id=:org"), {"org": org_id})

        if facility_ids:
            db.query(FacilityEnvironmentalData).filter(
                FacilityEnvironmentalData.facility_id.in_(facility_ids)
            ).delete(synchronize_session=False)

        # 2) Shipments (depends on routes)
        db.query(Shipment).filter(Shipment.organization_id == org_id).delete(synchronize_session=False)

        # 3) Routes (depends on facilities)
        db.query(Route).filter(Route.organization_id == org_id).delete(synchronize_session=False)

        # 4) Purchase Orders (depends on suppliers/products/facilities)
        db.query(PurchaseOrder).filter(PurchaseOrder.organization_id == org_id).delete(synchronize_session=False)

        # 5) Products
        db.query(Product).filter(Product.organization_id == org_id).delete(synchronize_session=False)

        # 6) Suppliers (first detach from facilities to avoid FK)
        from sqlalchemy import update as sa_update
        db.execute(
            sa_update(Facility)
            .where(Facility.organization_id == org_id)
            .values(supplier_id=None)
        )
        db.query(Supplier).filter(Supplier.organization_id == org_id).delete(synchronize_session=False)

        # 7) Facilities
        db.query(Facility).filter(Facility.organization_id == org_id).delete(synchronize_session=False)

        db.commit()

        # 8) Clear Neo4j graph for this org (both org_id and organization_id props)
        try:
            with neo4j._driver.session() as session:
                session.run("""
                MATCH (n) WHERE coalesce(n.org_id, n.organization_id) = $org DETACH DELETE n
                """, org=org_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Neo4j clear failed: {e}")

        return {"status": "ok", "message": "Organization data cleared"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{entity_type}/{id}")
async def delete_entity(
    entity_type: str,
    id: str,
    org_id: str = Query(...),
    db: Session = Depends(get_db),
    neo4j: Neo4jService = Depends(get_neo4j)
):
    """Delete a specific record"""
    if entity_type == "facilities":
        facility = db.query(Facility).filter(
            Facility.id == id,
            Facility.organization_id == org_id
        ).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")
        
        # Delete from PostgreSQL
        db.delete(facility)
        db.commit()
    elif entity_type == "suppliers":
        from db.models import Supplier
        supplier = db.query(Supplier).filter(
            Supplier.id == id,
            Supplier.organization_id == org_id
        ).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        try:
            db.delete(supplier)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            error_message = handle_foreign_key_error(e, "supplier", id)
            raise HTTPException(status_code=400, detail=error_message)
    elif entity_type == "products":
        from db.models import Product
        product = db.query(Product).filter(
            Product.id == id,
            Product.organization_id == org_id
        ).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        try:
            db.delete(product)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            error_message = handle_foreign_key_error(e, "product", id)
            raise HTTPException(status_code=400, detail=error_message)
    elif entity_type == "purchase_orders":
        from db.models import PurchaseOrder
        purchase_order = db.query(PurchaseOrder).filter(
            PurchaseOrder.id == id,
            PurchaseOrder.organization_id == org_id
        ).first()
        if not purchase_order:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        
        try:
            db.delete(purchase_order)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            error_message = handle_foreign_key_error(e, "purchase order", id)
            raise HTTPException(status_code=400, detail=error_message)
    elif entity_type == "shipments":
        from db.models import Shipment
        shipment = db.query(Shipment).filter(
            Shipment.id == id,
            Shipment.organization_id == org_id
        ).first()
        if not shipment:
            raise HTTPException(status_code=404, detail="Shipment not found")
        db.delete(shipment)
        db.commit()
    elif entity_type == "routes":
        from db.models import Route
        route = db.query(Route).filter(
            Route.id == id,
            Route.organization_id == org_id
        ).first()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        db.delete(route)
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    return {"status": "ok", "message": "Entity deleted"}


@router.delete("/{entity_type}")
async def clear_all_entities(
    entity_type: str,
    org_id: str = Query(...),
    db: Session = Depends(get_db),
    neo4j: Neo4jService = Depends(get_neo4j)
):
    """Delete all records of a specific entity type for an organization"""
    if entity_type == "facilities":
        from db.models import FacilityEnvironmentalData, PurchaseOrder, Route, Shipment
        
        # Get all facility IDs first
        facilities = db.query(Facility).filter(Facility.organization_id == org_id).all()
        facility_ids = [f.id for f in facilities]
        
        try:
            # Delete dependent records in the correct order
            # 1. Delete environmental data
            db.query(FacilityEnvironmentalData).filter(
                FacilityEnvironmentalData.facility_id.in_(facility_ids)
            ).delete(synchronize_session=False)
            
            # 2. Delete shipments (depends on routes)
            db.query(Shipment).filter(Shipment.organization_id == org_id).delete(synchronize_session=False)
            
            # 3. Delete routes (depends on facilities)
            db.query(Route).filter(Route.organization_id == org_id).delete(synchronize_session=False)
            
            # 4. Delete purchase orders (depends on facilities)
            db.query(PurchaseOrder).filter(PurchaseOrder.organization_id == org_id).delete(synchronize_session=False)
            
            # 5. Finally delete facilities
            db.query(Facility).filter(Facility.organization_id == org_id).delete(synchronize_session=False)
            
            db.commit()
            return {
                "status": "ok", 
                "deleted": len(facility_ids),
                "message": f"⚠️ NUCLEAR OPTION: Cleared {len(facility_ids)} facilities and ALL related data for this organization:\n"
                          f"• Environmental data (EO, AQI, pollution measurements)\n"
                          f"• Routes (transportation paths)\n"
                          f"• Shipments (tracking data)\n"
                          f"• Purchase orders (supplier orders)\n\n"
                          f"This action cannot be undone. Data has been permanently deleted."
            }
        except IntegrityError as e:
            db.rollback()
            error_message = handle_foreign_key_error(e, entity_type, "all")
            raise HTTPException(status_code=400, detail=error_message)
    elif entity_type == "suppliers":
        from db.models import Supplier, Facility
        # First detach suppliers from facilities in this org to avoid FK errors
        try:
            facilities_q = db.query(Facility).filter(Facility.organization_id == org_id, Facility.supplier_id.isnot(None))
            # Set supplier_id to NULL for all referencing facilities
            facilities_q.update({Facility.supplier_id: None}, synchronize_session=False)
            db.flush()

            deleted_count = db.query(Supplier).filter(Supplier.organization_id == org_id).count()
            db.query(Supplier).filter(Supplier.organization_id == org_id).delete(synchronize_session=False)
            db.commit()
            return {"status": "ok", "deleted": deleted_count}
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Failed to delete suppliers due to dependent records.")
    elif entity_type == "products":
        from db.models import Product
        deleted_count = db.query(Product).filter(Product.organization_id == org_id).count()
        
        try:
            db.query(Product).filter(Product.organization_id == org_id).delete()
            db.commit()
            return {"status": "ok", "deleted": deleted_count}
        except IntegrityError as e:
            db.rollback()
            error_message = f"Cannot delete all products because some are referenced by purchase orders. Please delete the related purchase orders first."
            raise HTTPException(status_code=400, detail=error_message)
    elif entity_type == "purchase_orders":
        from db.models import PurchaseOrder
        deleted_count = db.query(PurchaseOrder).filter(PurchaseOrder.organization_id == org_id).count()
        db.query(PurchaseOrder).filter(PurchaseOrder.organization_id == org_id).delete()
        db.commit()
        return {"status": "ok", "deleted": deleted_count}
    elif entity_type == "shipments":
        from db.models import Shipment
        deleted_count = db.query(Shipment).filter(Shipment.organization_id == org_id).count()
        db.query(Shipment).filter(Shipment.organization_id == org_id).delete()
        db.commit()
        return {"status": "ok", "deleted": deleted_count}
    elif entity_type == "routes":
        from db.models import Route
        deleted_count = db.query(Route).filter(Route.organization_id == org_id).count()
        db.query(Route).filter(Route.organization_id == org_id).delete()
        db.commit()
        return {"status": "ok", "deleted": deleted_count}
    else:
        raise HTTPException(status_code=400, detail="Invalid entity type")


@router.put("/{entity_type}/{id}")
async def update_entity(
    entity_type: str,
    id: str,
    data: Dict[str, Any],
    org_id: str = Query(...),
    db: Session = Depends(get_db),
    neo4j: Neo4jService = Depends(get_neo4j)
):
    """Update a specific record"""
    if entity_type == "facilities":
        from geoalchemy2.elements import WKTElement
        
        facility = db.query(Facility).filter(
            Facility.id == id,
            Facility.organization_id == org_id
        ).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")
        
        # Update PostgreSQL - handle location separately
        for key, value in data.items():
            if key in ['id', 'organization_id', 'lat', 'lon']:
                continue
            if hasattr(facility, key):
                setattr(facility, key, value)
        
        # Update location if lat/lon provided
        if 'lat' in data and 'lon' in data:
            lat, lon = data['lat'], data['lon']
            if lat is not None and lon is not None:
                facility.location = WKTElement(f'POINT({lon} {lat})', srid=4326)
        
        db.commit()
        db.refresh(facility)
        
        return {"status": "ok", "id": id}
    elif entity_type == "suppliers":
        from db.models import Supplier
        supplier = db.query(Supplier).filter(
            Supplier.id == id,
            Supplier.organization_id == org_id
        ).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        for key, value in data.items():
            if key in ['id', 'organization_id']:
                continue
            if hasattr(supplier, key):
                setattr(supplier, key, value)
        
        db.commit()
        db.refresh(supplier)
        return {"status": "ok", "id": id}
    elif entity_type == "products":
        from db.models import Product
        product = db.query(Product).filter(
            Product.id == id,
            Product.organization_id == org_id
        ).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        for key, value in data.items():
            if key in ['id', 'organization_id']:
                continue
            if hasattr(product, key):
                setattr(product, key, value)
        
        db.commit()
        db.refresh(product)
        return {"status": "ok", "id": id}
    elif entity_type == "purchase_orders":
        from db.models import PurchaseOrder
        purchase_order = db.query(PurchaseOrder).filter(
            PurchaseOrder.id == id,
            PurchaseOrder.organization_id == org_id
        ).first()
        if not purchase_order:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        
        for key, value in data.items():
            if key in ['id', 'organization_id']:
                continue
            if hasattr(purchase_order, key):
                setattr(purchase_order, key, value)
        
        db.commit()
        db.refresh(purchase_order)
        return {"status": "ok", "id": id}
    elif entity_type == "shipments":
        from db.models import Shipment
        shipment = db.query(Shipment).filter(
            Shipment.id == id,
            Shipment.organization_id == org_id
        ).first()
        if not shipment:
            raise HTTPException(status_code=404, detail="Shipment not found")
        
        for key, value in data.items():
            if key in ['id', 'organization_id']:
                continue
            if hasattr(shipment, key):
                setattr(shipment, key, value)
        
        db.commit()
        db.refresh(shipment)
        return {"status": "ok", "id": id}
    elif entity_type == "routes":
        from db.models import Route
        route = db.query(Route).filter(
            Route.id == id,
            Route.organization_id == org_id
        ).first()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        for key, value in data.items():
            if key in ['id', 'organization_id']:
                continue
            if hasattr(route, key):
                setattr(route, key, value)
        
        db.commit()
        db.refresh(route)
        return {"status": "ok", "id": id}
    else:
        raise HTTPException(status_code=400, detail="Invalid entity type")

