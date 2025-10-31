

**VeriEarth** is a comprehensive supply chain sustainability platform that provides environmental monitoring, carbon tracking, and advanced analytics capabilities for supply chain operations.

## 🚀 Features

### Core Functionality
- **Multi-Tenant Architecture**: Organizations with isolated data via `org_id` scoping
- **Data Ingestion**: Support for multiple ERP systems (SAP, Oracle, D365) via CSV uploads
- **Supply Chain Management**: Facilities, Routes, Shipments, Suppliers, Products, Purchase Orders
- **Environmental Data**: Google Earth Engine integration for AQI and pollutant monitoring
- **Knowledge Graph**: Neo4j-powered graph database for relationship mapping
- **Advanced Analytics**: Graph Data Science (GDS) algorithms for network analysis
- **Pattern Mining**: PrefixSpan for frequent emission pattern discovery
- **Caching Layer**: Redis for high-performance data retrieval
- **Authentication**: JWT-based cookie authentication with email verification
- **Security**: CSRF protection, rate limiting, CORS, trusted host middleware

### Analytics Capabilities
- **Betweenness Centrality**: Identify chokepoints in supply chain
- **PageRank**: Find influential hubs and critical routes
- **Louvain Communities**: Detect operational clusters
- **Shortest Path Analysis**: Compare routes by distance, duration, or emission
- **Frequent Pattern Mining**: Discover recurring high-emission routes
- **EO Hotspots**: Flag facilities with high air quality index
- **Dashboard KPIs**: Real-time supply chain metrics

### Data Processing
- **ETL Pipeline**: PostgreSQL → Neo4j synchronization
- **Emission Calculations**: Automatic emission factor application
- **Environmental Enrichment**: Background service for EO data backfill
- **Graph Projections**: On-demand GDS graph building for analytics

## 🏗️ Architecture

### Technology Stack
- **Backend Framework**: FastAPI (Python)
- **Relational Database**: PostgreSQL 15+ with PostGIS and TimescaleDB
- **Graph Database**: Neo4j 5.15 Community with Graph Data Science (GDS) plugin
- **Cache**: Redis 7
- **External APIs**: Google Earth Engine, Google Cloud Storage
- **Authentication**: JWT (cookie-based)
- **Migrations**: Alembic

### Service Architecture
```
┌─────────────┐
│   FastAPI    │ ──┐
│   Backend    │   │
└─────────────┘   │
                  │
┌─────────────┐   │
│  PostgreSQL │ ←─┤── Data Ingestion & Storage
│ (PostGIS)   │   │
└─────────────┘   │
                  │
┌─────────────┐   │
│   Neo4j     │ ←─┤── Knowledge Graph & Analytics
│   (GDS)     │   │
└─────────────┘   │
                  │
┌─────────────┐   │
│   Redis     │ ←─┤── Caching Layer
└─────────────┘   │
                  │
┌─────────────┐   │
│  Google EE  │ ←─┘── Environmental Data
└─────────────┘
```

## 📋 Environment Variables

Copy the example environment file and configure it:

```bash
cp backend/.env.example backend/.env
```

Then edit `backend/.env` with your values. See [backend/.env.example](backend/.env.example) for all required variables.

### Required Variables

**Database:**
- `DATABASE_URL` - PostgreSQL connection string
- `NEO4J_URI` - Neo4j Bolt URI
- `NEO4J_USER` - Neo4j username
- `NEO4J_PASSWORD` - Neo4j password
- `REDIS_URL` - Redis connection URL

**Google Earth Engine:**
- `GEE_PROJECT_ID` - GCP project ID
- `GEE_SERVICE_ACCOUNT_KEY_PATH` - Path to service account JSON key
- `GEE_SERVICE_ACCOUNT_EMAIL` - Service account email

**Security:**
- `JWT_SECRET_KEY` - **CHANGE THIS IN PRODUCTION!** Generate with: `openssl rand -hex 32`

### Optional Variables
- `EO_FACILITY_BUFFER_KM=5` - EO data collection radius (default: 5km)
- `EO_AUTO_ENRICH=true` - Auto-enrich facilities with EO data
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30` - Token expiration (default: 30 minutes)

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.10+
- Docker & Docker Compose (recommended)
- Google Earth Engine service account credentials (for EO features)
- PostgreSQL 15+ with PostGIS (if running without Docker)

### Quick Start with Docker

1. **Clone the repository** (if not already done)
   ```bash
   cd /path/to/veriearth/backend
   ```

2. **Set up environment variables**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your configuration (see Environment Variables section)
   ```

3. **Build and start services**
   ```bash
   docker-compose up -d
   ```

4. **Run database migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Verify services**
   ```bash
   curl http://localhost:8000/health
   ```

### Manual Setup (without Docker)

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL**
   - Ensure PostgreSQL is running with PostGIS extension
   - Create database: `createdb veriearth`

3. **Set up Neo4j**
   - Install Neo4j 5.15 Community Edition
   - Enable GDS plugin: `NEO4J_PLUGINS=["apoc","graph-data-science"]`
   - Start Neo4j service

4. **Set up Redis**
   - Install Redis 7
   - Start Redis service: `redis-server`

5. **Configure environment**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your configuration
   ```

6. **Run migrations**
   ```bash
   alembic upgrade head
   ```

7. **Start the server**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 📁 Project Structure

```
backend/
├── alembic/              # Database migrations
├── aqi/                  # Google Earth Engine integration
│   ├── gee_service.py    # GEE API client
│   └── report_agent.py   # Report generation
├── auth/                 # Authentication & authorization
│   ├── auth.py           # Core auth logic
│   └── cookie_jwt.py     # JWT cookie handling
├── db/                   # Database layer
│   ├── database.py       # SQLAlchemy engine & Neo4j driver
│   ├── models.py         # PostgreSQL ORM models
│   ├── neo4j_service.py # Neo4j client
│   ├── schemas.py        # Pydantic schemas
│   └── supply_chain_schemas.py
├── docs/                 # Documentation
│   ├── analytics/        # Analytics specifications
│   ├── kg/               # Knowledge graph documentation
│   ├── POSTGRES_SCHEMA_FOR_KG.md
│   └── REDIS_CACHING_STRATEGY.md
├── ingestion/            # Data ingestion pipeline
│   ├── file_processor.py # CSV parsing
│   ├── loader.py         # Database loading
│   ├── mappings.py       # ERP field mappings
│   ├── transformers.py   # Data transformation
│   └── validators.py     # Data validation
├── middleware/           # Security middleware
│   └── security.py      # CSRF, rate limiting
├── routes/               # API endpoints
│   ├── auth_routes.py           # Authentication endpoints
│   ├── dashboard_routes.py      # Dashboard KPIs
│   ├── data_management_routes.py # CRUD operations
│   ├── ingestion_routes.py      # Data upload
│   ├── kg_analytics_routes.py   # GDS analytics
│   ├── kg_routes.py             # Knowledge graph queries
│   ├── organization_routes.py   # Organization management
│   ├── report_routes.py         # Report generation
│   └── supply_chain_routes.py   # Supply chain operations
├── services/             # Business logic services
│   ├── background_eo_service.py # EO enrichment background task
│   ├── eo_backfill.py           # EO data backfill
│   ├── kg_etl_service.py        # Postgres → Neo4j ETL
│   ├── prefixspan_service.py    # Pattern mining
│   ├── redis_service.py         # Redis caching
│   └── supply_chain_service.py  # Supply chain operations
├── tests/                # Test suite
│   ├── performance_benchmark.py # Performance testing
│   └── README.md
├── test_data/            # Sample ERP data
├── test_data_small/      # Small test dataset
├── config.py            # Configuration management
├── main.py              # FastAPI application entry
├── docker-compose.yml   # Docker services
├── Dockerfile           # Backend container image
└── requirements.txt     # Python dependencies
```

## 🔌 API Endpoints

### Authentication (`/auth`)
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `GET /auth/verify-email` - Email verification
- `POST /auth/resend-verification` - Resend verification email
- `GET /auth/me` - Get current user profile
- `POST /auth/refresh` - Refresh access token

### Data Ingestion (`/api/ingestion`)
- `POST /api/ingestion/upload` - Upload CSV file
- `POST /api/ingestion/preview` - Preview CSV data
- `POST /api/ingestion/import` - Import data to database

### Knowledge Graph (`/api/kg`)
- `POST /api/kg/organizations/{org_id}/sync` - Sync Postgres → Neo4j
- `GET /api/kg/organizations/{org_id}/graph` - Get graph visualization data
- `GET /api/kg/organizations/{org_id}/status` - Get sync status

### Analytics (`/api/kg/analytics`)
- `POST /api/kg/analytics/graphs/build` - Build GDS graphs
- `GET /api/kg/analytics/graphs/status` - Get graph status
- `DELETE /api/kg/analytics/graphs/clear` - Clear graphs
- `GET /api/kg/analytics/facilities/betweenness` - Facility betweenness
- `GET /api/kg/analytics/facilities/pagerank` - Facility PageRank
- `GET /api/kg/analytics/facilities/communities` - Facility communities
- `GET /api/kg/analytics/routes/betweenness` - Route betweenness
- `GET /api/kg/analytics/routes/pagerank` - Route PageRank
- `GET /api/kg/analytics/routes/communities` - Route communities
- `POST /api/kg/analytics/shortest-path` - Shortest path analysis
- `POST /api/kg/analytics/sequences/prefixspan` - Pattern mining
- `GET /api/kg/analytics/eo/hotspots` - EO hotspots

### Dashboard (`/api`)
- `GET /api/dashboard/kpis` - Key performance indicators
- `GET /api/dashboard/emissions-trend` - Emissions over time
- `GET /api/dashboard/transport-distribution` - Transport mode breakdown
- `GET /api/dashboard/top-routes` - Top routes by emission
- `GET /api/dashboard/carriers` - Carrier statistics
- `GET /api/dashboard/facilities-aqi` - Facility AQI data

### Supply Chain (`/api/supply-chain`)
- `POST /api/supply-chain/organizations/{org_id}/eo/backfill` - EO data backfill

### Data Management (`/api/data`)
- `GET /api/data/stats` - Entity statistics
- `GET /api/data/{entity_type}` - List entities
- `POST /api/data/{entity_type}` - Create entity
- `PUT /api/data/{entity_type}/{id}` - Update entity
- `DELETE /api/data/{entity_type}/{id}` - Delete entity
- `POST /api/data/organizations/{org_id}/clear-all` - Clear all data

### Reports (`/api/report`)
- `POST /api/report/generate` - Generate sustainability report

### Utility
- `GET /` - API root
- `GET /health` - Health check (database, Redis status)
- `GET /csrf-token` - Get CSRF token
- `GET /docs` - Interactive API documentation (Swagger UI)

## 🧪 Testing

### Performance Benchmark
Run the performance benchmark suite to measure API response times:

```bash
cd backend/tests
python performance_benchmark.py
```

Results are saved to `tests/performance_results.json` and include:
- Data ingestion timings
- EO backfill performance
- KG sync metrics
- Analytics endpoint response times
- Cache hit/miss analysis

### Test Data
- **Full dataset**: `test_data/` - Sample data from SAP, Oracle, D365
- **Small dataset**: `test_data_small/` - Minimal test data (suppliers, facilities, products, purchase_orders, routes, shipments)

## 📚 Documentation

### Core Documentation
- **Knowledge Graph**: `backend/docs/kg/` - GDS queries, implementation details, frontend UI reference
- **Analytics**: `backend/docs/analytics/` - Business specs, MVP spec, optimization plan, sample responses
- **Schema**: `backend/docs/POSTGRES_SCHEMA_FOR_KG.md` - PostgreSQL schema documentation
- **Caching**: `backend/docs/REDIS_CACHING_STRATEGY.md` - Redis caching implementation guide

### Key Documents
- `backend/docs/analytics/ANALYTICS_BUSINESS_SPEC.md` - Business significance of analytics
- `backend/docs/analytics/ANALYTICS_MVP_SPEC.md` - MVP implementation specification
- `backend/docs/analytics/ANALYTICS_OPTIMIZATION_PLAN.md` - Future optimization roadmap
- `backend/docs/kg/KG_ANALYTICS_IMPLEMENTATION.md` - Complete analytics implementation guide
- `backend/docs/kg/KNOWLEDGE_GRAPH_INTEGRATION_PLAN.md` - KG integration architecture

## 🔄 Data Flow

### Ingestion Flow
1. User uploads CSV via `/api/ingestion/upload`
2. File is validated and previewed
3. Data is transformed (ERP mappings) and loaded into PostgreSQL
4. Emission factors are applied automatically
5. Cache is invalidated for affected org

### Knowledge Graph Sync Flow
1. Trigger: `/api/kg/organizations/{org_id}/sync`
2. Phase 1: Sync entities (Organization, Supplier, Facility, Route, Shipment, Product, PurchaseOrder, EOReading)
3. Compute emission weights on Route nodes
4. Phase 2: (Future) Real-time updates
5. Cache invalidation for analytics

### Analytics Flow
1. User opens Analytics tab in frontend
2. Frontend calls `/api/kg/analytics/graphs/build`
3. GDS graphs are projected (facility graph, route graph)
4. Analytics endpoints fetch data (with Redis caching)
5. Results displayed in frontend

## 🚨 Security Features

- **CSRF Protection**: Token-based CSRF protection for state-changing operations
- **Rate Limiting**: Per-IP rate limiting via SlowAPI
- **CORS**: Configured for frontend origins only
- **Trusted Hosts**: Validates request host headers
- **JWT Authentication**: Secure cookie-based authentication
- **Email Verification**: Required for account activation
- **Multi-Tenancy**: Data isolation via `org_id` scoping

## 🔧 Development Workflow

### Running Migrations
```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Debugging
- **API Docs**: Visit `http://localhost:8000/docs` for interactive API documentation
- **Health Check**: `curl http://localhost:8000/health`
- **Neo4j Browser**: `http://localhost:7474` (username: `neo4j`, password: `12345678`)
- **Redis CLI**: `docker-compose exec redis redis-cli`

### Code Style
- Follow Python PEP 8
- Use type hints where applicable
- Document complex functions with docstrings

## 🐳 Docker Services

### Service Ports
- **Backend**: `8000`
- **PostgreSQL**: `5432`
- **Neo4j HTTP**: `7474`
- **Neo4j Bolt**: `7687`
- **Redis**: `6379`

### Volumes
- `postgres_data`: PostgreSQL data persistence
- `neo4j_data`: Neo4j data persistence
- `neo4j_logs`: Neo4j logs
- `redis_data`: Redis data persistence

### Health Checks
All services include health checks. Check status:
```bash
docker-compose ps
```

## 📊 Performance

### Caching Strategy
Redis caching is implemented for:
- **GDS Analytics**: 15-minute TTL
- **Dashboard KPIs**: 5-minute TTL
- **PrefixSpan Patterns**: 30-minute TTL
- **EO Hotspots**: 15-minute TTL
- **Graph Queries**: 5-minute TTL

### Expected Performance (with caching)
- **GDS Analytics**: <100ms (cache hit), 3-5s (cache miss)
- **Dashboard KPIs**: <50ms (cache hit), 1-2s (cache miss)
- **Graph Queries**: <50ms (cache hit), 200-500ms (cache miss)

## 🎯 Key Accomplishments

- ✅ **Multi-tenant architecture** with organization-scoped data
- ✅ **Complete data ingestion pipeline** with ERP system support
- ✅ **Knowledge graph integration** with Neo4j and GDS algorithms
- ✅ **Advanced analytics** (Betweenness, PageRank, Louvain, Shortest Path)
- ✅ **Frequent pattern mining** using PrefixSpan algorithm
- ✅ **Environmental data integration** via Google Earth Engine
- ✅ **Redis caching layer** for performance optimization
- ✅ **Email verification** and secure authentication flow
- ✅ **Comprehensive API** with 50+ endpoints
- ✅ **Performance benchmarking** suite
- ✅ **Production-ready** with health checks and monitoring

## 🤝 Contributing

1. Create feature branch from `master`
2. Make changes with tests
3. Run performance benchmarks
4. Update documentation
5. Submit pull request

## 📝 License

See [LICENSE](LICENSE) file in the root of the repository.

## 🔗 Links

- **Frontend Repository**: [Link to frontend repo]
- **API Documentation**: `http://localhost:8000/docs`
- **Neo4j Browser**: `http://localhost:7474`

---

**Built with ❤️ for sustainable supply chains**
