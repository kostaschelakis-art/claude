import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TemplateCategory(str, enum.Enum):
    EMAIL = "email"
    STORY = "story"
    PUSH = "push"
    SLIDER = "slider"
    PROMO_BANNER = "promo_banner"
    IN_APP = "in_app"
    NEWSLETTER = "newsletter"
    CASINO = "casino"
    SPORTS = "sports"
    CUSTOM = "custom"


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    category: Mapped[TemplateCategory] = mapped_column(
        Enum(TemplateCategory, name="template_category", native_enum=True),
        nullable=False,
        index=True,
    )
    market_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("markets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    layout_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    dimensions_width: Mapped[int] = mapped_column(Integer, nullable=False)
    dimensions_height: Mapped[int] = mapped_column(Integer, nullable=False)
    safe_areas: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    persistent_elements: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    is_ai_generated: Mapped[bool] = mapped_column(default=False, nullable=False)
    source_image_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    market: Mapped["Market"] = relationship(  # noqa: F821
        "Market", back_populates="templates", lazy="selectin"
    )
    created_by_user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="templates_created", lazy="selectin"
    )
    variations: Mapped[list["TemplateVariation"]] = relationship(
        "TemplateVariation", back_populates="template", cascade="all, delete-orphan"
    )
    generated_images: Mapped[list["GeneratedImage"]] = relationship(  # noqa: F821
        "GeneratedImage", back_populates="template"
    )

    __table_args__ = (
        Index("ix_templates_category_market", "category", "market_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Template(id={self.id!r}, name={self.name!r}, "
            f"category={self.category!r})>"
        )


class TemplateVariation(Base):
    __tablename__ = "template_variations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variation_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    preview_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    template: Mapped["Template"] = relationship(
        "Template", back_populates="variations"
    )

    def __repr__(self) -> str:
        return (
            f"<TemplateVariation(id={self.id!r}, "
            f"template_id={self.template_id!r})>"
        )
