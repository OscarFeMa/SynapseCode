"""
Synapse Council v2.0 - API Middleware
Rate limiting, CORS, seguridad.
"""

import time

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.monitoring.prometheus import observe_http_request

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting simple basado en IP.
    Configurable por endpoint.
    """

    def __init__(self, app, requests_per_minute: int = 120, burst_size: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.requests: dict[str, list] = {}  # IP → list of timestamps
        self._last_cleanup: float = time.time()
        self._cleanup_interval: float = 300.0  # Limpiar IPs inactivas cada 5 min

        # Rutas exentas de rate limiting
        self._exempt_prefixes = (
            "/health",
            "/docs",
            "/openapi",
            "/redoc",
            "/ws",
            "/api/v1/health",
            "/metrics",
        )

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt paths or OPTIONS (CORS preflight)
        if request.method == "OPTIONS" or request.url.path.startswith(self._exempt_prefixes):
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check rate limit
        now = time.time()
        window_start = now - 60  # 1 minute window
        burst_window_start = now - 5  # 5 second burst window

        # Clean old requests and count recent ones
        if client_ip in self.requests:
            self.requests[client_ip] = [ts for ts in self.requests[client_ip] if ts > window_start]
            recent_count = len(self.requests[client_ip])
            burst_count = sum(1 for ts in self.requests[client_ip] if ts > burst_window_start)
        else:
            recent_count = 0
            burst_count = 0

        # Check burst limit (immediate, per 5 seconds)
        if burst_count >= self.burst_size:
            logger.warning("rate_limit.burst_exceeded", ip=client_ip, path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {self.burst_size} requests per burst (5s)."},
            )

        # Check sustained limit
        if recent_count >= self.requests_per_minute:
            logger.warning("rate_limit.sustained_exceeded", ip=client_ip, path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {self.requests_per_minute} requests per minute."},
            )

        # Record request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(now)

        # Limpiar timestamps antiguos periódicamente (evitar memory leak)
        # Issue: antes manteníamos IPs activas indefinidamente acumulando timestamps
        if now - self._last_cleanup > self._cleanup_interval:
            self._last_cleanup = now
            cutoff = now - 120  # Ventana de 2 minutos

            # Limpiar timestamps antiguos de cada IP y eliminar IPs vacías
            ips_to_remove = []
            for ip, ts_list in self.requests.items():
                # Filtrar solo timestamps recientes
                recent_ts = [t for t in ts_list if t > cutoff]
                if recent_ts:
                    self.requests[ip] = recent_ts
                else:
                    ips_to_remove.append(ip)

            # Eliminar IPs sin actividad reciente
            for ip in ips_to_remove:
                del self.requests[ip]

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

        # CSP (soportar Swagger UI via CDN)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https: https://fonts.gstatic.com; "
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
            observe_http_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=duration,
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
            observe_http_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_seconds=duration,
            )
            raise
