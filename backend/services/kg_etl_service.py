"""
Knowledge Graph ETL Service - Phase 1 Implementation

Syncs PostgreSQL data to Neo4j knowledge graph using idempotent MERGE patterns.
Phase 1: Organization, Supplier, Facility, Route, Shipment, EOReading (monthly snapshots)
Phase 2: Product, PurchaseOrder (to be implemented)
Phase 3: Derived relationships, GDS analytics (to be implemented)
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from neo4j import GraphDatabase
from geoalchemy2.shape import to_shape

logger = logging.getLogger(__name__)

class KGETLService:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, db: Session):
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.db = db
        self.batch_size = 500
        
    def close(self):
        self.neo4j_driver.close()
    
    def _get_org_database_name(self, org_id: str) -> str:
        """Get database name - using default database for all orgs (Community Edition)"""
        # Neo4j Community Edition doesn't support multiple databases
        # All organizations use the default 'neo4j' database with org_id filtering
        return "neo4j"
    
    def _ensure_database_exists(self, org_id: str) -> str:
        """Ensure we're using the correct database. Returns database name."""
        # Neo4j Community Edition limitation: single database only
        # Use default 'neo4j' database, isolate by org_id property on all nodes
        db_name = self._get_org_database_name(org_id)
        logger.info(f"Using database {db_name} for org {org_id} (org_id filtering for isolation)")
        return db_name
    
    def _run_cypher(self, query: str, params: Dict[str, Any] = None, database: str = None, tx=None):
        """Execute Cypher query in transaction or new session with optional database context"""
        if tx:
            return tx.run(query, params or {})
        with self.neo4j_driver.session(database=database) as session:
            return session.run(query, params or {})
    
    def setup_constraints_and_indexes(self, org_id: str):
        """Run once per org: create unique constraints and indexes in organization database"""
        db_name = self._ensure_database_exists(org_id)
        
        constraints = [
            "CREATE CONSTRAINT org_unique IF NOT EXISTS FOR (o:Organization) REQUIRE (o.id) IS UNIQUE",
            "CREATE CONSTRAINT supplier_unique IF NOT EXISTS FOR (s:Supplier) REQUIRE (s.id) IS UNIQUE",
            "CREATE CONSTRAINT facility_unique IF NOT EXISTS FOR (f:Facility) REQUIRE (f.id) IS UNIQUE",
            "CREATE CONSTRAINT route_unique IF NOT EXISTS FOR (r:Route) REQUIRE (r.id) IS UNIQUE",
            "CREATE CONSTRAINT shipment_unique IF NOT EXISTS FOR (sh:Shipment) REQUIRE (sh.id) IS UNIQUE",
            "CREATE CONSTRAINT eoread_unique IF NOT EXISTS FOR (e:EOReading) REQUIRE (e.id) IS UNIQUE",
            "CREATE CONSTRAINT product_unique IF NOT EXISTS FOR (p:Product) REQUIRE (p.id) IS UNIQUE",
            "CREATE CONSTRAINT po_unique IF NOT EXISTS FOR (po:PurchaseOrder) REQUIRE (po.id) IS UNIQUE",
        ]
        
        indexes = [
            "CREATE INDEX facility_city IF NOT EXISTS FOR (f:Facility) ON (f.city)",
            "CREATE INDEX route_mode IF NOT EXISTS FOR (r:Route) ON (r.transport_mode)",
            "CREATE INDEX shipment_date IF NOT EXISTS FOR (sh:Shipment) ON (sh.shipment_date)",
            "CREATE INDEX supplier_tier IF NOT EXISTS FOR (s:Supplier) ON (s.tier_level)",
            "CREATE INDEX eo_observed_at IF NOT EXISTS FOR (e:EOReading) ON (e.observed_at)",
            "CREATE INDEX product_category IF NOT EXISTS FOR (p:Product) ON (p.category)",
            "CREATE INDEX po_order_date IF NOT EXISTS FOR (po:PurchaseOrder) ON (po.order_date)",
        ]
        
        with self.neo4j_driver.session(database=db_name) as session:
            for stmt in constraints:
                try:
                    session.run(stmt)
                    logger.info(f"Applied constraint: {stmt[:50]}...")
                except Exception as e:
                    logger.warning(f"Constraint may exist: {e}")
            
            for stmt in indexes:
                try:
                    session.run(stmt)
                    logger.info(f"Applied index: {stmt[:50]}...")
                except Exception as e:
                    logger.warning(f"Index may exist: {e}")
    
    # ========== PHASE 1: Core Supply Chain ==========
    
    def sync_organization(self, org_id: str, database: str) -> bool:
        """Sync Organization node to organization database"""
        org = self.db.execute(
            text("SELECT id, name, industry, subscription_tier FROM organizations WHERE id = :id"),
            {"id": org_id}
        ).mappings().first()
        
        if not org:
            logger.warning(f"Organization {org_id} not found in PostgreSQL")
            return False
        
        query = """
        MERGE (o:Organization {id: $id})
        ON CREATE SET o.created_at = timestamp()
        ON MATCH SET o.updated_at = timestamp()
        SET o.name = $name,
            o.industry = $industry,
            o.subscription_tier = $subscription_tier
        RETURN o.id AS id
        """
        
        with self.neo4j_driver.session(database=database) as session:
            result = session.run(query, id=org["id"], name=org["name"], 
                               industry=org.get("industry"), subscription_tier=org.get("subscription_tier"))
            record = result.single()
            logger.info(f"Synced Organization: {org['name']}")
            return record is not None
    
    def sync_suppliers(self, org_id: str, database: str, last_synced_at: Optional[datetime] = None) -> int:
        """Batch sync Suppliers. Returns count synced."""
        where_clause = "WHERE organization_id = :org_id"
        params = {"org_id": org_id}
        if last_synced_at:
            where_clause += " AND updated_at > :last_sync"
            params["last_sync"] = last_synced_at
        
        suppliers = self.db.execute(
            text(f"""
                SELECT id, name, city, region, country, tier_level, certifications, 
                       contact_email, contact_phone, is_active
                FROM suppliers {where_clause}
            """),
            params
        ).mappings().all()
        
        if not suppliers:
            return 0
        
        query = """
        UNWIND $rows AS r
        MERGE (s:Supplier {id: r.id})
        ON CREATE SET s.created_at = timestamp()
        ON MATCH SET s.updated_at = timestamp()
        SET s.org_id = $org_id,
            s.name = r.name,
            s.city = r.city,
            s.region = r.region,
            s.country = r.country,
            s.tier_level = r.tier_level,
            s.certifications = r.certifications,
            s.contact_email = r.contact_email,
            s.contact_phone = r.contact_phone,
            s.is_active = coalesce(r.is_active, true)
        
        WITH s
        MERGE (org:Organization {id: $org_id})
        MERGE (org)-[:HAS_SUPPLIER]->(s)
        RETURN count(s) AS cnt
        """
        
        rows_data = [dict(r) for r in suppliers]
        synced = 0
        for i in range(0, len(rows_data), self.batch_size):
            batch = rows_data[i:i + self.batch_size]
            with self.neo4j_driver.session(database=database) as session:
                result = session.run(query, rows=batch, org_id=org_id)
                synced += result.single()["cnt"]
        
        logger.info(f"Synced {synced} suppliers for org {org_id}")
        return synced
    
    def sync_facilities(self, org_id: str, database: str, last_synced_at: Optional[datetime] = None) -> int:
        """Batch sync Facilities with optional supplier ownership. Returns count synced."""
        where_clause = "WHERE f.organization_id = :org_id"
        params = {"org_id": org_id}
        if last_synced_at:
            where_clause += " AND f.updated_at > :last_sync"
            params["last_sync"] = last_synced_at
        
        facilities = self.db.execute(
            text(f"""
                SELECT f.id, f.name, f.facility_type, f.city, f.country, f.address,
                       f.capacity_tons, f.is_active, f.supplier_id,
                       ST_Y(f.location::geometry) AS latitude,
                       ST_X(f.location::geometry) AS longitude
                FROM facilities f
                {where_clause}
            """),
            params
        ).mappings().all()
        
        if not facilities:
            return 0
        
        query = """
        UNWIND $rows AS r
        MERGE (f:Facility {id: r.id})
        ON CREATE SET f.created_at = timestamp()
        ON MATCH SET f.updated_at = timestamp()
        SET f.org_id = $org_id,
            f.name = r.name,
            f.facility_type = r.facility_type,
            f.city = r.city,
            f.country = r.country,
            f.address = r.address,
            f.capacity_tons = r.capacity_tons,
            f.is_active = coalesce(r.is_active, true),
            f.latitude = r.latitude,
            f.longitude = r.longitude
        
        WITH f, r
        WHERE r.latitude IS NOT NULL AND r.longitude IS NOT NULL
        SET f.location = point({longitude: r.longitude, latitude: r.latitude})
        
        WITH f, r
        MERGE (org:Organization {id: $org_id})
        MERGE (org)-[:HAS_FACILITY]->(f)
        
        WITH f, r
        WHERE r.supplier_id IS NOT NULL
        MERGE (s:Supplier {id: r.supplier_id})
        MERGE (s)-[:OWNS]->(f)
        
        RETURN count(f) AS cnt
        """
        
        rows_data = [dict(r) for r in facilities]
        # Convert enum to string if needed
        for row in rows_data:
            if hasattr(row.get("facility_type"), "value"):
                row["facility_type"] = row["facility_type"].value
        
        synced = 0
        for i in range(0, len(rows_data), self.batch_size):
            batch = rows_data[i:i + self.batch_size]
            with self.neo4j_driver.session(database=database) as session:
                result = session.run(query, rows=batch, org_id=org_id)
                synced += result.single()["cnt"]
        
        logger.info(f"Synced {synced} facilities for org {org_id}")
        return synced
    
    def sync_routes(self, org_id: str, database: str, last_synced_at: Optional[datetime] = None) -> int:
        """Batch sync Routes as nodes with ORIGIN/DESTINATION relationships. Returns count synced."""
        where_clause = "WHERE r.organization_id = :org_id"
        params = {"org_id": org_id}
        if last_synced_at:
            where_clause += " AND r.updated_at > :last_sync"
            params["last_sync"] = last_synced_at
        
        routes = self.db.execute(
            text(f"""
                SELECT r.id, r.origin_facility_id, r.destination_facility_id,
                       r.transport_mode, r.distance_km, r.duration_hours,
                       r.is_multi_leg, r.intermediate_stops, r.is_active
                FROM routes r
                {where_clause}
            """),
            params
        ).mappings().all()
        
        if not routes:
            return 0
        
        query = """
        UNWIND $rows AS r
        MERGE (rt:Route {id: r.id})
        ON CREATE SET rt.created_at = timestamp()
        ON MATCH SET rt.updated_at = timestamp()
        SET rt.org_id = $org_id,
            rt.transport_mode = r.transport_mode,
            rt.distance_km = r.distance_km,
            rt.duration_hours = r.duration_hours,
            rt.is_multi_leg = coalesce(r.is_multi_leg, false),
            rt.intermediate_stops = r.intermediate_stops,
            rt.is_active = coalesce(r.is_active, true)
        
        WITH rt, r
        MERGE (o:Facility {id: r.origin_facility_id})
        MERGE (d:Facility {id: r.destination_facility_id})
        MERGE (o)-[:ORIGIN]->(rt)
        MERGE (rt)-[:DESTINATION]->(d)
        
        RETURN count(rt) AS cnt
        """
        
        rows_data = [dict(r) for r in routes]
        # Convert enum to string if needed
        for row in rows_data:
            if hasattr(row.get("transport_mode"), "value"):
                row["transport_mode"] = row["transport_mode"].value
        
        synced = 0
        for i in range(0, len(rows_data), self.batch_size):
            batch = rows_data[i:i + self.batch_size]
            with self.neo4j_driver.session(database=database) as session:
                result = session.run(query, rows=batch, org_id=org_id)
                synced += result.single()["cnt"]
        
        logger.info(f"Synced {synced} routes for org {org_id}")
        return synced
    
    def sync_shipments(self, org_id: str, database: str, last_synced_at: Optional[datetime] = None) -> int:
        """Batch sync Shipments with USES_ROUTE and BELONGS_TO relationships. Returns count synced."""
        where_clause = "WHERE s.organization_id = :org_id"
        params = {"org_id": org_id}
        if last_synced_at:
            where_clause += " AND s.updated_at > :last_sync"
            params["last_sync"] = last_synced_at
        
        shipments = self.db.execute(
            text(f"""
                SELECT s.id, s.route_id, s.weight_kg, s.volume_m3, s.total_cost,
                       s.total_emissions_kg_co2, s.shipment_date, s.planned_delivery_date,
                       s.actual_delivery_date, s.status, s.carrier, s.tracking_number
                FROM shipments s
                {where_clause}
            """),
            params
        ).mappings().all()
        
        if not shipments:
            return 0
        
        query = """
        UNWIND $rows AS r
        MERGE (sh:Shipment {id: r.id})
        ON CREATE SET sh.created_at = timestamp()
        ON MATCH SET sh.updated_at = timestamp()
        SET sh.org_id = $org_id,
            sh.weight_kg = r.weight_kg,
            sh.volume_m3 = r.volume_m3,
            sh.total_cost = r.total_cost,
            sh.total_emissions_kg_co2 = r.total_emissions_kg_co2,
            sh.shipment_date = r.shipment_date,
            sh.planned_delivery_date = r.planned_delivery_date,
            sh.actual_delivery_date = r.actual_delivery_date,
            sh.status = r.status,
            sh.carrier = r.carrier,
            sh.tracking_number = r.tracking_number
        
        WITH sh, r
        MERGE (rt:Route {id: r.route_id})
        MERGE (sh)-[:USES_ROUTE]->(rt)
        
        WITH sh
        MERGE (org:Organization {id: $org_id})
        MERGE (sh)-[:BELONGS_TO]->(org)
        
        RETURN count(sh) AS cnt
        """
        
        rows_data = [dict(r) for r in shipments]
        # Convert enum and datetime to string for Neo4j
        for row in rows_data:
            if hasattr(row.get("status"), "value"):
                row["status"] = row["status"].value
            for date_field in ["shipment_date", "planned_delivery_date", "actual_delivery_date"]:
                if row.get(date_field) and hasattr(row[date_field], "isoformat"):
                    row[date_field] = row[date_field].isoformat()
        
        synced = 0
        for i in range(0, len(rows_data), self.batch_size):
            batch = rows_data[i:i + self.batch_size]
            with self.neo4j_driver.session(database=database) as session:
                result = session.run(query, rows=batch, org_id=org_id)
                synced += result.single()["cnt"]
        
        logger.info(f"Synced {synced} shipments for org {org_id}")
        return synced
    
    def sync_eo_readings_monthly(self, org_id: str, database: str) -> int:
        """Sync EOReading nodes from monthly aggregates in facility_eo_timeseries. Returns count synced."""
        # Aggregate monthly snapshots per facility
        monthly_data = self.db.execute(
            text("""
                SELECT facility_id,
                       DATE_TRUNC('month', observed_at)::date AS year_month,
                       AVG(aqi_score) AS avg_aqi,
                       MAX(aqi_score) AS max_aqi,
                       AVG(no2) AS avg_no2,
                       AVG(co) AS avg_co,
                       AVG(so2) AS avg_so2,
                       AVG(o3) AS avg_o3,
                       AVG(ch4) AS avg_ch4,
                       AVG(aod) AS avg_aod,
                       MAX(observed_at) AS last_observed_at
                FROM facility_eo_timeseries
                WHERE organization_id = :org_id
                GROUP BY facility_id, DATE_TRUNC('month', observed_at)
                ORDER BY facility_id, year_month
            """),
            {"org_id": org_id}
        ).mappings().all()
        
        if not monthly_data:
            logger.info(f"No EO timeseries data for org {org_id}")
            return 0
        
        query = """
        UNWIND $rows AS r
        MERGE (e:EOReading {id: r.id})
        ON CREATE SET e.created_at = timestamp()
        ON MATCH SET e.updated_at = timestamp()
        SET e.facility_id = r.facility_id,
            e.org_id = $org_id,
            e.observed_at = r.observed_at,
            e.aqi_score = r.avg_aqi,
            e.no2 = r.avg_no2,
            e.co = r.avg_co,
            e.so2 = r.avg_so2,
            e.o3 = r.avg_o3,
            e.ch4 = r.avg_ch4,
            e.aod = r.avg_aod,
            e.pollution_level = CASE 
                WHEN r.avg_aqi < 50 THEN 'good'
                WHEN r.avg_aqi < 100 THEN 'moderate'
                WHEN r.avg_aqi < 150 THEN 'unhealthy_sensitive'
                WHEN r.avg_aqi < 200 THEN 'unhealthy'
                ELSE 'hazardous'
            END
        
        WITH e, r
        MERGE (f:Facility {id: r.facility_id})
        MERGE (f)-[:HAS_EO_READING]->(e)
        
        RETURN count(e) AS cnt
        """
        
        rows_data = []
        for row in monthly_data:
            # Create unique ID: facility_id::YYYY-MM
            year_month_str = row["year_month"].strftime("%Y-%m")
            eo_id = f"{row['facility_id']}::{year_month_str}"
            rows_data.append({
                "id": eo_id,
                "facility_id": row["facility_id"],
                "observed_at": row["year_month"].isoformat(),
                "avg_aqi": float(row["avg_aqi"]) if row["avg_aqi"] else None,
                "max_aqi": float(row["max_aqi"]) if row["max_aqi"] else None,
                "avg_no2": float(row["avg_no2"]) if row["avg_no2"] else None,
                "avg_co": float(row["avg_co"]) if row["avg_co"] else None,
                "avg_so2": float(row["avg_so2"]) if row["avg_so2"] else None,
                "avg_o3": float(row["avg_o3"]) if row["avg_o3"] else None,
                "avg_ch4": float(row["avg_ch4"]) if row["avg_ch4"] else None,
                "avg_aod": float(row["avg_aod"]) if row["avg_aod"] else None,
            })
        
        synced = 0
        for i in range(0, len(rows_data), self.batch_size):
            batch = rows_data[i:i + self.batch_size]
            with self.neo4j_driver.session(database=database) as session:
                result = session.run(query, rows=batch, org_id=org_id)
                synced += result.single()["cnt"]
        
        logger.info(f"Synced {synced} EO monthly readings for org {org_id}")
        return synced
    
    def _compute_route_emission_weights(self, org_id: str, database: str) -> None:
        """
        Compute emission_weight for each Route node as the sum of total_emissions_kg_co2
        from all shipments on that route (from Postgres).
        """
        # Fetch route emission sums from Postgres
        emis_data = self.db.execute(
            text("""
                SELECT sh.route_id, SUM(sh.total_emissions_kg_co2) AS total_emis
                FROM shipments sh
                WHERE sh.organization_id = :org
                GROUP BY sh.route_id
            """),
            {"org": org_id}
        ).mappings().all()
        
        if not emis_data:
            return
        
        # Update Neo4j Route nodes with emission_weight
        query = """
        UNWIND $rows AS r
        MATCH (rt:Route {id: r.route_id, org_id: $org_id})
        SET rt.emission_weight = r.total_emis
        RETURN count(rt) AS cnt
        """
        
        rows_data = [{"route_id": row["route_id"], "total_emis": float(row["total_emis"] or 0.0)} for row in emis_data]
        
        with self.neo4j_driver.session(database=database) as session:
            for i in range(0, len(rows_data), self.batch_size):
                batch = rows_data[i:i + self.batch_size]
                session.run(query, rows=batch, org_id=org_id).consume()
        
        logger.info(f"Computed emission_weight for {len(rows_data)} routes in org {org_id}")
    
    def sync_phase1(self, org_id: str, last_synced_at: Optional[datetime] = None) -> Dict[str, int]:
        """Run Phase 1 ETL: Organization → Supplier → Facility → Route → Shipment → EOReading"""
        logger.info(f"Starting Phase 1 sync for organization {org_id}")
        stats = {}
        
        # Ensure organization database exists and get name
        database = self._ensure_database_exists(org_id)
        
        # Setup constraints/indexes in org database
        self.setup_constraints_and_indexes(org_id)
        
        # 1. Organization
        if self.sync_organization(org_id, database):
            stats["organizations"] = 1
        
        # 2. Suppliers (depends on Organization)
        stats["suppliers"] = self.sync_suppliers(org_id, database, last_synced_at)
        
        # 3. Facilities (depends on Organization, optionally Supplier)
        stats["facilities"] = self.sync_facilities(org_id, database, last_synced_at)
        
        # 4. Routes (depends on Facilities)
        stats["routes"] = self.sync_routes(org_id, database, last_synced_at)
        
        # 5. Shipments (depends on Routes)
        stats["shipments"] = self.sync_shipments(org_id, database, last_synced_at)
        
        # 6. Compute emission_weight on Routes (sum of shipment emissions per route)
        self._compute_route_emission_weights(org_id, database)
        
        # 7. EOReading monthly snapshots (depends on Facilities)
        stats["eo_readings"] = self.sync_eo_readings_monthly(org_id, database)
        
        logger.info(f"Phase 1 sync completed: {stats}")
        return stats
    
    # ========== PHASE 2: Procurement Integration ==========
    
    def sync_products(self, org_id: str, database: str, last_synced_at: Optional[datetime] = None) -> int:
        """Batch sync Products. Returns count synced."""
        where_clause = "WHERE p.organization_id = :org_id"
        params = {"org_id": org_id}
        if last_synced_at:
            where_clause += " AND p.updated_at > :last_sync"
            params["last_sync"] = last_synced_at
        
        products = self.db.execute(
            text(f"""
                SELECT p.id, p.name, p.category, p.uom, p.weight_kg, 
                       p.volume_m3, p.carbon_intensity_per_unit, p.is_active
                FROM products p
                {where_clause}
            """),
            params
        ).mappings().all()
        
        if not products:
            return 0
        
        query = """
        UNWIND $rows AS r
        MERGE (p:Product {id: r.id})
        ON CREATE SET p.created_at = timestamp()
        ON MATCH SET p.updated_at = timestamp()
        SET p.org_id = $org_id,
            p.name = r.name,
            p.category = r.category,
            p.uom = r.uom,
            p.weight_kg = r.weight_kg,
            p.volume_m3 = r.volume_m3,
            p.carbon_intensity_per_unit = r.carbon_intensity_per_unit,
            p.is_active = coalesce(r.is_active, true)
        
        WITH p
        MERGE (org:Organization {id: $org_id})
        MERGE (org)-[:HAS_PRODUCT]->(p)
        RETURN count(p) AS cnt
        """
        
        rows_data = [dict(r) for r in products]
        synced = 0
        for i in range(0, len(rows_data), self.batch_size):
            batch = rows_data[i:i + self.batch_size]
            with self.neo4j_driver.session(database=database) as session:
                result = session.run(query, rows=batch, org_id=org_id)
                synced += result.single()["cnt"]
        
        logger.info(f"Synced {synced} products for org {org_id}")
        return synced
    
    def sync_purchase_orders(self, org_id: str, database: str, last_synced_at: Optional[datetime] = None) -> int:
        """Batch sync PurchaseOrders with relationships to Product, Supplier, Facility. Returns count synced."""
        where_clause = "WHERE po.organization_id = :org_id"
        params = {"org_id": org_id}
        if last_synced_at:
            where_clause += " AND po.updated_at > :last_sync"
            params["last_sync"] = last_synced_at
        
        purchase_orders = self.db.execute(
            text(f"""
                SELECT po.id, po.po_id, po.po_line_id, po.supplier_id, po.facility_id, po.product_id,
                       po.quantity, po.unit_price, po.total_cost, po.order_date, 
                       po.expected_delivery_date, po.transport_mode, po.currency, po.status
                FROM purchase_orders po
                {where_clause}
            """),
            params
        ).mappings().all()
        
        if not purchase_orders:
            return 0
        
        query = """
        UNWIND $rows AS r
        MERGE (po:PurchaseOrder {id: r.id})
        ON CREATE SET po.created_at = timestamp()
        ON MATCH SET po.updated_at = timestamp()
        SET po.org_id = $org_id,
            po.po_id = r.po_id,
            po.po_line_id = r.po_line_id,
            po.quantity = r.quantity,
            po.unit_price = r.unit_price,
            po.total_cost = r.total_cost,
            po.order_date = r.order_date,
            po.expected_delivery_date = r.expected_delivery_date,
            po.transport_mode = r.transport_mode,
            po.currency = r.currency,
            po.status = r.status
        
        WITH po, r
        WHERE r.product_id IS NOT NULL
        MERGE (p:Product {id: r.product_id})
        MERGE (po)-[:FOR_PRODUCT]->(p)
        
        WITH po, r
        WHERE r.supplier_id IS NOT NULL
        MERGE (s:Supplier {id: r.supplier_id})
        MERGE (s)-[:RECEIVES_PO]->(po)
        
        WITH po, r
        WHERE r.facility_id IS NOT NULL
        MERGE (f:Facility {id: r.facility_id})
        MERGE (po)-[:FULFILLED_AT]->(f)
        
        RETURN count(po) AS cnt
        """
        
        rows_data = [dict(r) for r in purchase_orders]
        # Convert datetime to ISO string for Neo4j
        for row in rows_data:
            for date_field in ["order_date", "expected_delivery_date"]:
                if row.get(date_field) and hasattr(row[date_field], "isoformat"):
                    row[date_field] = row[date_field].isoformat()
        
        synced = 0
        for i in range(0, len(rows_data), self.batch_size):
            batch = rows_data[i:i + self.batch_size]
            with self.neo4j_driver.session(database=database) as session:
                result = session.run(query, rows=batch, org_id=org_id)
                synced += result.single()["cnt"]
        
        logger.info(f"Synced {synced} purchase orders for org {org_id}")
        return synced
    
    def sync_phase2(self, org_id: str, last_synced_at: Optional[datetime] = None) -> Dict[str, int]:
        """Run Phase 2 ETL: Product → PurchaseOrder (depends on Supplier, Facility from Phase 1)"""
        logger.info(f"Starting Phase 2 sync for organization {org_id}")
        stats = {}
        
        # Ensure organization database exists
        database = self._ensure_database_exists(org_id)
        
        # Update constraints/indexes to include Phase 2 entities
        self.setup_constraints_and_indexes(org_id)
        
        # 1. Products (depends on Organization)
        stats["products"] = self.sync_products(org_id, database, last_synced_at)
        
        # 2. PurchaseOrders (depends on Product, Supplier, Facility)
        stats["purchase_orders"] = self.sync_purchase_orders(org_id, database, last_synced_at)
        
        logger.info(f"Phase 2 sync completed: {stats}")
        return stats
    
    # ========== PHASE 3: Derived Analytics (to be implemented) ==========
    # TODO: compute_derived_relationships, gds_analytics methods

    def _graph_names(self, org_id: str) -> Dict[str, str]:
        safe = org_id.replace('-', '_')
        return {
            "facility": f"org_facility_graph_{safe}",
            "route": f"org_route_graph_{safe}",
        }

    def _graph_exists(self, name: str, database: str) -> bool:
        with self.neo4j_driver.session(database=database) as session:
            rec = session.run("CALL gds.graph.exists($n)", {"n": name}).single()
            return bool(rec and rec.get("exists"))

    def _build_facility_graph(self, org_id: str, database: str, name: str) -> None:
        cy = (
            "MATCH (o:Facility {org_id:$org})-[:ORIGIN]->(rt:Route {org_id:$org})"
            "-[:DESTINATION]->(d:Facility {org_id:$org})\n"
            "RETURN gds.graph.project($name, o, d, { relationshipProperties: {"
            " distance: coalesce(rt.distance_km, 0.0),"
            " duration: coalesce(rt.duration_hours, 0.0),"
            " emission: coalesce(rt.emission_weight, coalesce(rt.distance_km, 0.0)) } }) AS g"
        )
        with self.neo4j_driver.session(database=database) as session:
            session.run("CALL gds.graph.drop($n, false)", {"n": name})
            session.run(cy, {"org": org_id, "name": name}).consume()

    def _build_route_graph_shared_facility(self, org_id: str, database: str, name: str) -> None:
        cy = (
            "MATCH (r1:Route {org_id:$org}), (r2:Route {org_id:$org})\n"
            "WHERE r1.id < r2.id AND (\n"
            "  EXISTS { MATCH (r1)-[:DESTINATION]->(f:Facility {org_id:$org})<-[:DESTINATION]-(r2) } OR\n"
            "  EXISTS { MATCH (r1)-[:ORIGIN]->(f:Facility {org_id:$org})<-[:ORIGIN]-(r2) } OR\n"
            "  EXISTS { MATCH (r1)-[:DESTINATION]->(f:Facility {org_id:$org})<-[:ORIGIN]-(r2) } OR\n"
            "  EXISTS { MATCH (r1)-[:ORIGIN]->(f:Facility {org_id:$org})<-[:DESTINATION]-(r2) } )\n"
            "RETURN gds.graph.project($name, r1, r2, {}) AS g"
        )
        with self.neo4j_driver.session(database=database) as session:
            session.run("CALL gds.graph.drop($n, false)", {"n": name})
            session.run(cy, {"org": org_id, "name": name}).consume()

    def ensure_graphs_for_org(self, org_id: str) -> Dict[str, Any]:
        db = self._ensure_database_exists(org_id)
        names = self._graph_names(org_id)
        built = {}
        # Facility graph
        if not self._graph_exists(names["facility"], db):
            self._build_facility_graph(org_id, db, names["facility"])
            built[names["facility"]] = True
        # Route graph
        if not self._graph_exists(names["route"], db):
            self._build_route_graph_shared_facility(org_id, db, names["route"])
            built[names["route"]] = True
        # Return current catalog
        with self.neo4j_driver.session(database=db) as session:
            data = session.run("CALL gds.graph.list() YIELD graphName, nodeCount, relationshipCount RETURN graphName,nodeCount,relationshipCount").data()
        return {"built": built, "graphs": data}

