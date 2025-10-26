from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

import auth.auth
from db.database import SessionLocal, engine
import db.models, db.schemas, db.crud
import auth
from routes import auth_routes, report_routes
from routes import ingestion_routes
from routes import supply_chain_routes

db.models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include routes
app.include_router(auth_routes.router, tags=["auth"])
app.include_router(report_routes.router, prefix="/api/report", tags=["report"])
app.include_router(ingestion_routes.router)
app.include_router(supply_chain_routes.router)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register", response_model=db.schemas.UserOut)
def register(user: db.schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.crud.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    created_user = db.crud.create_user(db, user)
    return created_user

@app.post("/login", response_model=db.schemas.Token)
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/google")
def google_oauth_redirect():
    return {"url": auth.get_google_oauth_url()}

@app.get("/auth/google/callback")
async def google_oauth_callback(code: str, db: Session = Depends(get_db)):
    google_user_info = await auth.auth.fetch_google_user_info(code)
    user = auth.auth.register_or_login_google_user(db, google_user_info)
    access_token = auth.auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}