from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import secrets
import time
from typing import Dict, Set
import os

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# CSRF token storage (in production, use Redis)
csrf_tokens: Dict[str, float] = {}
CSRF_TOKEN_EXPIRE_SECONDS = 3600  # 1 hour

class SecurityMiddleware(BaseHTTPMiddleware):
    """Custom security middleware for CSRF protection and request validation"""
    
    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key
        self.allowed_origins = {
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        }
        
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF for safe methods and auth endpoints
        if self._should_skip_csrf(request):
            response = await call_next(request)
            self._add_cors_headers(request, response)
            return response
            
        # Validate origin
        if not self._validate_origin(request):
            resp = JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid origin"}
            )
            self._add_cors_headers(request, resp)
            return resp
            
        # CSRF protection for state-changing requests
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            csrf_error = await self._validate_csrf(request)
            if csrf_error:
                self._add_cors_headers(request, csrf_error)
                return csrf_error
                
        response = await call_next(request)
        
        # Add CORS and security headers
        self._add_cors_headers(request, response)
        self._add_security_headers(response)
        
        return response
    
    def _should_skip_csrf(self, request: Request) -> bool:
        """Skip CSRF validation for safe methods and auth endpoints"""
        safe_methods = {"GET", "HEAD", "OPTIONS"}
        auth_endpoints = {"/auth/login", "/auth/register", "/auth/google/callback"}
        
        return (
            request.method in safe_methods or
            request.url.path in auth_endpoints or
            request.url.path.startswith("/docs") or
            request.url.path.startswith("/openapi.json")
        )
    
    def _validate_origin(self, request: Request) -> bool:
        """Validate request origin"""
        origin = request.headers.get("origin")
        if not origin:
            return True  # Allow requests without origin (e.g., Postman)
        return origin in self.allowed_origins
    
    async def _validate_csrf(self, request: Request) -> JSONResponse | None:
        """Validate CSRF token"""
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing"}
            )
            
        # Verify token exists and hasn't expired
        if csrf_token not in csrf_tokens:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid CSRF token"}
            )
            
        if time.time() > csrf_tokens[csrf_token]:
            del csrf_tokens[csrf_token]
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token expired"}
            )
            
        return None
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )

    def _add_cors_headers(self, request: Request, response: Response):
        origin = request.headers.get("origin")
        if origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-CSRF-Token"

def generate_csrf_token() -> str:
    """Generate a new CSRF token"""
    token = secrets.token_urlsafe(32)
    csrf_tokens[token] = time.time() + CSRF_TOKEN_EXPIRE_SECONDS
    return token

def cleanup_expired_tokens():
    """Remove expired CSRF tokens"""
    current_time = time.time()
    expired_tokens = [
        token for token, expire_time in csrf_tokens.items()
        if current_time > expire_time
    ]
    for token in expired_tokens:
        del csrf_tokens[token]

# Rate limiting decorators
def rate_limit_auth():
    """Rate limit for authentication endpoints"""
    return limiter.limit("5/minute")

def rate_limit_api():
    """Rate limit for API endpoints"""
    return limiter.limit("100/minute")

def rate_limit_upload():
    """Rate limit for file upload endpoints"""
    return limiter.limit("10/minute")
