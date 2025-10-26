from sqlalchemy import Column, String, Boolean, DateTime, func, Enum as SAEnum, ForeignKey, Float, Integer, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSON
from geoalchemy2 import Geometry
import uuid
from enum import Enum as PyEnum

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True, unique=True)
    verification_token = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ---------------------
# Multi-tenancy (core)
# ---------------------
class Organization(Base):
    __tablename__ = 'organizations'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    schema_name = Column(String, unique=True, nullable=False)
    industry = Column(String)
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserOrganization(Base):
    __tablename__ = 'user_organizations'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    organization_id = Column(String, ForeignKey('organizations.id'), nullable=False)
    role = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------
# Supply chain enums
# ---------------------
class FacilityType(str, PyEnum):
    MANUFACTURING = "manufacturing"
    WAREHOUSE = "warehouse"
    DISTRIBUTION_CENTER = "distribution_center"
    PORT = "port"
    RETAIL = "retail"


class TransportMode(str, PyEnum):
    ROAD_TRUCK = "road_truck"
    ROAD_VAN = "road_van"
    RAIL_FREIGHT = "rail_freight"
    AIR_CARGO = "air_cargo"
    SEA_CONTAINER = "sea_container"
    SEA_BULK = "sea_bulk"
    PIPELINE = "pipeline"


class ShipmentStatus(str, PyEnum):
    PLANNED = "planned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


# ---------------------
# Supply chain models
# ---------------------
class Facility(Base):
    __tablename__ = 'facilities'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey('organizations.id'), nullable=False)  # For multi-tenancy
    name = Column(String, nullable=False)
    facility_type = Column(SAEnum(FacilityType), nullable=False)
    location = Column(Geometry('POINT', srid=4326))
    address = Column(Text)
    city = Column(String)
    country = Column(String)
    capacity_tons = Column(Float)
    is_active = Column(Boolean, default=True)
    neo4j_node_id = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    location = Column(Geometry('POINT', srid=4326))
    country = Column(String)
    sustainability_score = Column(Float)
    certifications = Column(JSON)
    tier_level = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Route(Base):
    __tablename__ = 'routes'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    origin_facility_id = Column(String, ForeignKey('facilities.id'), nullable=False)
    destination_facility_id = Column(String, ForeignKey('facilities.id'), nullable=False)
    transport_mode = Column(SAEnum(TransportMode), nullable=False)
    distance_km = Column(Float, nullable=False)
    duration_hours = Column(Float)
    is_multi_leg = Column(Boolean, default=False)
    intermediate_stops = Column(JSON)
    is_active = Column(Boolean, default=True)
    neo4j_relationship_id = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EmissionFactor(Base):
    __tablename__ = 'emission_factors'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transport_mode = Column(SAEnum(TransportMode), nullable=False)
    vehicle_type = Column(String)
    emission_factor_kg_co2_per_ton_km = Column(Float, nullable=False)
    source = Column(String)
    region = Column(String)
    effective_date = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Shipment(Base):
    __tablename__ = 'shipments'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    route_id = Column(String, ForeignKey('routes.id'), nullable=False)
    weight_kg = Column(Float, nullable=False)
    volume_m3 = Column(Float)

    cost_per_kg = Column(Float)
    total_cost = Column(Float, nullable=False)

    emission_factor_kg_co2_per_ton_km = Column(Float)
    emissions_per_kg = Column(Float)
    total_emissions_kg_co2 = Column(Float, nullable=False)

    shipment_date = Column(DateTime, nullable=False)
    planned_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)

    status = Column(SAEnum(ShipmentStatus), default=ShipmentStatus.PLANNED)
    carrier = Column(String)
    tracking_number = Column(String)

    extra_metadata = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class FacilityEnvironmentalData(Base):
    __tablename__ = 'facility_environmental_data'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    facility_id = Column(String, ForeignKey('facilities.id'), nullable=False)
    organization_id = Column(String, ForeignKey('organizations.id'))  # For isolation
    captured_at = Column(DateTime, nullable=False)
    
    # Pollutant measurements (averages from EO data)
    no2_value = Column(Float)
    co_value = Column(Float)
    ch4_value = Column(Float)
    so2_value = Column(Float)
    aod_value = Column(Float)
    o3_value = Column(Float)
    
    # Derived metrics
    aqi_score = Column(Float)
    pollution_level = Column(String)  # good, moderate, unhealthy_sensitive, unhealthy, hazardous
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
