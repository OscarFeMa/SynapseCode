"""
Synapse Council v2.0 - API Middleware
Rate limiting, CORS, seguridad.
"""
import time
from typing import Dict, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting simple basado en IP.
    Configurable por endpoint.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.requests: Dict[str, list] = {}  # IP -> list of timestamps
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for WebSocket upgrades
        if request.url.path.startswith("/ws"):
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        # Clean old requests and count recent ones
        if client_ip in self.requests:
            self.requests[client_ip] = [
                ts for ts in self.requests[client_ip]
                if ts > window_start
            ]
            recent_count = len(self.requests[client_ip])
        else:
            recent_count = 0
        
        # Check burst limit (immediate)
        if recent_count >= self.burst_size:
            logger.warning(
                "rate_limit.burst_exceeded",
                ip=client_ip,
                path=request.url.path
            )
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {self.burst_size} requests per burst."}
            )
        
        # Check sustained limit
        if recent_count >= self.requests_per_minute:
            logger.warning(
                "rate_limit.sustained_exceeded",
                ip=client_ip,
                path=request.url.path
            )
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {self.requests_per_minute} requests per minute."}
            )
        
        # Record request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(now)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - len(self.requests[client_ip]))
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrae IP real del cliente (considerando proxies)"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade headers de seguridad a todas las respuestas"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # CSP (basic)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' ws: wss: http: https:;"
        )
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging de requests HTTP"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            ip=request.client.host if request.client else "unknown",
        )
        
        # Process
        try:
            response = await call_next(request)
            
            # Log success
            duration = time.time() - start_time
            logger.info(
                "http.response",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                "http.error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
            )
            raise
