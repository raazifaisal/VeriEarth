from sqlalchemy.orm import Session
from db.models import Facility, Route, Shipment, TransportMode
from db.neo4j_service import Neo4jService
from db.supply_chain_schemas import FacilityCreate, RouteCreate, ShipmentCreate
import logging

logger = logging.getLogger(__name__)


class SupplyChainService:
    def __init__(self, db: Session, neo4j: Neo4jService, organization_id: str):
        self.db = db
        self.neo4j = neo4j
        self.organization_id = organization_id

    def create_facility(self, payload: FacilityCreate) -> Facility:
        try:
            pg_facility = Facility(
                organization_id=self.organization_id,
                name=payload.name,
                facility_type=payload.facility_type.value,
                location=f'POINT({payload.longitude} {payload.latitude})',
                address=payload.address,
                city=payload.city,
                country=payload.country,
                capacity_tons=payload.capacity_tons,
            )
            self.db.add(pg_facility)
            self.db.commit()
            self.db.refresh(pg_facility)

            self.neo4j.create_facility_node(
                {
                    'id': pg_facility.id,
                    'name': payload.name,
                    'type': payload.facility_type.value,
                    'latitude': payload.latitude,
                    'longitude': payload.longitude,
                    'city': payload.city,
                    'country': payload.country,
                    'capacity_tons': payload.capacity_tons,
                },
                self.organization_id,
            )

            return pg_facility
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create facility: {e}")
            raise

    def create_route(self, payload: RouteCreate) -> Route:
        try:
            pg_route = Route(
                origin_facility_id=payload.origin_facility_id,
                destination_facility_id=payload.destination_facility_id,
                transport_mode=payload.transport_mode.value,
                distance_km=payload.distance_km,
                duration_hours=payload.duration_hours,
                is_multi_leg=bool(payload.intermediate_stops),
                intermediate_stops=payload.intermediate_stops,
            )
            self.db.add(pg_route)
            self.db.commit()
            self.db.refresh(pg_route)

            self.neo4j.create_route_relationship(
                {
                    'origin_id': payload.origin_facility_id,
                    'dest_id': payload.destination_facility_id,
                    'route_id': pg_route.id,
                    'transport_mode': payload.transport_mode.value,
                    'distance_km': payload.distance_km,
                    'duration_hours': payload.duration_hours,
                    'emission_factor': None,
                },
                self.organization_id,
            )

            return pg_route
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create route: {e}")
            raise

    def create_shipment(self, payload: ShipmentCreate) -> Shipment:
        try:
            pg_shipment = Shipment(
                route_id=payload.route_id,
                weight_kg=payload.weight_kg,
                volume_m3=payload.volume_m3,
                cost_per_kg=payload.cost_per_kg,
                total_cost=payload.total_cost,
                emissions_per_kg=payload.emissions_per_kg,
                total_emissions_kg_co2=payload.total_emissions_kg_co2,
                shipment_date=payload.shipment_date,
                planned_delivery_date=payload.planned_delivery_date,
            )
            self.db.add(pg_shipment)
            self.db.commit()
            self.db.refresh(pg_shipment)
            return pg_shipment
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create shipment: {e}")
            raise


