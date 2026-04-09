"""Template CRUD, analysis, and variation routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.middleware import get_current_user
from app.auth.roles import check_market_access
from app.database import get_db
from app.models import Template, TemplateCategory, TemplateVariation, User, UserRole

router = APIRouter(prefix="/templates", tags=["templates"])


# --------------------------------------------------------------------------- #
# Request schemas
# --------------------------------------------------------------------------- #


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(
        ...,
        pattern=r"^(email|story|push|slider|promo_banner|in_app|newsletter|casino|sports|custom)$",
    )
    market_id: uuid.UUID | None = None
    layout_config: dict = Field(default_factory=dict)
    dimensions_width: int = Field(..., gt=0, le=10000)
    dimensions_height: int = Field(..., gt=0, le=10000)
    safe_areas: list[dict] = Field(default_factory=list)
    persistent_elements: list[dict] = Field(default_factory=list)
    is_ai_generated: bool = False
    source_image_url: str | None = None


class TemplateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(
        default=None,
        pattern=r"^(email|story|push|slider|promo_banner|in_app|newsletter|casino|sports|custom)$",
    )
    market_id: uuid.UUID | None = None
    layout_config: dict | None = None
    dimensions_width: int | None = Field(default=None, gt=0, le=10000)
    dimensions_height: int | None = Field(default=None, gt=0, le=10000)
    safe_areas: list[dict] | None = None
    persistent_elements: list[dict] | None = None
    is_ai_generated: bool | None = None
    source_image_url: str | None = None


class VariationCreateRequest(BaseModel):
    variation_config: dict = Field(default_factory=dict)
    preview_url: str | None = None


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #


def _template_to_dict(t: Template) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "description": t.description,
        "category": t.category.value,
        "market_id": str(t.market_id) if t.market_id else None,
        "created_by": str(t.created_by),
        "layout_config": t.layout_config,
        "dimensions_width": t.dimensions_width,
        "dimensions_height": t.dimensions_height,
        "safe_areas": t.safe_areas,
        "persistent_elements": t.persistent_elements,
        "is_ai_generated": t.is_ai_generated,
        "source_image_url": t.source_image_url,
        "created_at": t.created_at.isoformat(),
    }


def _variation_to_dict(v: TemplateVariation) -> dict:
    return {
        "id": str(v.id),
        "template_id": str(v.template_id),
        "variation_config": v.variation_config,
        "preview_url": v.preview_url,
        "created_at": v.created_at.isoformat(),
    }


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_template(
    body: TemplateCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new template."""
    if body.market_id is not None:
        check_market_access(current_user, body.market_id)

    try:
        category_enum = TemplateCategory(body.category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {body.category}",
        )

    template = Template(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        category=category_enum,
        market_id=body.market_id,
        created_by=current_user.id,
        layout_config=body.layout_config,
        dimensions_width=body.dimensions_width,
        dimensions_height=body.dimensions_height,
        safe_areas=body.safe_areas,
        persistent_elements=body.persistent_elements,
        is_ai_generated=body.is_ai_generated,
        source_image_url=body.source_image_url,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)

    return _template_to_dict(template)


@router.post("/analyze")
async def analyze_template(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept an uploaded image file and return analysis.

    This is a placeholder -- a real implementation would send the image to an
    AI provider for layout analysis and safe-area detection.
    """
    content = await file.read()
    file_size = len(content)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "file_size": file_size,
        "analysis": {
            "detected_safe_areas": [
                {"x": 50, "y": 50, "w": 200, "h": 100, "label": "text_area"},
                {"x": 10, "y": 10, "w": 80, "h": 80, "label": "logo_zone"},
            ],
            "detected_elements": [
                {
                    "element_type": "logo",
                    "position": {"x": 10, "y": 10, "anchor": "top-left"},
                    "size": {"width": 80, "height": 80},
                    "confidence": 0.85,
                }
            ],
            "suggested_dimensions": {"width": 1080, "height": 1920},
            "suggested_category": "story",
            "confidence": 0.78,
        },
        "note": "This is a placeholder analysis. A production implementation would use AI vision models.",
    }


@router.get("/")
async def list_templates(
    category: str | None = Query(default=None),
    market_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List templates with optional filters."""
    query = select(Template)

    if category is not None:
        try:
            category_enum = TemplateCategory(category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {category}",
            )
        query = query.where(Template.category == category_enum)

    if market_id is not None:
        check_market_access(current_user, market_id)
        # Show templates for the given market + global templates (market_id is NULL)
        query = query.where(
            (Template.market_id == market_id) | (Template.market_id.is_(None))
        )
    elif current_user.role != UserRole.SUPER_ADMIN:
        # Non-super-admin sees their market's templates + global templates
        query = query.where(
            (Template.market_id == current_user.market_id)
            | (Template.market_id.is_(None))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Template.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    templates = result.scalars().all()

    return {
        "items": [
            {
                "id": str(t.id),
                "name": t.name,
                "category": t.category.value,
                "dimensions_width": t.dimensions_width,
                "dimensions_height": t.dimensions_height,
                "market_id": str(t.market_id) if t.market_id else None,
            }
            for t in templates
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{template_id}")
async def get_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single template by ID."""
    result = await db.execute(
        select(Template)
        .options(selectinload(Template.variations))
        .where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    data = _template_to_dict(template)
    data["variations"] = [_variation_to_dict(v) for v in template.variations]
    return data


@router.put("/{template_id}")
async def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing template."""
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Only the creator or admin+ can update
    if template.created_by != current_user.id and current_user.role not in (
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own templates",
        )

    update_data = body.model_dump(exclude_unset=True)

    if "category" in update_data and update_data["category"] is not None:
        try:
            update_data["category"] = TemplateCategory(update_data["category"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {update_data['category']}",
            )

    if "market_id" in update_data and update_data["market_id"] is not None:
        check_market_access(current_user, update_data["market_id"])

    for field, value in update_data.items():
        setattr(template, field, value)

    await db.flush()
    await db.refresh(template)

    return _template_to_dict(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a template."""
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    if template.created_by != current_user.id and current_user.role not in (
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own templates",
        )

    await db.delete(template)
    await db.flush()
    return None


@router.post("/{template_id}/variations", status_code=status.HTTP_201_CREATED)
async def create_variation(
    template_id: uuid.UUID,
    body: VariationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a template variation (placeholder -- returns stub variation)."""
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    variation = TemplateVariation(
        id=uuid.uuid4(),
        template_id=template_id,
        variation_config=body.variation_config,
        preview_url=body.preview_url,
    )
    db.add(variation)
    await db.flush()
    await db.refresh(variation)

    return _variation_to_dict(variation)


@router.get("/{template_id}/variations")
async def list_variations(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all variations for a template."""
    # Verify template exists
    tmpl_result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    if tmpl_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    result = await db.execute(
        select(TemplateVariation)
        .where(TemplateVariation.template_id == template_id)
        .order_by(TemplateVariation.created_at.desc())
    )
    variations = result.scalars().all()

    return {
        "template_id": str(template_id),
        "items": [_variation_to_dict(v) for v in variations],
        "total": len(variations),
    }
