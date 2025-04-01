from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import uvicorn
import auth.auth
from db.database import SessionLocal, engine
import db.models, db.schemas, db.crud
import auth
from routes import auth_routes, report_routes

# Create database tables
db.models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include routes
app.include_router(auth_routes.router, tags=["auth"])
app.include_router(report_routes.router, prefix="/api/report", tags=["report"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



if __name__ == "__main__":
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        workers=1     # Number of worker processes
    )