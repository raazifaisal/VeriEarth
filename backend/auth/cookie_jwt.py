from fastapi import Response, Request
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Cookie security settings (overridable via env)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()  # 'lax' | 'strict' | 'none'
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", None)
COOKIE_PATH = os.getenv("COOKIE_PATH", "/")

class CookieJWTService:
    """JWT service using httpOnly cookies for security"""
    
    @staticmethod
    def create_access_token(data: dict) -> str:
        """Create access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
        """Verify and decode token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != token_type:
                return None
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def set_auth_cookies(response: Response, user_id: str, email: str):
        """Set httpOnly cookies for authentication"""
        access_token = CookieJWTService.create_access_token({
            "sub": user_id,
            "email": email
        })
        refresh_token = CookieJWTService.create_refresh_token({
            "sub": user_id,
            "email": email
        })
        
        # Set access token cookie (short-lived)
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            path=COOKIE_PATH,
        )
        
        # Set refresh token cookie (long-lived)
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            domain=COOKIE_DOMAIN,
            path=COOKIE_PATH,
        )
    
    @staticmethod
    def clear_auth_cookies(response: Response):
        """Clear authentication cookies"""
        response.delete_cookie(key="access_token", httponly=True, samesite=COOKIE_SAMESITE, domain=COOKIE_DOMAIN, path=COOKIE_PATH)
        response.delete_cookie(key="refresh_token", httponly=True, samesite=COOKIE_SAMESITE, domain=COOKIE_DOMAIN, path=COOKIE_PATH)
    
    @staticmethod
    def get_token_from_cookies(request: Request, token_type: str = "access") -> Optional[str]:
        """Get token from cookies"""
        cookie_name = f"{token_type}_token"
        return request.cookies.get(cookie_name)
    
    @staticmethod
    def get_current_user_from_cookies(request: Request) -> Optional[dict]:
        """Get current user from cookies"""
        access_token = CookieJWTService.get_token_from_cookies(request, "access")
        if not access_token:
            return None
        
        payload = CookieJWTService.verify_token(access_token, "access")
        if not payload:
            return None
            
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email")
        }
