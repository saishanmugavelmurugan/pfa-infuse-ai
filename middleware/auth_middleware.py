"""Authentication middleware."""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
import os
import logging

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')

class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate JWT tokens on protected routes."""
    
    # Routes that don't require authentication
    PUBLIC_PATHS = [
        '/api/auth/login',
        '/api/auth/register',
        '/api/health',
        '/api/language/',
        '/api/healthtrack/drug-database/',
        '/docs',
        '/openapi.json',
    ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip auth for public paths
        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)
        
        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return await call_next(request)
        
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                request.state.user = payload
            except jwt.ExpiredSignatureError:
                logger.warning(f"Expired token for path: {path}")
                # Allow request to continue, route handler will check auth
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid token for path: {path}: {e}")
                # Allow request to continue, route handler will check auth
        
        return await call_next(request)
