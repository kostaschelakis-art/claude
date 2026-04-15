"""Brand guidelines, assets, and QA routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user
from app.auth.roles import check_market_access, require_role
from app.database import get_db
from app.models import (
    BrandAsset,
    BrandGuideline,
    BrandGuidelineCategory,
    BrandGuidelineScope,
    GeneratedImage,
    QAResult,
    User,
    UserRole,
)

router = APIRouter(prefix="/brand", tags=["brand"])


# --------------------------------------------------------------------------- #
# Request schemas
# --------------------------------------------------------------------------- #


class GuidelineCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(
        ...,
        pattern=r"^(color|typography|logo|graphics|illustration|imagery|positioning|motion)$",
    )
    scope: str = Field(default="global", pattern=r"^(global|market)$")
    market_id: uuid.UUID | None = None
    rules: dict = Field(default_factory=dict)
    examples: list[str] = Field(default_factory=list)
    priority: int = Field(default=0)
    is_active: bool = True


class GuidelineUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(
        default=None,
        pattern=r"^(color|typography|logo|graphics|illustration|imagery|positioning|motion)$",
    )
    scope: str | None = Field(default=None, pattern=r"^(global|market)$")
    market_id: uuid.UUID | None = None
    rules: dict | None = None
    examples: list[str] | None = None
    priority: int | None = None
    is_active: bool | None = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _guideline_to_dict(g: BrandGuideline) -> dict:
    return {
        "id": str(g.id),
        "name": g.name,
        "category": g.category.value,
        "scope": g.scope.value,
        "market_id": str(g.market_id) if g.market_id else None,
        "rules": g.rules,
        "examples": g.examples,
        "priority": g.priority,
        "is_active": g.is_active,
        "created_at": g.created_at.isoformat(),
        "updated_at": g.updated_at.isoformat(),
    }


def _asset_to_dict(a: BrandAsset) -> dict:
    return {
        "id": str(a.id),
        "name": a.name,
        "asset_type": a.asset_type.value,
        "file_url": a.file_url,
        "metadata": a.metadata_,
        "market_id": str(a.market_id) if a.market_id else None,
        "created_at": a.created_at.isoformat(),
    }


def _qa_to_dict(q: QAResult) -> dict:
    return {
        "id": str(q.id),
        "image_id": str(q.image_id),
        "overall_score": q.overall_score,
        "category_scores": q.category_scores,
        "violations": q.violations,
        "suggestions": q.suggestions,
        "evaluated_at": q.evaluated_at.isoformat(),
    }


# --------------------------------------------------------------------------- #
# Brand Guidelines routes
# --------------------------------------------------------------------------- #


@router.get("/guidelines")
async def list_guidelines(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List brand guidelines: global guidelines + guidelines for the user's market."""
    if current_user.role == UserRole.SUPER_ADMIN:
        result = await db.execute(
            select(BrandGuideline)
            .where(BrandGuideline.is_active.is_(True))
            .order_by(BrandGuideline.priority.desc(), BrandGuideline.name)
        )
    else:
        result = await db.execute(
            select(BrandGuideline)
            .where(
                BrandGuideline.is_active.is_(True),
                or_(
                    BrandGuideline.scope == BrandGuidelineScope.GLOBAL,
                    BrandGuideline.market_id == current_user.market_id,
                ),
            )
            .order_by(BrandGuideline.priority.desc(), BrandGuideline.name)
        )

    guidelines = result.scalars().all()
    return {
        "items": [_guideline_to_dict(g) for g in guidelines],
        "total": len(guidelines),
    }


@router.post("/guidelines", status_code=status.HTTP_201_CREATED)
async def create_guideline(
    body: GuidelineCreateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new brand guideline. Requires ADMIN role or above."""
    if body.scope == "market" and body.market_id is not None:
        check_market_access(current_user, body.market_id)

    try:
        category_enum = BrandGuidelineCategory(body.category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {body.category}",
        )

    scope_enum = BrandGuidelineScope(body.scope)

    guideline = BrandGuideline(
        id=uuid.uuid4(),
        name=body.name,
        category=category_enum,
        scope=scope_enum,
        market_id=body.market_id,
        rules=body.rules,
        examples=body.examples,
        priority=body.priority,
        is_active=body.is_active,
    )
    db.add(guideline)
    await db.flush()
    await db.refresh(guideline)

    return _guideline_to_dict(guideline)


@router.put("/guidelines/{guideline_id}")
async def update_guideline(
    guideline_id: uuid.UUID,
    body: GuidelineUpdateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing brand guideline."""
    result = await db.execute(
        select(BrandGuideline).where(BrandGuideline.id == guideline_id)
    )
    guideline = result.scalar_one_or_none()
    if guideline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand guideline not found",
        )

    # Non-super-admin admins can only update guidelines for their market
    if current_user.role != UserRole.SUPER_ADMIN:
        if guideline.market_id is not None and guideline.market_id != current_user.market_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this guideline",
            )

    update_data = body.model_dump(exclude_unset=True)

    if "category" in update_data and update_data["category"] is not None:
        try:
            update_data["category"] = BrandGuidelineCategory(update_data["category"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {update_data['category']}",
            )

    if "scope" in update_data and update_data["scope"] is not None:
        update_data["scope"] = BrandGuidelineScope(update_data["scope"])

    if "market_id" in update_data and update_data["market_id"] is not None:
        check_market_access(current_user, update_data["market_id"])

    for field, value in update_data.items():
        setattr(guideline, field, value)

    await db.flush()
    await db.refresh(guideline)

    return _guideline_to_dict(guideline)


@router.delete("/guidelines/{guideline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guideline(
    guideline_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a brand guideline."""
    result = await db.execute(
        select(BrandGuideline).where(BrandGuideline.id == guideline_id)
    )
    guideline = result.scalar_one_or_none()
    if guideline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand guideline not found",
        )

    if current_user.role != UserRole.SUPER_ADMIN:
        if guideline.market_id is not None and guideline.market_id != current_user.market_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this guideline",
            )

    await db.delete(guideline)
    await db.flush()
    return None


# --------------------------------------------------------------------------- #
# Brand Assets routes
# --------------------------------------------------------------------------- #


@router.post("/assets", status_code=status.HTTP_201_CREATED)
async def upload_brand_asset(
    file: UploadFile = File(...),
    name: str | None = Query(default=None, max_length=255),
    asset_type: str = Query(default="logo", pattern=r"^(logo|font|graphic|icon|pattern)$"),
    market_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(require_role(UserRole.CREATOR)),
    db: AsyncSession = Depends(get_db),
):
    """Upload a brand asset file and persist the bytes to object storage.

    ``name`` defaults to the uploaded filename (minus extension) and
    ``asset_type`` defaults to ``logo`` so the simple "Upload Brand
    Asset" button on the Brand Guidelines page works with no extra
    UI.
    """
    if market_id is not None:
        check_market_access(current_user, market_id)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file upload")
    file_size = len(content)

    from app.models import AssetType
    from app.services.storage_service import S3Client

    try:
        asset_type_enum = AssetType(asset_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid asset type: {asset_type}",
        )

    # Persist the bytes to MinIO and proxy them back via the backend
    # (the browser can't reach the internal ``minio:9000`` hostname).
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() or "png"
    if ext not in {"png", "jpg", "jpeg", "webp", "svg", "gif"}:
        ext = "png"
    asset_id = uuid.uuid4()
    storage_key = f"brand-assets/{asset_id}.{ext}"

    try:
        storage = S3Client()
        await storage.ensure_bucket()
        await storage.upload(
            key=storage_key,
            data=content,
            content_type=file.content_type or f"image/{ext}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to store brand asset: {exc}",
        )

    file_url = f"/api/v1/brand/assets/{asset_id}/file"

    display_name = name or (file.filename or "Brand asset").rsplit(".", 1)[0][:255]

    asset = BrandAsset(
        id=asset_id,
        name=display_name,
        asset_type=asset_type_enum,
        file_url=file_url,
        metadata_={
            "original_filename": file.filename,
            "content_type": file.content_type,
            "file_size": file_size,
            "storage_key": storage_key,
        },
        market_id=market_id,
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)

    return _asset_to_dict(asset)


@router.get("/assets")
async def list_brand_assets(
    asset_type: str | None = Query(default=None, pattern=r"^(logo|font|graphic|icon|pattern)$"),
    market_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List brand assets with optional filters."""
    query = select(BrandAsset)

    if asset_type is not None:
        from app.models import AssetType
        query = query.where(BrandAsset.asset_type == AssetType(asset_type))

    if market_id is not None:
        check_market_access(current_user, market_id)
        query = query.where(
            (BrandAsset.market_id == market_id) | (BrandAsset.market_id.is_(None))
        )
    elif current_user.role != UserRole.SUPER_ADMIN:
        query = query.where(
            (BrandAsset.market_id == current_user.market_id)
            | (BrandAsset.market_id.is_(None))
        )

    query = query.order_by(BrandAsset.created_at.desc())
    result = await db.execute(query)
    assets = result.scalars().all()

    return {
        "items": [_asset_to_dict(a) for a in assets],
        "total": len(assets),
    }


@router.get("/assets/{asset_id}/file")
async def get_brand_asset_file(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Stream a brand asset's bytes. Unauthenticated so ``<img>`` tags work."""
    from fastapi.responses import Response

    from app.services.storage_service import S3Client

    result = await db.execute(
        select(BrandAsset).where(BrandAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="Brand asset not found")

    meta = asset.metadata_ or {}
    key = meta.get("storage_key")
    if not key:
        raise HTTPException(status_code=404, detail="Asset bytes unavailable")

    try:
        data = await S3Client().download(key)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail=f"Asset bytes unavailable: {exc}"
        )

    media_type = meta.get("content_type") or "application/octet-stream"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


# --------------------------------------------------------------------------- #
# QA routes
# --------------------------------------------------------------------------- #


@router.post("/qa/{image_id}", status_code=status.HTTP_201_CREATED)
async def run_qa(
    image_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run QA on an image (placeholder -- returns mock scores).

    A real implementation would evaluate the image against applicable brand
    guidelines using AI-powered checks.
    """
    result = await db.execute(
        select(GeneratedImage).where(GeneratedImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Mock QA evaluation
    qa_result = QAResult(
        id=uuid.uuid4(),
        image_id=image_id,
        overall_score=82.5,
        category_scores={
            "color": {"score": 90.0, "weight": 1.0, "explanation": "Colors within brand palette"},
            "typography": {"score": 85.0, "weight": 1.0, "explanation": "Font usage is compliant"},
            "logo": {"score": 70.0, "weight": 1.5, "explanation": "Logo placement could be improved"},
            "composition": {"score": 80.0, "weight": 1.0, "explanation": "Good overall layout"},
        },
        violations=[
            {
                "category": "logo",
                "severity": "minor",
                "description": "Logo clear space is slightly below recommended minimum",
                "expected": "16px clear space",
                "actual": "12px clear space",
            }
        ],
        suggestions=[
            {
                "category": "logo",
                "description": "Increase clear space around logo to 16px minimum",
                "auto_fixable": True,
                "fix_action": {"type": "adjust_padding", "target": "logo", "value": 16},
            },
            {
                "category": "color",
                "description": "Consider using the primary brand color for the CTA button",
                "auto_fixable": False,
            },
        ],
    )
    db.add(qa_result)
    await db.flush()
    await db.refresh(qa_result)

    return _qa_to_dict(qa_result)


@router.get("/qa/{image_id}")
async def get_qa_results(
    image_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get QA results for an image."""
    # Verify image exists
    img_result = await db.execute(
        select(GeneratedImage).where(GeneratedImage.id == image_id)
    )
    if img_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    result = await db.execute(
        select(QAResult)
        .where(QAResult.image_id == image_id)
        .order_by(QAResult.evaluated_at.desc())
    )
    qa_results = result.scalars().all()

    return {
        "image_id": str(image_id),
        "items": [_qa_to_dict(q) for q in qa_results],
        "total": len(qa_results),
    }
