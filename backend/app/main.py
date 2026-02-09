"""
Xavfsiz Backend Tizimi — FastAPI Application
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.redis import redis_client
from app.middleware.security import SecurityHeadersMiddleware

logging.basicConfig(
    level=logging.DEBUG if settings.is_development else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(" Starting …")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("Database ready")
    except Exception as exc:
        log.error("DB error: %s", exc)

    try:
        await redis_client.connect()
        log.info("Redis ready")
    except Exception as exc:
        log.warning(" Redis: %s", exc)

    yield

    log.info("Shutting down …")
    await redis_client.disconnect()
    await engine.dispose()
    log.info("Closed")


app = FastAPI(
    title="Xavfsiz Backend Tizimi",
    description="Admin + User Management API",
    version="1.0.0",
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"],
)
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(l) for l in e["loc"][1:]), "message": e["msg"], "type": e["type"]}
        for e in exc.errors()
    ]
    return JSONResponse(content={"success": False, "message": "Validatsiya xatosi", "errors": errors}, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


@app.exception_handler(Exception)
async def global_error(request: Request, exc: Exception) -> JSONResponse:
    log.error("Unhandled: %s", exc, exc_info=True)
    body = {"success": False, "message": "Ichki server xatosi"} if settings.is_production else {"success": False, "message": str(exc), "type": type(exc).__name__}
    return JSONResponse(content=body, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["Health"])
async def health() -> dict[str, Any]:
    return {"status": "healthy", "version": "1.0.0", "environment": settings.ENVIRONMENT}


@app.get("/", tags=["Info"])
async def root() -> dict[str, str]:
    return {"name": "Xavfsiz Backend Tizimi", "version": "1.0.0", "docs": "/api/docs", "health": "/health"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.is_development)
