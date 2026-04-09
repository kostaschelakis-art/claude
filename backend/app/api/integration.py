"""Integration API: simplified generation endpoint with API-key auth, status, and webhooks."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import GeneratedImage, ImageStatus, User, UserRole

router = APIRouter(prefix="/integration", tags=["integration"])


# --------------------------------------------------------------------------- #
# API-key authentication dependency
# --------------------------------------------------------------------------- #


async def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate the API key from the X-API-Key header.

    For now, the API key is matched against the application secret_key.
    A production system would look up API keys in a dedicated table and
    resolve the associated user/service account.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    # Simple validation: match against secret_key (placeholder).
    # In production, look up the key in an api_keys table.
    if x_api_key != settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Return a synthetic integration user or the first super-admin
    result = await db.execute(
        select(User).where(User.role == UserRole.SUPER_ADMIN, User.is_active.is_(True)).limit(1)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Fall back: create a placeholder context -- the caller only
        # needs a user_id for record ownership.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No active integration user configured",
        )

    return user


# --------------------------------------------------------------------------- #
# Request / Response schemas
# --------------------------------------------------------------------------- #


class IntegrationGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    market_id: uuid.UUID
    width: int = Field(default=1024, gt=0, le=10000)
    height: int = Field(default=1024, gt=0, le=10000)
    ai_provider: str | None = Field(
        default=None,
        pattern=r"^(google|openai|stability)$",
    )
    callback_url: str | None = Field(
        default=None,
        description="Optional webhook URL to receive completion notification",
    )


class WebhookRegisterRequest(BaseModel):
    url: str = Field(..., description="Webhook endpoint URL")
    events: list[str] = Field(
        default_factory=lambda: ["generation.completed", "generation.failed"],
        description="List of event types to subscribe to",
    )
    secret: str | None = Field(
        default=None,
        description="Shared secret for HMAC signature verification",
    )


# --------------------------------------------------------------------------- #
# In-memory webhook registry (would be database-backed in production)
# --------------------------------------------------------------------------- #

_webhook_registry: list[dict] = []


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def integration_generate(
    body: IntegrationGenerateRequest,
    integration_user: User = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Simplified generation endpoint for external integrations.

    Authenticated via X-API-Key header instead of Bearer JWT.
    Creates a GeneratedImage record with PENDING status and returns a job_id.
    """
    ai_provider = body.ai_provider or settings.default_ai_provider

    image = GeneratedImage(
        id=uuid.uuid4(),
        prompt=body.prompt,
        user_id=integration_user.id,
        market_id=body.market_id,
        ai_provider=ai_provider,
        status=ImageStatus.PENDING,
        width=body.width,
        height=body.height,
        generation_params={
            "source": "integration_api",
            "callback_url": body.callback_url,
        },
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)

    return {
        "job_id": str(image.id),
        "status": image.status.value,
        "prompt": image.prompt,
        "width": image.width,
        "height": image.height,
        "ai_provider": image.ai_provider,
        "created_at": image.created_at.isoformat(),
    }


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: uuid.UUID,
    _integration_user: User = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Check the status of a generation job."""
    result = await db.execute(
        select(GeneratedImage).where(GeneratedImage.id == job_id)
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    response = {
        "job_id": str(image.id),
        "status": image.status.value,
        "prompt": image.prompt,
        "width": image.width,
        "height": image.height,
        "ai_provider": image.ai_provider,
        "created_at": image.created_at.isoformat(),
    }

    if image.status == ImageStatus.COMPLETED:
        response["composite_url"] = image.composite_url
        response["file_size_bytes"] = image.file_size_bytes

    if image.status == ImageStatus.FAILED:
        response["error"] = image.generation_params.get("error") if image.generation_params else None

    return response


@router.post("/webhook/register", status_code=status.HTTP_201_CREATED)
async def register_webhook(
    body: WebhookRegisterRequest,
    _integration_user: User = Depends(verify_api_key),
):
    """Register a webhook URL to receive event notifications.

    In production, this would persist the webhook to a database table.
    This implementation uses an in-memory registry for demonstration.
    """
    webhook_id = str(uuid.uuid4())

    webhook_entry = {
        "id": webhook_id,
        "url": body.url,
        "events": body.events,
        "secret": body.secret,
        "active": True,
    }
    _webhook_registry.append(webhook_entry)

    return {
        "id": webhook_id,
        "url": body.url,
        "events": body.events,
        "active": True,
        "message": "Webhook registered successfully",
    }
