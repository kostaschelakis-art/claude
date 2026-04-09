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


class ImageStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEW = "review"


class LayerType(str, enum.Enum):
    BACKGROUND = "background"
    SUBJECT = "subject"
    TEXT = "text"
    LOGO = "logo"
    OVERLAY = "overlay"
    EFFECT = "effect"


class ExportFormat(str, enum.Enum):
    PNG = "png"
    JPG = "jpg"
    WEBP = "webp"
    SVG = "svg"
    PDF = "pdf"


class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    prompt: Mapped[str] = mapped_column(String(4000), nullable=False)
    refined_prompt: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    market_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("markets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ai_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ImageStatus] = mapped_column(
        Enum(ImageStatus, name="image_status", native_enum=True),
        nullable=False,
        default=ImageStatus.PENDING,
        index=True,
    )
    layers: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    composite_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str | None] = mapped_column(String(10), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_params: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="generated_images", lazy="selectin"
    )
    market: Mapped["Market"] = relationship(  # noqa: F821
        "Market", back_populates="generated_images", lazy="selectin"
    )
    template: Mapped["Template"] = relationship(  # noqa: F821
        "Template", back_populates="generated_images", lazy="selectin"
    )
    image_layers: Mapped[list["ImageLayer"]] = relationship(
        "ImageLayer", back_populates="image", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["ImageReview"]] = relationship(
        "ImageReview", back_populates="image", cascade="all, delete-orphan"
    )
    exports: Mapped[list["ImageExport"]] = relationship(
        "ImageExport", back_populates="image", cascade="all, delete-orphan"
    )
    qa_results: Mapped[list["QAResult"]] = relationship(  # noqa: F821
        "QAResult", back_populates="image", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_generated_images_user_status", "user_id", "status"),
        Index("ix_generated_images_market_status", "market_id", "status"),
        Index("ix_generated_images_created", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<GeneratedImage(id={self.id!r}, status={self.status!r}, "
            f"provider={self.ai_provider!r})>"
        )


class ImageLayer(Base):
    __tablename__ = "image_layers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    layer_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    layer_type: Mapped[LayerType] = mapped_column(
        Enum(LayerType, name="layer_type", native_enum=True),
        nullable=False,
    )
    content_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    properties: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=dict
    )
    is_editable: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    image: Mapped["GeneratedImage"] = relationship(
        "GeneratedImage", back_populates="image_layers"
    )

    __table_args__ = (
        Index("ix_image_layers_image_index", "image_id", "layer_index"),
    )

    def __repr__(self) -> str:
        return (
            f"<ImageLayer(id={self.id!r}, image_id={self.image_id!r}, "
            f"layer_type={self.layer_type!r}, index={self.layer_index!r})>"
        )


class ImageReview(Base):
    __tablename__ = "image_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbs: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    image: Mapped["GeneratedImage"] = relationship(
        "GeneratedImage", back_populates="reviews"
    )
    reviewer: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="image_reviews"
    )

    __table_args__ = (
        Index("ix_image_reviews_image_reviewer", "image_id", "reviewer_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ImageReview(id={self.id!r}, image_id={self.image_id!r}, "
            f"score={self.score!r})>"
        )


class ImageExport(Base):
    __tablename__ = "image_exports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format: Mapped[ExportFormat] = mapped_column(
        Enum(ExportFormat, name="export_format", native_enum=True),
        nullable=False,
    )
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    preset_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    image: Mapped["GeneratedImage"] = relationship(
        "GeneratedImage", back_populates="exports"
    )

    __table_args__ = (
        Index("ix_image_exports_image_format", "image_id", "format"),
    )

    def __repr__(self) -> str:
        return (
            f"<ImageExport(id={self.id!r}, image_id={self.image_id!r}, "
            f"format={self.format!r})>"
        )
