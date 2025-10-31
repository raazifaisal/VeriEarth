from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os

from db.database import engine
import db.models
from routes import auth_routes, report_routes, ingestion_routes, supply_chain_routes, data_management_routes, dashboard_routes, kg_routes, organization_routes
from routes import kg_analytics_routes
from middleware.security import SecurityMiddleware, generate_csrf_token

# Create database tables
db.models.Base.metadata.create_all(bind=engine)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="VeriEarth API",
    description="Supply Chain Carbon Intelligence Platform",
    version="1.0.0"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security middleware (order matters!)
# Apply CORS first so CORS headers are present even when inner middleware raises errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js frontend
        "http://127.0.0.1:3000",  # Alternative localhost
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# Custom security middleware for CSRF protection
app.add_middleware(
    SecurityMiddleware,
    secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
)

# Include routers
app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
app.include_router(report_routes.router, prefix="/api/report", tags=["Reports"])
app.include_router(ingestion_routes.router, prefix="/api/ingestion", tags=["Data Ingestion"])
app.include_router(supply_chain_routes.router, prefix="/api", tags=["Supply Chain"])
app.include_router(data_management_routes.router, prefix="/api/data", tags=["Data Management"])
app.include_router(dashboard_routes.router, prefix="/api", tags=["Dashboard"])
app.include_router(kg_routes.router, prefix="/api/kg", tags=["Knowledge Graph"])
app.include_router(kg_analytics_routes.router, prefix="/api/kg/analytics", tags=["KG Analytics"])
app.include_router(organization_routes.router, prefix="/api", tags=["Organization"])

@app.get("/")
def root():
    return {
        "message": "VeriEarth API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/csrf-token")
def get_csrf_token():
    """Get CSRF token for frontend"""
    return {"csrf_token": generate_csrf_token()}