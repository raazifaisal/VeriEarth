from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
import logging
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from auth.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    fetch_google_user_info,
    register_or_login_google_user,
    get_google_oauth_url,
    generate_verification_token,
    send_verification_email,
    validate_refresh_token,
    get_current_user,
    get_current_user_from_cookies,
    hash_password,
    verify_password,
)
from auth.cookie_jwt import CookieJWTService
from middleware.security import rate_limit_auth
from db.schemas import UserCreate
from db.database import get_db
from db.crud import get_user_by_email, get_user_by_verification_token, create_regular_user
from db.models import Organization, UserOrganization, User
import uuid
from jwt import PyJWKError

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

@router.post("/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        # If user exists but isn't verified yet, resend verification instead of blocking
        if not existing_user.is_verified:
            verification_token = generate_verification_token()
            existing_user.verification_token = verification_token
            db.commit()
            try:
                await send_verification_email(existing_user.email, verification_token)
            except Exception as e:
                logger.exception("Failed to resend verification email: %s", e)
            return {"msg": "Account exists but not verified. Verification email resent if possible."}
        raise HTTPException(status_code=400, detail="Email already registered")

    user = create_regular_user(db, user_data, generate_verification_token=generate_verification_token)

    # Generate and set verification token
    verification_token = generate_verification_token()
    user.verification_token = verification_token
    
    # Create default organization for the user
    org_name = user_data.full_name if user_data.full_name else user_data.email.split('@')[0]
    organization = Organization(
        id=str(uuid.uuid4()),
        name=f"{org_name}'s Organization",
        schema_name=f"org_{user.id[:8]}",
        is_active=True
    )
    db.add(organization)
    db.flush()  # Flush to get the organization ID
    
    # Link user to organization
    user_org = UserOrganization(
        id=str(uuid.uuid4()),
        user_id=user.id,
        organization_id=organization.id,
        role="admin"
    )
    db.add(user_org)
    db.commit()

    # Send verification email (best-effort; do not fail registration)
    try:
        await send_verification_email(user.email, verification_token)
    except Exception as e:
        logger.exception("Failed to send verification email: %s", e)

    return {"msg": "Please check your email to verify your account"}

@router.post("/login")
def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")
    # Block login until email is verified
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account not verified")

    # Set httpOnly cookies instead of returning tokens
    CookieJWTService.set_auth_cookies(response, user.id, user.email)

    return {"msg": "Login successful"}

@router.get("/google/login")
def google_login():
    return {"url": get_google_oauth_url()}

@router.get("/google/callback")
async def google_callback(response: Response, code: str, db: Session = Depends(get_db)):
    google_user_info = await fetch_google_user_info(code)
    user = register_or_login_google_user(db, google_user_info)

    # Set httpOnly cookies instead of returning tokens
    CookieJWTService.set_auth_cookies(response, user.id, user.email)

    return {"msg": "Google login successful"}

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    # First check if token exists
    user = get_user_by_verification_token(db, token)

    if not user:
        # Token doesn't exist - check if user is already verified (idempotent)
        # This handles the case where verification link is clicked twice
        # We'll check by email if we can extract it, but for security we'll just return error
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    # If user is already verified, return success (idempotent)
    if user.is_verified:
        return {"msg": "Email already verified. You can sign in now."}

    # Verify the user
    user.is_active = True
    user.is_verified = True  # Mark user as verified
    user.verification_token = None
    db.commit()

    return {"msg": "Email verified successfully"}

class ResendVerificationRequest(BaseModel):
    email: str

@router.post("/resend-verification")
async def resend_verification(request_data: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend verification email for an unverified user"""
    user = get_user_by_email(db, request_data.email)
    
    if not user:
        # Don't reveal if email exists or not (security best practice)
        return {"msg": "If an account exists with this email, a verification email has been sent."}
    
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")
    
    # Generate new verification token
    verification_token = generate_verification_token()
    user.verification_token = verification_token
    db.commit()
    
    # Send verification email (best-effort)
    try:
        await send_verification_email(user.email, verification_token)
        return {"msg": "Verification email sent. Please check your inbox."}
    except Exception as e:
        logger.exception("Failed to resend verification email: %s", e)
        raise HTTPException(status_code=500, detail="Failed to send verification email. Please try again later.")

@router.post("/refresh")
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """Refresh access token using refresh token from cookie"""
    refresh_token = CookieJWTService.get_token_from_cookies(request, "refresh")
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")
    
    try:
        payload = CookieJWTService.verify_token(refresh_token, "refresh")
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        email = payload.get("email")
        user = get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Set new access token cookie
        CookieJWTService.set_auth_cookies(response, user.id, user.email)

        return {"msg": "Token refreshed successfully"}

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

@router.post("/logout")
def logout(response: Response):
    """Logout user by clearing cookies"""
    CookieJWTService.clear_auth_cookies(response)
    return {"msg": "Logged out successfully"}

@router.get("/me")
async def get_me(request: Request, db: Session = Depends(get_db)):
    """Get current user profile and their organizations - allows unverified users to check status"""
    current_user = get_current_user_from_cookies(request, db, require_verified=False)
    # Get user's organizations
    user_orgs = db.query(UserOrganization).filter(UserOrganization.user_id == current_user.id).all()
    org_ids = [uo.organization_id for uo in user_orgs]
    organizations = db.query(Organization).filter(Organization.id.in_(org_ids)).all() if org_ids else []
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "organizations": [
            {
                "id": org.id,
                "name": org.name,
                "role": next((uo.role for uo in user_orgs if uo.organization_id == org.id), None)
            }
            for org in organizations
        ]
    }

class OrganizationCreate(BaseModel):
    name: str

@router.post("/organizations")
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_user_from_cookies),
    db: Session = Depends(get_db)
):
    """Create a new organization for the current user"""
    # Create organization
    organization = Organization(
        id=str(uuid.uuid4()),
        name=org_data.name,
        schema_name=f"org_{uuid.uuid4().hex[:8]}",
        is_active=True
    )
    db.add(organization)
    db.flush()
    
    # Link user to organization as admin
    user_org = UserOrganization(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        organization_id=organization.id,
        role="admin"
    )
    db.add(user_org)
    db.commit()
    db.refresh(organization)
    
    return {
        "id": organization.id,
        "name": organization.name,
        "role": "admin"
    }

# ---- Profile Update ----
class ProfileUpdate(BaseModel):
    full_name: str | None = None

@router.put("/me")
async def update_me(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user_from_cookies),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    db.commit()
    return {"status": "ok"}


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

@router.post("/me/password")
async def change_password(
    body: PasswordChange,
    current_user: User = Depends(get_current_user_from_cookies),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.hashed_password:
        # Disallow password change for pure OAuth accounts without local password
        raise HTTPException(status_code=400, detail="Password change not available for this account")
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Invalid current password")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"status": "ok"}
