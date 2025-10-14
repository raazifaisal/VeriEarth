from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class FacilityTypeEnum(str, Enum):
    MANUFACTURING = "manufacturing"
    WAREHOUSE = "warehouse"
    DISTRIBUTION_CENTER = "distribution_center"
    PORT = "port"
    RETAIL = "retail"


class TransportModeEnum(str, Enum):
    ROAD_TRUCK = "road_truck"
    ROAD_VAN = "road_van"
    RAIL_FREIGHT = "rail_freight"
    AIR_CARGO = "air_cargo"
    SEA_CONTAINER = "sea_container"
    SEA_BULK = "sea_bulk"
    PIPELINE = "pipeline"


class ShipmentStatusEnum(str, Enum):
    PLANNED = "planned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class FacilityCreate(BaseModel):
    name: str
    facility_type: FacilityTypeEnum
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None
    city: Optional[str] = None
    country: str
    capacity_tons: Optional[float] = None


class FacilityOut(BaseModel):
    id: str
    name: str
    facility_type: FacilityTypeEnum
    latitude: float
    longitude: float
    city: Optional[str]
    country: str
    is_active: bool
    created_at: datetime


class RouteCreate(BaseModel):
    origin_facility_id: str
    destination_facility_id: str
    transport_mode: TransportModeEnum
    distance_km: float = Field(..., gt=0)
    duration_hours: Optional[float] = None
    intermediate_stops: Optional[List[str]] = None


class RouteOut(BaseModel):
    id: str
    origin_facility_id: str
    destination_facility_id: str
    transport_mode: TransportModeEnum
    distance_km: float
    is_multi_leg: bool
    created_at: datetime


class ShipmentCreate(BaseModel):
    route_id: str
    weight_kg: float = Field(..., gt=0)
    volume_m3: Optional[float] = None
    cost_per_kg: Optional[float] = None
    total_cost: float = Field(..., ge=0)
    emissions_per_kg: Optional[float] = None
    total_emissions_kg_co2: float = Field(..., ge=0)
    shipment_date: datetime
    planned_delivery_date: Optional[datetime] = None
    carrier: Optional[str] = None


class ShipmentOut(BaseModel):
    id: str
    route_id: str
    weight_kg: float
    total_cost: float
    total_emissions_kg_co2: float
    shipment_date: datetime
    status: ShipmentStatusEnum
    created_at: datetime


