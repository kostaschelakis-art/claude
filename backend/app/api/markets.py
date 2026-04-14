"""Market management routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user
from app.auth.roles import require_role
from app.database import get_db
from app.models import Market, User, UserRole

router = APIRouter(prefix="/markets", tags=["markets"])


# --------------------------------------------------------------------------- #
# Request schemas
# --------------------------------------------------------------------------- #


class MarketCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=2, max_length=10)
    display_name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    legal_disclaimers: list[dict] = Field(default_factory=list)
    restricted_content_rules: list[dict] = Field(default_factory=list)
    data_region: str | None = None
    storage_bucket: str | None = None


class MarketUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=2, max_length=10)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    data_region: str | None = None
    storage_bucket: str | None = None


class LegalDisclaimersUpdate(BaseModel):
    legal_disclaimers: list[dict]


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #


def _market_to_dict(m: Market) -> dict:
    return {
        "id": str(m.id),
        "name": m.name,
        "code": m.code,
        "display_name": m.display_name,
        "is_active": m.is_active,
        "legal_disclaimers": m.legal_disclaimers,
        "restricted_content_rules": m.restricted_content_rules,
        "data_region": m.data_region,
        "storage_bucket": m.storage_bucket,
        "created_at": m.created_at.isoformat(),
    }


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.get("", include_in_schema=False)
@router.get("/")
async def list_markets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List markets. Super-admins see all; others see only their own market."""
    if current_user.role == UserRole.SUPER_ADMIN:
        result = await db.execute(
            select(Market).order_by(Market.name)
        )
        markets = result.scalars().all()
    else:
        if current_user.market_id is None:
            return {"items": [], "total": 0}
        result = await db.execute(
            select(Market).where(Market.id == current_user.market_id)
        )
        markets = result.scalars().all()

    return {
        "items": [_market_to_dict(m) for m in markets],
        "total": len(markets),
    }


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))],
)
async def create_market(
    body: MarketCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new market (super-admin only)."""
    # Check for duplicate code
    existing = await db.execute(
        select(Market).where(Market.code == body.code)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Market with code '{body.code}' already exists",
        )

    market = Market(
        id=uuid.uuid4(),
        name=body.name,
        code=body.code,
        display_name=body.display_name,
        is_active=body.is_active,
        legal_disclaimers=body.legal_disclaimers,
        restricted_content_rules=body.restricted_content_rules,
        data_region=body.data_region,
        storage_bucket=body.storage_bucket,
    )
    db.add(market)
    await db.flush()
    await db.refresh(market)

    return _market_to_dict(market)


@router.get("/{market_id}")
async def get_market(
    market_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific market."""
    # Non-super-admin users can only view their own market
    if current_user.role != UserRole.SUPER_ADMIN:
        if current_user.market_id != market_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this market",
            )

    result = await db.execute(
        select(Market).where(Market.id == market_id)
    )
    market = result.scalar_one_or_none()
    if market is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market not found",
        )

    return _market_to_dict(market)


@router.put("/{market_id}")
async def update_market(
    market_id: uuid.UUID,
    body: MarketUpdateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update a market. Requires ADMIN role or above."""
    # Non-super-admin admins can only update their own market
    if current_user.role != UserRole.SUPER_ADMIN:
        if current_user.market_id != market_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this market",
            )

    result = await db.execute(
        select(Market).where(Market.id == market_id)
    )
    market = result.scalar_one_or_none()
    if market is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market not found",
        )

    update_data = body.model_dump(exclude_unset=True)

    # Check for code uniqueness if updating code
    if "code" in update_data and update_data["code"] is not None:
        existing = await db.execute(
            select(Market).where(
                Market.code == update_data["code"],
                Market.id != market_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Market with code '{update_data['code']}' already exists",
            )

    for field, value in update_data.items():
        setattr(market, field, value)

    await db.flush()
    await db.refresh(market)

    return _market_to_dict(market)


@router.put("/{market_id}/legal")
async def update_legal_disclaimers(
    market_id: uuid.UUID,
    body: LegalDisclaimersUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update the legal disclaimers for a market. Requires ADMIN role or above."""
    if current_user.role != UserRole.SUPER_ADMIN:
        if current_user.market_id != market_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this market",
            )

    result = await db.execute(
        select(Market).where(Market.id == market_id)
    )
    market = result.scalar_one_or_none()
    if market is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market not found",
        )

    market.legal_disclaimers = body.legal_disclaimers
    await db.flush()
    await db.refresh(market)

    return _market_to_dict(market)
