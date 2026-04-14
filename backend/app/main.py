"""BrandForge API - AI Image Generation Platform."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    await _init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="BrandForge API",
        description="AI-powered image generation platform for brand-compliant marketing assets.",
        version="1.0.0",
        lifespan=lifespan,
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
    async def value_error_handler(_req: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @application.exception_handler(PermissionError)
    async def permission_error_handler(_req: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @application.exception_handler(FileNotFoundError)
    async def not_found_handler(_req: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return application


app = create_app()
