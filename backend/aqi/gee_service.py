import ee
from datetime import datetime
from typing import List, Dict, Literal
import os
import json
from config import GEE_PROJECT_ID, GEE_SERVICE_ACCOUNT_KEY_PATH, GEE_SERVICE_ACCOUNT_EMAIL

# Initialize Earth Engine
def initialize_earth_engine():
    try:
        # First, try to use default authentication (user account) - this works for development
        # Check if already initialized
        try:
            ee.Number(1).getInfo()
        except:
            # Not initialized, so initialize with default auth
            ee.Initialize(project=GEE_PROJECT_ID)
            print(f"✅ Earth Engine Initialized with default auth for project '{GEE_PROJECT_ID}'")
            
    except Exception as e:
        print(f"⚠️ Default auth failed, trying service account...: {e}")
        try:
            # Fallback to service account if default auth fails
            gee_service_account_key = os.getenv('GEE_SERVICE_ACCOUNT_KEY')
            
            if gee_service_account_key:
                # Parse JSON from environment variable
                if isinstance(gee_service_account_key, str):
                    service_account_info = json.loads(gee_service_account_key)
                else:
                    service_account_info = gee_service_account_key
                
                # Use the correct initialization method
                credentials = ee.ServiceAccountCredentials(
                    email=service_account_info['client_email'],
                    key_file=None,
                    key_data=json.dumps(service_account_info)
                )
                ee.Initialize(credentials, project=GEE_PROJECT_ID)
                print(f"✅ Earth Engine Initialized with service account from env for project '{GEE_PROJECT_ID}'")
            
            # Check if we have service account file path
            elif GEE_SERVICE_ACCOUNT_KEY_PATH and os.path.exists(GEE_SERVICE_ACCOUNT_KEY_PATH):
                # Use service account file authentication - the correct way
                credentials = ee.ServiceAccountCredentials(
                    email=GEE_SERVICE_ACCOUNT_EMAIL,
                    key_file=GEE_SERVICE_ACCOUNT_KEY_PATH
                )
                ee.Initialize(credentials, project=GEE_PROJECT_ID)
                print(f"✅ Earth Engine Initialized with service account file for project '{GEE_PROJECT_ID}'")
            
            else:
                raise Exception("No authentication method available")
                
        except Exception as e2:
            print(f"⚠️ Earth Engine Initialization Failed: {e2}")
            print("💡 To fix this, you need to:")
            print("   1. Run: earthengine authenticate (for development)")
            print("   2. Or set up service account credentials")
            raise e2

# Define the pollutants and their datasets
POLLUTANTS = [
    {'name': 'NO2', 'dataset': 'COPERNICUS/S5P/OFFL/L3_NO2', 'band': 'NO2_column_number_density'},
    {'name': 'CO', 'dataset': 'COPERNICUS/S5P/OFFL/L3_CO', 'band': 'CO_column_number_density'},
    {'name': 'HCHO', 'dataset': 'COPERNICUS/S5P/OFFL/L3_HCHO', 'band': 'tropospheric_HCHO_column_number_density'},
    {'name': 'CH4', 'dataset': 'COPERNICUS/S5P/OFFL/L3_CH4', 'band': 'CH4_column_volume_mixing_ratio_dry_air'},
    {'name': 'SO2', 'dataset': 'COPERNICUS/S5P/OFFL/L3_SO2', 'band': 'SO2_column_number_density'},
    {'name': 'AOD', 'dataset': 'MODIS/061/MCD19A2_GRANULES', 'band': 'Optical_Depth_047'},
    {'name': 'O3', 'dataset': 'COPERNICUS/S5P/OFFL/L3_O3', 'band': 'O3_column_number_density'},
]

def generate_date_ranges(start_date: ee.Date, end_date: ee.Date, interval: Literal['day', 'week', 'month', 'year']):
    """ Generate date ranges based on the interval type. """
    ranges = []
    current = start_date

    while current.millis().lt(end_date.millis()).getInfo():
        if interval == 'day':
            next_date = current.advance(1, 'day')
        elif interval == 'week':
            next_date = current.advance(1, 'week')
        elif interval == 'month':
            next_date = current.advance(1, 'month')
        elif interval == 'year':
            next_date = current.advance(1, 'year')
        else:
            raise ValueError(f"Unsupported interval: {interval}")

        ranges.append((current, next_date))
        current = next_date

    return ranges

def fetch_pollutant_data(aoi: Dict, start_date: str, end_date: str, interval: Literal['day', 'week', 'month', 'year']) -> List[Dict]:
    initialize_earth_engine()

    print("\n🚀 Fetching pollutant data for AOI and time range:")
    print(f"   Start Date: {start_date}")
    print(f"   End Date: {end_date}")
    print(f"   Interval: {interval}")
    print(f"   AOI: {aoi['coordinates']}")

    aoi_geometry = ee.Geometry.Polygon(aoi['coordinates'])
    start_date = ee.Date(start_date)
    end_date = ee.Date(end_date)

    date_ranges = generate_date_ranges(start_date, end_date, interval)
    print(f"📆 Total {interval}s in range: {len(date_ranges)}")

    all_data = []

    pollutant_count = 0
    for pollutant in POLLUTANTS:
        pollutant_count += 1
        print(f"\n{'='*60}")
        print(f"🔎 [{pollutant_count}/{len(POLLUTANTS)}] Processing pollutant: {pollutant['name']}")
        print(f"   Dataset: {pollutant['dataset']}")
        print(f"   Band: {pollutant['band']}")
        print(f"{'='*60}")

        try:
            collection = ee.ImageCollection(pollutant['dataset']) \
                .filterBounds(aoi_geometry) \
                .filterDate(start_date, end_date) \
                .select(pollutant['band'])

            collection_size = collection.size().getInfo()
            print(f"   ✅ Collection Filtered - Found {collection_size} images for {pollutant['name']}")

            period_count = 0
            for start, end in date_ranges:
                period_count += 1
                if interval == 'day':
                    period_label = start.format('YYYY-MM-dd').getInfo()
                elif interval == 'week':
                    year = start.get('year').format().getInfo()
                    week = start.get('week').format().getInfo()  # Week 1 to 52
                    period_label = f"{year}-W{week.zfill(2)}"
                elif interval == 'month':
                    period_label = start.format('YYYY-MM').getInfo()
                elif interval == 'year':
                    period_label = start.format('YYYY').getInfo()
                else:
                    raise ValueError(f"Unsupported interval: {interval}")

                print(f"\n   📊 [{period_count}/{len(date_ranges)}] Processing {interval}: {period_label}")
                print(f"      ⏳ Fetching data...")

                try:
                    period_image = collection.filterDate(start, end).mean().clip(aoi_geometry)

                    print(f"      ⏳ Computing mean value...")
                    mean_value = period_image.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=aoi_geometry,
                        scale=1000,
                        maxPixels=1e13
                    ).get(pollutant['band']).getInfo()

                    print(f"      ✅ SUCCESS: {pollutant['name']} = {mean_value} for {period_label}")
                    
                    all_data.append({
                        "period": period_label,
                        "pollutant": pollutant['name'],
                        "value": mean_value,
                        "interval": interval
                    })

                except Exception as e:
                    print(f"      ⚠️ FAILED: {pollutant['name']} for {period_label}: {e}")
                    all_data.append({
                        "period": period_label,
                        "pollutant": pollutant['name'],
                        "value": None,
                        "interval": interval
                    })
                
                print(f"      ⏱️  Progress: {(period_count/len(date_ranges)*100):.1f}% complete for {pollutant['name']}")
        except Exception as e:
            print(f"   ❌ Error processing pollutant {pollutant['name']}: {e}")
            # Add None values for all periods for this pollutant
            for start, end in date_ranges:
                if interval == 'day':
                    period_label = start.format('YYYY-MM-dd').getInfo()
                elif interval == 'week':
                    year = start.get('year').format().getInfo()
                    week = start.get('week').format().getInfo()
                    period_label = f"{year}-W{week.zfill(2)}"
                elif interval == 'month':
                    period_label = start.format('YYYY-MM').getInfo()
                elif interval == 'year':
                    period_label = start.format('YYYY').getInfo()
                
                all_data.append({
                    "period": period_label,
                    "pollutant": pollutant['name'],
                    "value": None,
                    "interval": interval
                })

    print("\n✅ Data fetching complete. Total records:", len(all_data))
    return all_data


# # Test block
# if __name__ == "__main__":
#     # Define the AOI (Area of Interest)
#     aoi = {
#         "type": "Polygon",
#         "coordinates": [
#             [
#                 [77.2090, 28.6139],  # Point 1
#                 [77.2100, 28.6139],  # Point 2
#                 [77.2100, 28.6150],  # Point 3
#                 [77.2090, 28.6150],  # Point 4
#                 [77.2090, 28.6139]   # Close the polygon (same as Point 1)
#             ]
#         ]
#     }

#     # Define the time range and interval
#     start_date = "2023-01-01"
#     end_date = "2023-12-31"
#     interval = "month"  # Can be 'day', 'week', 'month', or 'year'

#     # Fetch pollutant data
#     print("🚀 Starting pollutant data fetch...")
#     data = fetch_pollutant_data(
#         aoi=aoi,
#         start_date=start_date,
#         end_date=end_date,
#         interval=interval
#     )

#     # Print the fetched data
#     print("\n📊 Fetched Data:")
#     for record in data:
#         print(record)