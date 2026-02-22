"""Request logging middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
import uuid

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Start timer
        start_time = time.time()
        
        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - Started",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'client_ip': request.client.host if request.client else 'unknown'
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - {response.status_code} ({duration_ms}ms)",
            extra={
                'request_id': request_id,
                'status_code': response.status_code,
                'duration_ms': duration_ms
            }
        )
        
        # Add request ID to response headers
        response.headers['X-Request-ID'] = request_id
        
        return response
