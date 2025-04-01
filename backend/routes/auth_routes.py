from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from auth.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    fetch_google_user_info,
    register_or_login_google_user,
    get_google_oauth_url,
    generate_verification_token,
    send_verification_email,
    validate_refresh_token
)
from db.schemas import UserCreate
from db.database import get_db
from db.crud import get_user_by_email, get_user_by_verification_token, create_regular_user
from jwt import PyJWKError

router = APIRouter()
@router.post("/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(db, user_data.email)

    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(
                status_code=400,
                detail="Email already registered. Please log in."
            )
        else:
            # Resend verification email if user exists but is not verified
            await send_verification_email(existing_user.email, existing_user.verification_token)
            return {"msg": "Email already registered but not verified. A new verification email has been sent."}

    # Create a new user
    user = create_regular_user(db, user_data, generate_verification_token=generate_verification_token)
    db.commit()
    db.refresh(user)

    # Send verification email
    await send_verification_email(user.email, user.verification_token)
    
    return {"msg": "Please check your email to verify your account"}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account not verified")

    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/google/login")
def google_login():
    return {"url": get_google_oauth_url()}

@router.get("/auth/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    google_user_info = await fetch_google_user_info(code)
    user = register_or_login_google_user(db, google_user_info)

    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = get_user_by_verification_token(db, token)

    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    user.is_verified = True
    user.verification_token = None
    db.commit()

    return {"msg": "Email verified successfully"}

@router.post("/refresh")
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = validate_refresh_token(refresh_token)

        email = payload.get("sub")
        user = get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        access_token = create_access_token({"sub": user.email})

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    except PyJWKError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
