from datetime import datetime, timedelta
import jwt  # Use PyJWT instead of jose
from jwt import PyJWTError  # Use PyJWTError instead of JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
import secrets
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import httpx

from db.crud import get_user_by_email, create_social_user
from db.schemas import UserOAuthCreate
from db.models import User
from db.database import get_db

load_dotenv()

# Secrets & Config
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Google OAuth Config
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

# --- PASSWORD HASHING ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# --- AUTH TOKEN CREATION ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- USER AUTHENTICATION ---
def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return None
    return user

# --- GOOGLE OAUTH ---
def get_google_oauth_url() -> str:
    return (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&scope=openid%20email%20profile"
    )

async def fetch_google_user_info(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_response.json()

        if "error" in token_data:
            raise Exception(f"Google OAuth Error: {token_data['error']}")

        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        return userinfo_response.json()

def register_or_login_google_user(db: Session, google_user_info: dict) -> User:
    user = get_user_by_email(db, google_user_info['email'])

    if user is None:
        oauth_user = UserOAuthCreate(
            email=google_user_info['email'],
            full_name=google_user_info.get('name'),
            oauth_provider='google',
            oauth_id=google_user_info['sub']
        )
        user = create_social_user(db, oauth_user)
    elif user.oauth_provider != 'google':
        raise HTTPException(status_code=400, detail="Email already registered with another method.")

    return user

# --- EMAIL VERIFICATION ---
def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)

async def send_verification_email(email: EmailStr, token: str):
    verify_url_base = os.getenv("VERIFY_EMAIL_URL", "http://localhost:3000/verify-email")
    verify_url = f"{verify_url_base}?token={token}"
    
    message = MessageSchema(
    subject="Verify Your Email Address - VeriEarth",
    recipients=[email],
    body=f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h1 style="color: #4CAF50; text-align: center;">Welcome to VeriEarth!</h1>
                <p>Hi there,</p>
                <p>Thank you for signing up with VeriEarth. To get started, please verify your email address by clicking the button below:</p>
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{verify_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-size: 16px;">
                        Verify Email Address
                    </a>
                </div>
                <p>If the button above doesn't work, you can also copy and paste the following link into your browser:</p>
                <p style="word-break: break-all; color: #4CAF50;">{verify_url}</p>
                <p>If you didn't create an account with VeriEarth, you can safely ignore this email.</p>
                <p>Best regards,<br>The VeriEarth Team</p>
                <hr style="border: 0; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="text-align: center; font-size: 12px; color: #777;">
                    This email was sent to {email}. If you have any questions, please contact us at <a href="mailto:support@veriearth.com" style="color: #4CAF50; text-decoration: none;">support@veriearth.com</a>.
                </p>
            </div>
        </body>
    </html>
    """,
    subtype="html"
)

    fm = FastMail(ConnectionConfig(
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_FROM=os.getenv("MAIL_FROM"),
        MAIL_PORT=587,
        MAIL_SERVER="smtp.gmail.com",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True
    ))

    await fm.send_message(message)

# --- PROTECTED USER RETRIEVAL ---
async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except PyJWTError:  # Use PyJWTError instead of JWTError
        raise credentials_exception

    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    return user

# --- REFRESH TOKEN HANDLING ---
def validate_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        return payload
    except PyJWTError:  # Use PyJWTError instead of JWTError
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def get_current_user_from_cookies(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user from httpOnly cookies"""
    from auth.cookie_jwt import CookieJWTService
    
    user_data = CookieJWTService.get_current_user_from_cookies(request)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user_by_email(db, user_data["email"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    return user
