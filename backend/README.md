# VeriEarth Backend

VeriEarth is a comprehensive supply chain sustainability platform that provides environmental monitoring and reporting capabilities.

## Features

- Supply chain management with Neo4j integration
- Data ingestion system for multiple ERP systems (SAP, Oracle, D365)
- Environmental data processing and AQI reporting
- Database migrations and schema management
- RESTful API endpoints for all operations

## Quick Start

1. Install dependencies: `pip3 install -r requirements.txt`
2. Run database migrations: `alembic upgrade head`
3. Start the server: `python3 main.py`

## Test Data

Sample data files are available in the `test_data/` directory for testing different ERP system integrations.
