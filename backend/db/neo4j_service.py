from neo4j import GraphDatabase
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class Neo4jService:
    def __init__(self, uri: str, user: str, password: str):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def _session(self):
        return self._driver.session()

    def create_facility_node(self, facility_data: Dict[str, Any], organization_id: str):
        """Create a Facility node."""
        query = (
            """
            CREATE (f:Facility {
                id: $id,
                name: $name,
                type: $type,
                latitude: $latitude,
                longitude: $longitude,
                city: $city,
                country: $country,
                capacity_tons: $capacity_tons,
                organization_id: $organization_id,
                is_active: true
            })
            RETURN f.id AS id
            """
        )
        with self._session() as session:
            result = session.run(query, **facility_data, organization_id=organization_id)
            record = result.single()
            return record["id"] if record else None

    def create_route_relationship(self, route_data: Dict[str, Any], organization_id: str):
        """Create a ROUTE relationship between two facilities."""
        query = (
            """
            MATCH (origin:Facility {id: $origin_id, organization_id: $organization_id})
            MATCH (dest:Facility {id: $dest_id, organization_id: $organization_id})
            CREATE (origin)-[r:ROUTE {
                id: $route_id,
                transport_mode: $transport_mode,
                distance_km: $distance_km,
                duration_hours: $duration_hours,
                emission_factor: $emission_factor,
                organization_id: $organization_id,
                is_active: true
            }]->(dest)
            RETURN r.id AS id
            """
        )
        with self._session() as session:
            result = session.run(query, **route_data, organization_id=organization_id)
            record = result.single()
            return record["id"] if record else None

    def find_lowest_emission_paths(
        self,
        origin_id: str,
        destination_id: str,
        organization_id: str,
        max_hops: int = 5,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find candidate paths ordered by total estimated emissions."""
        query = (
            """
            MATCH path = (o:Facility {id: $origin_id, organization_id: $org_id})
                         -[:ROUTE*1..$max_hops]->
                         (d:Facility {id: $destination_id, organization_id: $org_id})
            WHERE ALL(r IN relationships(path) WHERE r.is_active = true)
            WITH path,
                 reduce(dist = 0.0, r IN relationships(path) | dist + coalesce(r.distance_km, 0.0)) AS total_distance,
                 reduce(emis = 0.0, r IN relationships(path) | emis + coalesce(r.emission_factor, 0.0) * coalesce(r.distance_km, 0.0)) AS total_emissions
            RETURN path AS path,
                   total_distance AS total_distance,
                   total_emissions AS total_emissions
            ORDER BY total_emissions ASC
            LIMIT $limit
            """
        )
        with self._session() as session:
            result = session.run(
                query,
                origin_id=origin_id,
                destination_id=destination_id,
                org_id=organization_id,
                max_hops=max_hops,
                limit=limit,
            )
            return [r.data() for r in result]

    def create_environmental_snapshot(self, facility_id: str, eo_data: dict):
        """Store EO data as graph node linked to facility"""
        import uuid
        
        query = '''
        MATCH (f:Facility {id: $facility_id})
        CREATE (e:EnvironmentalSnapshot {
            id: $snapshot_id,
            facility_id: $facility_id,
            captured_at: datetime($captured_at),
            NO2: $no2,
            CO: $co,
            CH4: $ch4,
            SO2: $so2,
            AOD: $aod,
            O3: $o3,
            aqi_score: $aqi_score,
            pollution_level: $pollution_level
        })
        CREATE (f)-[:HAS_ENVIRONMENTAL_DATA {captured_at: datetime($captured_at)}]->(e)
        RETURN e.id AS id
        '''
        
        with self._session() as session:
            result = session.run(query,
                snapshot_id=str(uuid.uuid4()),
                facility_id=facility_id,
                captured_at=datetime.now().isoformat(),
                no2=eo_data.get("no2_avg"),
                co=eo_data.get("co_avg"),
                ch4=eo_data.get("ch4_avg"),
                so2=eo_data.get("so2_avg"),
                aod=eo_data.get("aod_avg"),
                o3=eo_data.get("o3_avg"),
                aqi_score=eo_data.get("aqi_score"),
                pollution_level=eo_data.get("pollution_level")
            )
            record = result.single()
            return record["id"] if record else None
    
    def find_high_pollution_facilities(self, org_id: str, threshold: float = 100):
        """Query facilities in high-pollution areas"""
        query = '''
        MATCH (f:Facility {organization_id: $org_id})-[:HAS_ENVIRONMENTAL_DATA]->(e:EnvironmentalSnapshot)
        WHERE e.aqi_score > $threshold
        WITH f, e
        ORDER BY e.captured_at DESC
        RETURN f.id AS facility_id, f.name AS facility_name, 
               e.aqi_score AS aqi_score, e.pollution_level AS pollution_level
        LIMIT 50
        '''
        
        with self._session() as session:
            result = session.run(query, org_id=org_id, threshold=threshold)
            return [r.data() for r in result]


