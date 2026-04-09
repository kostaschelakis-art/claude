import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BrandGuidelineCategory(str, enum.Enum):
    COLOR = "color"
    TYPOGRAPHY = "typography"
    LOGO = "logo"
    GRAPHICS = "graphics"
    ILLUSTRATION = "illustration"
    IMAGERY = "imagery"
    POSITIONING = "positioning"
    MOTION = "motion"


class BrandGuidelineScope(str, enum.Enum):
    GLOBAL = "global"
    MARKET = "market"


class AssetType(str, enum.Enum):
    LOGO = "logo"
    FONT = "font"
    GRAPHIC = "graphic"
    ICON = "icon"
    PATTERN = "pattern"


class BrandGuideline(Base):
    __tablename__ = "brand_guidelines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[BrandGuidelineCategory] = mapped_column(
        Enum(
            BrandGuidelineCategory,
            name="brand_guideline_category",
            native_enum=True,
        ),
        nullable=False,
        index=True,
    )
    scope: Mapped[BrandGuidelineScope] = mapped_column(
        Enum(
            BrandGuidelineScope,
            name="brand_guideline_scope",
            native_enum=True,
        ),
        nullable=False,
        default=BrandGuidelineScope.GLOBAL,
        index=True,
    )
    market_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("markets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rules: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    examples: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    market: Mapped["Market"] = relationship(  # noqa: F821
        "Market", back_populates="brand_guidelines", lazy="selectin"
    )
    market_overrides: Mapped[list["MarketBrandOverride"]] = relationship(  # noqa: F821
        "MarketBrandOverride",
        back_populates="brand_guideline",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_brand_guidelines_scope_market", "scope", "market_id"),
        Index("ix_brand_guidelines_category_active", "category", "is_active"),
        Index("ix_brand_guidelines_priority", "priority"),
    )

    def __repr__(self) -> str:
        return (
            f"<BrandGuideline(id={self.id!r}, name={self.name!r}, "
            f"category={self.category!r}, scope={self.scope!r})>"
        )


class BrandAsset(Base):
    __tablename__ = "brand_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type", native_enum=True),
        nullable=False,
        index=True,
    )
    file_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
    market_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("markets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    market: Mapped["Market"] = relationship(  # noqa: F821
        "Market", back_populates="brand_assets", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_brand_assets_type_market", "asset_type", "market_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<BrandAsset(id={self.id!r}, name={self.name!r}, "
            f"asset_type={self.asset_type!r})>"
        )


class QAResult(Base):
    __tablename__ = "qa_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    category_scores: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    violations: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    suggestions: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    image: Mapped["GeneratedImage"] = relationship(  # noqa: F821
        "GeneratedImage", back_populates="qa_results"
    )
    feedback_loops: Mapped[list["FeedbackLoop"]] = relationship(
        "FeedbackLoop", back_populates="qa_result", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_qa_results_score", "overall_score"),
        Index("ix_qa_results_evaluated", "evaluated_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<QAResult(id={self.id!r}, image_id={self.image_id!r}, "
            f"overall_score={self.overall_score!r})>"
        )


class FeedbackLoop(Base):
    __tablename__ = "feedback_loops"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qa_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("qa_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    used_in_training: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    qa_result: Mapped["QAResult"] = relationship(
        "QAResult", back_populates="feedback_loops"
    )

    __table_args__ = (
        Index("ix_feedback_loops_training", "used_in_training"),
    )

    def __repr__(self) -> str:
        return (
            f"<FeedbackLoop(id={self.id!r}, image_id={self.image_id!r}, "
            f"user_rating={self.user_rating!r})>"
        )
