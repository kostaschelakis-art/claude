"""BrandForge API - AI Image Generation Platform."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.config import settings
from app.database import engine, Base

logger = logging.getLogger(__name__)


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed_initial_data() -> None:
    """Seed markets, brand guidelines, and ensure MinIO bucket exists."""
    import logging

    from app.database import async_session_factory
    from app.seed.brand_seed import seed_brand_guidelines, seed_markets
    from app.services.storage_service import S3Client

    logger = logging.getLogger(__name__)

    async with async_session_factory() as session:
        try:
            await seed_markets(session)
            await seed_brand_guidelines(session)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Seeding initial data failed")
            raise

    try:
        storage = S3Client()
        await storage.ensure_bucket()
    except Exception:
        logger.warning("Could not ensure MinIO bucket on startup", exc_info=True)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    await _init_db()
    await _seed_initial_data()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="BrandForge API",
        description="AI-powered image generation platform for brand-compliant marketing assets.",
        version="1.0.0",
        lifespan=lifespan,
        # Don't 307-redirect /images → /images/ — the browser strips auth
        # headers on the follow-up, which breaks our frontend.
        redirect_slashes=False,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.router import api_router
    application.include_router(api_router, prefix="/api/v1")

    @application.get("/health", tags=["health"])
    async def health_check() -> dict:
        return {"status": "healthy", "service": "brandforge-api", "version": "1.0.0"}

    @application.exception_handler(ValueError)
    async def value_error_handler(req: Request, exc: ValueError) -> JSONResponse:
        # Pydantic ValidationError is a subclass of ValueError. Log it and
        # surface a 422 with sanitised (JSON-safe) error details.
        if isinstance(exc, PydanticValidationError):
            logger.warning(
                "Pydantic validation error on %s %s: %s",
                req.method, req.url.path, exc,
            )
            safe_errors = [
                {
                    "loc": list(err.get("loc", ())),
                    "msg": err.get("msg", ""),
                    "type": err.get("type", ""),
                }
                for err in exc.errors()
            ]
            return JSONResponse(status_code=422, content={"detail": safe_errors})
        logger.exception("ValueError in handler for %s %s", req.method, req.url.path)
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @application.exception_handler(PermissionError)
    async def permission_error_handler(_req: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @application.exception_handler(FileNotFoundError)
    async def not_found_handler(_req: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return application


app = create_app()
