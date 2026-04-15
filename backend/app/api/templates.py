"""Template CRUD, analysis, and variation routes."""

from __future__ import annotations

import uuid
from typing import Any

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


@router.post("", status_code=status.HTTP_201_CREATED, include_in_schema=False)
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
    save_as_template: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload an asset, detect brand patterns, and optionally persist it as a Template.

    Pipeline:
        1. Read the uploaded bytes.
        2. Upload them to object storage so we keep a reference.
        3. Call Gemini vision to extract layout zones, dominant colours,
           typography cues, suggested category, and a short overall-style
           description.
        4. Compare the detected palette against the Betano brand palettes
           and return a brand-alignment report.
        5. If ``save_as_template=true``, insert a ``Template`` row so the
           pattern can be reused for future generations.
    """
    import logging
    from io import BytesIO

    from PIL import Image

    from app.ai.google_imagen import GoogleImagenProvider
    from app.seed.brand_seed import BETANO_BRAND
    from app.services.storage_service import S3Client

    logger = logging.getLogger(__name__)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file upload")

    # --- derive real dimensions from the image ------------------------
    try:
        with Image.open(BytesIO(content)) as img:
            width, height = img.size
    except Exception:
        width, height = 1080, 1080

    # --- store the source asset ---------------------------------------
    source_url: str | None = None
    try:
        storage = S3Client()
        await storage.ensure_bucket()
        ext = (file.filename or "").rsplit(".", 1)[-1].lower() or "png"
        if ext not in {"png", "jpg", "jpeg", "webp"}:
            ext = "png"
        key = f"uploads/{uuid.uuid4()}.{ext}"
        source_url = await storage.upload(
            key=key,
            data=content,
            content_type=file.content_type or f"image/{ext}",
        )
    except Exception:
        logger.exception("Failed to upload analysed asset to object storage")

    # --- run Gemini vision analysis ------------------------------------
    analysis: dict = {}
    try:
        provider = GoogleImagenProvider()
        analysis = await provider.analyze_image(content)
    except Exception as exc:
        logger.exception("Gemini vision analysis failed")
        analysis = {"error": str(exc)}

    # --- brand alignment check ----------------------------------------
    brand_alignment = _score_brand_alignment(analysis)

    # --- suggested category + safe areas ------------------------------
    suggested_category = analysis.get("suggested_category") or _guess_category_from_ratio(
        width, height
    )
    safe_areas = _derive_safe_areas(analysis, width, height)

    response: dict[str, Any] = {
        "filename": file.filename,
        "content_type": file.content_type,
        "file_size": len(content),
        "source_url": source_url,
        "dimensions": {"width": width, "height": height},
        "analysis": analysis,
        "brand_alignment": brand_alignment,
        "suggested_category": suggested_category,
        "safe_areas": safe_areas,
        "brand_context_used": {
            "sportsbook_primary": list(BETANO_BRAND["colours"]["primary_sportsbook"].keys()),
            "casino_primary": list(BETANO_BRAND["colours"]["primary_casino"].keys()),
        },
    }

    # --- optionally persist as a reusable template --------------------
    if save_as_template:
        try:
            category_enum = TemplateCategory(suggested_category)
        except ValueError:
            category_enum = TemplateCategory.CUSTOM

        template = Template(
            id=uuid.uuid4(),
            name=(file.filename or "Uploaded asset")[:255],
            description=(
                (analysis.get("overall_style") or "Pattern detected from uploaded asset.")
                if isinstance(analysis, dict)
                else "Pattern detected from uploaded asset."
            )[:2000],
            category=category_enum,
            market_id=current_user.market_id,
            created_by=current_user.id,
            layout_config={
                "layout_zones": analysis.get("layout_zones") if isinstance(analysis, dict) else [],
                "dominant_colors": analysis.get("dominant_colors") if isinstance(analysis, dict) else [],
                "typography_style": analysis.get("typography_style") if isinstance(analysis, dict) else {},
            },
            dimensions_width=width,
            dimensions_height=height,
            safe_areas=safe_areas,
            persistent_elements=[],
            is_ai_generated=False,
            source_image_url=source_url,
        )
        db.add(template)
        await db.flush()
        await db.refresh(template)
        response["template_id"] = str(template.id)

    return response


# --------------------------------------------------------------------------- #
# Pattern / brand-alignment helpers
# --------------------------------------------------------------------------- #


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _score_brand_alignment(analysis: dict) -> dict:
    """Compare detected dominant colours to the Betano brand palettes."""
    from app.seed.brand_seed import BETANO_BRAND

    detected = analysis.get("dominant_colors") if isinstance(analysis, dict) else None
    if not isinstance(detected, list) or not detected:
        return {
            "score": 0,
            "detected_hexes": [],
            "matches": [],
            "note": "No dominant colour data available.",
        }

    # Build a lookup of brand colour name -> rgb
    brand_colors: list[tuple[str, tuple[int, int, int]]] = []
    for mode in ("primary_sportsbook", "primary_casino", "tonal"):
        for name, spec in BETANO_BRAND["colours"][mode].items():
            brand_colors.append((f"{mode}.{name}", tuple(spec["rgb"])))  # type: ignore[arg-type]

    detected_hexes: list[str] = []
    matches: list[dict] = []
    for entry in detected:
        hex_val = entry.get("hex") if isinstance(entry, dict) else str(entry)
        if not isinstance(hex_val, str):
            continue
        rgb = _hex_to_rgb(hex_val)
        detected_hexes.append(hex_val)
        best = min(brand_colors, key=lambda bc: _rgb_distance(bc[1], rgb))
        distance = _rgb_distance(best[1], rgb)
        matches.append(
            {
                "detected_hex": hex_val,
                "closest_brand_colour": best[0],
                "distance": round(distance, 1),
                "is_brand_match": distance < 40,
            }
        )

    hit_count = sum(1 for m in matches if m["is_brand_match"])
    score = int(round((hit_count / max(1, len(matches))) * 100))
    return {
        "score": score,
        "detected_hexes": detected_hexes,
        "matches": matches,
        "note": (
            "Score is the percentage of dominant colours that land within "
            "40 RGB units of a Betano primary or tonal colour."
        ),
    }


def _guess_category_from_ratio(width: int, height: int) -> str:
    ratio = width / max(1, height)
    if ratio < 0.7:
        return "story"
    if 0.9 <= ratio <= 1.1:
        return "casino"
    if ratio > 1.7:
        return "slider"
    return "promo_banner"


def _derive_safe_areas(analysis: dict, width: int, height: int) -> list[dict]:
    zones = analysis.get("layout_zones") if isinstance(analysis, dict) else None
    if not isinstance(zones, list):
        return []
    result: list[dict] = []
    for z in zones:
        if not isinstance(z, dict):
            continue
        result.append(
            {
                "x": int(z.get("x_pct", 0) * width / 100),
                "y": int(z.get("y_pct", 0) * height / 100),
                "w": int(z.get("w_pct", 0) * width / 100),
                "h": int(z.get("h_pct", 0) * height / 100),
                "label": str(z.get("zone", "area")),
                "description": str(z.get("description", "")),
            }
        )
    return result


@router.get("", include_in_schema=False)
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
