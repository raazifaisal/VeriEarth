from typing import Dict, List


CANONICAL_HEADERS: Dict[str, List[str]] = {
    "suppliers": [
        "supplier_id","name","address","city","region","country","postal_code",
        "latitude","longitude","tier_level","certifications","contact_email","contact_phone",
    ],
    "facilities": [
        "facility_id","name","type","address","city","region","country","postal_code",
        "latitude","longitude","capacity_tons","time_zone","owner_company",
    ],
    "products": [
        "product_id","name","category","uom","weight_kg","volume_m3","carbon_intensity_per_unit",
    ],
    "purchase_orders": [
        "po_id","po_line_id","supplier_id","facility_id","product_id","quantity","unit_price",
        "total_cost","order_date","expected_delivery_date","transport_mode","currency","status",
    ],
    "sales_orders": [
        "so_id","so_line_id","customer_id","facility_id","product_id","quantity","unit_price",
        "total_amount","order_date","requested_delivery_date","currency","status",
    ],
    "inventory": [
        "facility_id","product_id","quantity_on_hand","quantity_reserved","reorder_point",
        "max_stock_level","last_count_date",
    ],
    "routes": [
        "route_id","origin_facility_id","destination_facility_id","transport_mode","distance_km",
        "duration_hours","intermediate_stops_json","carrier_id",
    ],
    "shipments": [
        "shipment_id","po_id","so_id","origin_facility_id","destination_facility_id","transport_mode",
        "weight_kg","volume_m3","pickup_date","delivery_date","carrier","tracking_number","distance_km",
    ],
    "customers": [
        "customer_id","name","address","city","region","country","postal_code",
        "latitude","longitude","customer_type",
    ],
}


SAP_HEADER_HINTS = {
    "suppliers": {"LIFNR": "supplier_id", "NAME1": "name", "ORT01": "city", "REGIO": "region", "LAND1": "country", "PSTLZ": "postal_code"},
    "products": {"MATNR": "product_id", "MAKTX": "name", "MATKL": "category", "MEINS": "uom"},
    "purchase_orders": {"EBELN": "po_id", "EBELP": "po_line_id", "LIFNR": "supplier_id", "WERKS": "facility_id", "MATNR": "product_id", "MENGE": "quantity", "NETPR": "unit_price", "BEDAT": "order_date"},
    "facilities": {
        "LIFNR": "facility_id",
        "NAME1": "name",
        "WERKS": "facility_id",  # Plant code
        "NAME2": "name",
        "ORT01": "city",
        "REGIO": "region",
        "LAND1": "country",
        "PSTLZ": "postal_code",
        "LATITUDE": "latitude",
        "LONGITUDE": "longitude",
    },
    "shipments": {
        "VBELN": "shipment_id",  # Delivery document
        "VSTEL": "origin_facility_id",  # Shipping point
        "KUNNR": "destination_facility_id",
        "WADAT": "pickup_date",
        "LFDAT": "delivery_date",
        "BTGEW": "weight_kg",
        "GEWEI": "weight_unit",
    }
}


ORACLE_HEADER_HINTS = {
    "suppliers": {"VENDOR_ID": "supplier_id", "VENDOR_NAME": "name", "COUNTRY": "country"},
    "products": {"INVENTORY_ITEM_ID": "product_id", "DESCRIPTION": "name", "PRIMARY_UOM_CODE": "uom"},
    "purchase_orders": {"SEGMENT1": "po_id", "LINE_NUM": "po_line_id", "VENDOR_ID": "supplier_id"},
    "facilities": {
        "LOCATION_ID": "facility_id",
        "LOCATION_CODE": "facility_id",
        "LOCATION_NAME": "name",
        "ADDRESS_LINE_1": "address",
        "CITY": "city",
        "COUNTRY": "country",
        "POSTAL_CODE": "postal_code",
    },
    "shipments": {
        "SHIPMENT_NUM": "shipment_id",
        "SHIPMENT_NUMBER": "shipment_id",
        "FROM_LOCATION": "origin_facility_id",
        "TO_LOCATION": "destination_facility_id",
        "SHIP_DATE": "pickup_date",
        "GROSS_WEIGHT": "weight_kg",
    }
}


D365_HEADER_HINTS = {
    "suppliers": {"AccountNum": "supplier_id", "Name": "name"},
    "facilities": {
        "WarehouseId": "facility_id",
        "WarehouseName": "name",
        "SiteId": "site_id",
    },
    "shipments": {
        "TransferOrderNumber": "shipment_id",
        "FromWarehouse": "origin_facility_id",
        "ToWarehouse": "destination_facility_id",
        "ShipDate": "pickup_date",
    }
}


def guess_mapping(entity: str, headers: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    header_set = set(headers)

    # Try canonical direct match
    for h in CANONICAL_HEADERS.get(entity, []):
        if h in header_set:
            mapping[h] = h

    # Try ERP-specific hints
    for hints in (SAP_HEADER_HINTS.get(entity, {}), ORACLE_HEADER_HINTS.get(entity, {}), D365_HEADER_HINTS.get(entity, {})):
        for src, dest in hints.items():
            if src in header_set and dest not in mapping:
                mapping[src] = dest

    return mapping


