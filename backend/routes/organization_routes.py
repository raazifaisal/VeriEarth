from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Organization
from auth.auth import get_current_user_from_cookies, hash_password, verify_password

router = APIRouter()


class OrgUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    description: str | None = None
    address: str | None = None
    details: dict | None = None


@router.get("/organizations/{org_id}")
def get_organization(org_id: str, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookies)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {
        "id": org.id,
        "name": org.name,
        "industry": org.industry,
        "description": org.description,
        "address": org.address,
        "details": org.details,
        "subscription_tier": org.subscription_tier,
        "is_active": org.is_active,
    }


@router.put("/organizations/{org_id}")
def update_organization(org_id: str, payload: OrgUpdate, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookies)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if payload.name is not None:
        org.name = payload.name
    if payload.industry is not None:
        org.industry = payload.industry
    if payload.description is not None:
        org.description = payload.description
    if payload.address is not None:
        org.address = payload.address
    if payload.details is not None:
        org.details = payload.details
    db.commit()
    db.refresh(org)
    return {"status": "ok"}


class SudoPasswordSet(BaseModel):
    password: str
    current_password: str | None = None


@router.post("/organizations/{org_id}/sudo-password")
def set_sudo_password(org_id: str, body: SudoPasswordSet, db: Session = Depends(get_db), user=Depends(get_current_user_from_cookies)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    # If already set, require current_password
    if org.sudo_password_hash:
        if not body.current_password or not verify_password(body.current_password, org.sudo_password_hash):
            raise HTTPException(status_code=403, detail="Invalid current password")
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")
    org.sudo_password_hash = hash_password(body.password)
    db.commit()
    return {"status": "ok"}


