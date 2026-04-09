"""Image generation, retrieval, review, and export routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.middleware import get_current_user
from app.auth.roles import check_market_access
from app.config import settings
from app.database import get_db
from app.models import (
    ExportFormat,
    GeneratedImage,
    ImageExport,
    ImageLayer,
    ImageReview,
    ImageStatus,
    QAResult,
    User,
    UserRole,
)

router = APIRouter(prefix="/images", tags=["images"])

# --------------------------------------------------------------------------- #
# Dimension presets (Betano specs)
# --------------------------------------------------------------------------- #

DIMENSION_PRESETS: list[dict[str, Any]] = [
    {"name": "Newsletter Single", "width": 600, "height": 735, "category": "email"},
    {"name": "Newsletter Visual", "width": 525, "height": 675, "category": "email"},
    {"name": "Newsletter Double Theme", "width": 450, "height": 450, "category": "email"},
    {"name": "Newsletter Half", "width": 450, "height": 225, "category": "email"},
    {"name": "Newsletter Quarter", "width": 225, "height": 300, "category": "email"},
    {"name": "CTA Button", "width": 226, "height": 65, "category": "email"},
    {"name": "Story Enhanced Thumbnail", "width": 471, "height": 330, "category": "story"},
    {"name": "Story Background", "width": 1862, "height": 2778, "category": "story"},
    {"name": "Story Logo", "width": 174, "height": 210, "category": "story"},
    {"name": "Story Logo Large", "width": 1098, "height": 1329, "category": "story"},
    {"name": "Story Profile Icon", "width": 72, "height": 72, "category": "story"},
    {"name": "Story Universal BG", "width": 1862, "height": 2778, "category": "story"},
    {"name": "Slider", "width": 2048, "height": 1152, "category": "promo"},
    {"name": "Push Notification", "width": 458, "height": 258, "category": "push"},
    {"name": "Private Message", "width": 1126, "height": 260, "category": "messaging"},
    {"name": "Email Header", "width": 600, "height": 200, "category": "email"},
    {"name": "In-App Banner", "width": 1080, "height": 1920, "category": "in_app"},
    {"name": "Promo Banner", "width": 1200, "height": 628, "category": "promo"},
    {"name": "Social Story", "width": 1080, "height": 1920, "category": "social"},
    {"name": "Social Post Square", "width": 1080, "height": 1080, "category": "social"},
    {"name": "Casino Thumbnail", "width": 240, "height": 240, "category": "casino"},
    {"name": "Casino Group Thumb", "width": 471, "height": 330, "category": "casino"},
]

_PRESET_MAP: dict[str, dict[str, Any]] = {p["name"]: p for p in DIMENSION_PRESETS}


# --------------------------------------------------------------------------- #
# Pydantic request / response helpers kept local to avoid circular imports
# --------------------------------------------------------------------------- #

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    market_id: uuid.UUID
    template_id: uuid.UUID | None = None
    width: int = Field(default=1024, gt=0, le=10000)
    height: int = Field(default=1024, gt=0, le=10000)
    dimension_preset: str | None = Field(
        default=None,
        description="Preset name from /presets/dimensions. Overrides width/height.",
    )
    ai_provider: str | None = Field(
        default=None,
        pattern=r"^(google|openai|stability)$",
    )
    style_preferences: dict | None = None


class ReviewRequest(BaseModel):
    score: int = Field(..., ge=1, le=5)
    thumbs_up: bool
    feedback_text: str | None = Field(default=None, max_length=4000)


class ExportRequest(BaseModel):
    format: str = Field(..., pattern=r"^(png|jpg|webp|svg|pdf)$")
    width: int = Field(..., gt=0, le=10000)
    height: int = Field(..., gt=0, le=10000)
    preset_name: str | None = None


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.get("/presets/dimensions")
async def list_dimension_presets() -> list[dict[str, Any]]:
    """Return all available dimension presets."""
    return DIMENSION_PRESETS


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_image(
    body: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a GeneratedImage record with PENDING status and return a job_id."""
    check_market_access(current_user, body.market_id)

    # Resolve dimensions from preset if provided
    width = body.width
    height = body.height
    if body.dimension_preset:
        preset = _PRESET_MAP.get(body.dimension_preset)
        if preset is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown dimension preset: {body.dimension_preset}",
            )
        width = preset["width"]
        height = preset["height"]

    ai_provider = body.ai_provider or settings.default_ai_provider

    image = GeneratedImage(
        id=uuid.uuid4(),
        prompt=body.prompt,
        user_id=current_user.id,
        market_id=body.market_id,
        template_id=body.template_id,
        ai_provider=ai_provider,
        status=ImageStatus.PENDING,
        width=width,
        height=height,
        generation_params={
            "style_preferences": body.style_preferences,
            "dimension_preset": body.dimension_preset,
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


@router.get("/{image_id}")
async def get_image(
    image_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single image with its layers, reviews, and QA results."""
    result = await db.execute(
        select(GeneratedImage)
        .options(
            selectinload(GeneratedImage.image_layers),
            selectinload(GeneratedImage.reviews),
            selectinload(GeneratedImage.qa_results),
        )
        .where(GeneratedImage.id == image_id)
    )
    image = result.scalar_one_or_none()

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Non-super-admin users can only see their own images or images in their market
    if current_user.role != UserRole.SUPER_ADMIN:
        if image.user_id != current_user.id and image.market_id != current_user.market_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    layers = [
        {
            "id": str(layer.id),
            "layer_index": layer.layer_index,
            "layer_type": layer.layer_type.value,
            "content_url": layer.content_url,
            "properties": layer.properties,
            "is_editable": layer.is_editable,
            "created_at": layer.created_at.isoformat(),
        }
        for layer in image.image_layers
    ]

    reviews = [
        {
            "id": str(rev.id),
            "reviewer_id": str(rev.reviewer_id),
            "score": rev.score,
            "thumbs": rev.thumbs,
            "feedback_text": rev.feedback_text,
            "created_at": rev.created_at.isoformat(),
        }
        for rev in image.reviews
    ]

    qa_results = [
        {
            "id": str(qa.id),
            "overall_score": qa.overall_score,
            "category_scores": qa.category_scores,
            "violations": qa.violations,
            "suggestions": qa.suggestions,
            "evaluated_at": qa.evaluated_at.isoformat(),
        }
        for qa in image.qa_results
    ]

    return {
        "id": str(image.id),
        "prompt": image.prompt,
        "refined_prompt": image.refined_prompt,
        "user_id": str(image.user_id),
        "market_id": str(image.market_id),
        "template_id": str(image.template_id) if image.template_id else None,
        "ai_provider": image.ai_provider,
        "ai_model": image.ai_model,
        "status": image.status.value,
        "composite_url": image.composite_url,
        "width": image.width,
        "height": image.height,
        "format": image.format,
        "file_size_bytes": image.file_size_bytes,
        "generation_params": image.generation_params,
        "created_at": image.created_at.isoformat(),
        "layers": layers,
        "reviews": reviews,
        "qa_results": qa_results,
    }


@router.get("/")
async def list_images(
    market_id: uuid.UUID | None = Query(default=None),
    image_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List images for the current user with optional filters."""
    query = select(GeneratedImage)

    # Non-super-admin users only see their own images
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.where(GeneratedImage.user_id == current_user.id)

    if market_id is not None:
        check_market_access(current_user, market_id)
        query = query.where(GeneratedImage.market_id == market_id)

    if image_status is not None:
        try:
            status_enum = ImageStatus(image_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {image_status}. Must be one of: {', '.join(s.value for s in ImageStatus)}",
            )
        query = query.where(GeneratedImage.status == status_enum)

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply ordering and pagination
    query = query.order_by(GeneratedImage.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    images = result.scalars().all()

    return {
        "items": [
            {
                "id": str(img.id),
                "prompt": img.prompt,
                "status": img.status.value,
                "composite_url": img.composite_url,
                "width": img.width,
                "height": img.height,
                "ai_provider": img.ai_provider,
                "created_at": img.created_at.isoformat(),
            }
            for img in images
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{image_id}/review", status_code=status.HTTP_201_CREATED)
async def submit_review(
    image_id: uuid.UUID,
    body: ReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a review for an image."""
    # Verify image exists
    result = await db.execute(
        select(GeneratedImage).where(GeneratedImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    review = ImageReview(
        id=uuid.uuid4(),
        image_id=image_id,
        reviewer_id=current_user.id,
        score=body.score,
        thumbs=body.thumbs_up,
        feedback_text=body.feedback_text,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)

    return {
        "id": str(review.id),
        "image_id": str(review.image_id),
        "reviewer_id": str(review.reviewer_id),
        "score": review.score,
        "thumbs": review.thumbs,
        "feedback_text": review.feedback_text,
        "created_at": review.created_at.isoformat(),
    }


@router.post("/{image_id}/export", status_code=status.HTTP_201_CREATED)
async def export_image(
    image_id: uuid.UUID,
    body: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an export record for an image."""
    # Verify image exists
    result = await db.execute(
        select(GeneratedImage).where(GeneratedImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    if image.status != ImageStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image is not ready for export (status: {image.status.value})",
        )

    export_format = ExportFormat(body.format)

    export = ImageExport(
        id=uuid.uuid4(),
        image_id=image_id,
        format=export_format,
        width=body.width,
        height=body.height,
        preset_name=body.preset_name,
        # file_url and file_size_bytes would be populated by an async worker
        file_url=None,
        file_size_bytes=None,
    )
    db.add(export)
    await db.flush()
    await db.refresh(export)

    return {
        "id": str(export.id),
        "image_id": str(export.image_id),
        "format": export.format.value,
        "width": export.width,
        "height": export.height,
        "preset_name": export.preset_name,
        "file_url": export.file_url,
        "file_size_bytes": export.file_size_bytes,
        "created_at": export.created_at.isoformat(),
    }


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an image. Users can delete their own images; admins can delete any."""
    result = await db.execute(
        select(GeneratedImage).where(GeneratedImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Only the owner or admin+ can delete
    if image.user_id != current_user.id and current_user.role not in (
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own images",
        )

    await db.delete(image)
    await db.flush()
    return None
