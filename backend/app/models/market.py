import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    legal_disclaimers: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    restricted_content_rules: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    data_region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    storage_bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User", back_populates="market"
    )
    templates: Mapped[list["Template"]] = relationship(  # noqa: F821
        "Template", back_populates="market"
    )
    generated_images: Mapped[list["GeneratedImage"]] = relationship(  # noqa: F821
        "GeneratedImage", back_populates="market"
    )
    brand_overrides: Mapped[list["MarketBrandOverride"]] = relationship(
        "MarketBrandOverride", back_populates="market", cascade="all, delete-orphan"
    )
    brand_guidelines: Mapped[list["BrandGuideline"]] = relationship(  # noqa: F821
        "BrandGuideline", back_populates="market"
    )
    brand_assets: Mapped[list["BrandAsset"]] = relationship(  # noqa: F821
        "BrandAsset", back_populates="market"
    )

    __table_args__ = (
        Index("ix_markets_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Market(id={self.id!r}, code={self.code!r}, name={self.name!r})>"


class MarketBrandOverride(Base):
    __tablename__ = "market_brand_overrides"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    market_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("markets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_guideline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brand_guidelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    override_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )

    # Relationships
    market: Mapped["Market"] = relationship("Market", back_populates="brand_overrides")
    brand_guideline: Mapped["BrandGuideline"] = relationship(  # noqa: F821
        "BrandGuideline", back_populates="market_overrides"
    )

    __table_args__ = (
        Index(
            "ix_market_brand_overrides_market_guideline",
            "market_id",
            "brand_guideline_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketBrandOverride(id={self.id!r}, market_id={self.market_id!r}, "
            f"brand_guideline_id={self.brand_guideline_id!r})>"
        )
