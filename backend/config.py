import os
from dotenv import load_dotenv

load_dotenv()

# Existing config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/veriearth")

# Neo4j config (add these)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

# EO correlation settings
EO_FACILITY_BUFFER_KM = int(os.getenv("EO_FACILITY_BUFFER_KM", 5))
EO_AUTO_ENRICH = os.getenv("EO_AUTO_ENRICH", "true").lower() == "true"
