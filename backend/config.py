import os
from dotenv import load_dotenv

load_dotenv()

# Existing config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/veriearth")

# Neo4j config
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

# Google Earth Engine Configuration
GEE_PROJECT_ID = os.getenv("GEE_PROJECT_ID", "veriearth-468117")
GEE_SERVICE_ACCOUNT_KEY_PATH = os.getenv("GEE_SERVICE_ACCOUNT_KEY_PATH")
GEE_SERVICE_ACCOUNT_EMAIL = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL")

# EO correlation settings
EO_FACILITY_BUFFER_KM = int(os.getenv("EO_FACILITY_BUFFER_KM", 5))
EO_AUTO_ENRICH = os.getenv("EO_AUTO_ENRICH", "true").lower() == "true"

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
