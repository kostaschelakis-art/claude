"""Main API router – aggregates all sub-routers under /api/v1."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.images import router as images_router
from app.api.templates import router as templates_router
from app.api.markets import router as markets_router
from app.api.brand import router as brand_router
from app.api.editor import router as editor_router
from app.api.integration import router as integration_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(images_router)
api_router.include_router(templates_router)
api_router.include_router(markets_router)
api_router.include_router(brand_router)
api_router.include_router(editor_router)
api_router.include_router(integration_router)
