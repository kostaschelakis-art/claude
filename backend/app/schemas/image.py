import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Layer schemas ---


class LayerBase(BaseModel):
    layer_index: int = Field(..., ge=0)
    layer_type: str = Field(
        ...,
        pattern=r"^(background|subject|text|logo|overlay|effect)$",
    )
    content_url: str | None = None
    properties: dict = Field(
        default_factory=dict,
        description="Layer properties: position, size, opacity, effects, blendMode",
    )
    is_editable: bool = True


class LayerCreate(LayerBase):
    image_id: uuid.UUID


class LayerUpdate(BaseModel):
    layer_index: int | None = Field(default=None, ge=0)
    content_url: str | None = None
    properties: dict | None = None
    is_editable: bool | None = None


class LayerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    layer_index: int
    layer_type: str
    content_url: str | None = None
    properties: dict | None = None
    is_editable: bool
    created_at: datetime


# --- Image generation request ---


class DimensionsPreset(BaseModel):
    """Predefined dimension presets for common formats."""

    preset: str = Field(
        ...,
        description=(
            "Preset name: 'story_1080x1920', 'push_512x512', "
            "'email_600x400', 'banner_1200x628', 'slider_800x600', "
            "'in_app_375x667', 'custom'"
        ),
    )
    custom_width: int | None = Field(default=None, gt=0, le=10000)
    custom_height: int | None = Field(default=None, gt=0, le=10000)


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    template_id: uuid.UUID | None = None
    market_id: uuid.UUID
    dimensions: DimensionsPreset = Field(
        default_factory=lambda: DimensionsPreset(preset="custom", custom_width=1024, custom_height=1024)
    )
    ai_provider: str | None = Field(
        default=None,
        pattern=r"^(google|openai|stability)$",
        description="AI provider override; uses server default if not set",
    )
    ai_model: str | None = Field(
        default=None,
        description="Specific model name (e.g. 'gemini-2.0-flash', 'dall-e-3')",
    )
    style_preferences: dict | None = Field(
        default=None,
        description=(
            "Style preferences: {style, color_palette, mood, "
            "composition, negative_prompt, seed, steps, cfg_scale}"
        ),
    )
    auto_apply_brand: bool = Field(
        default=True,
        description="Automatically apply brand guidelines to prompt refinement",
    )
    layers_config: list[LayerBase] | None = Field(
        default=None,
        description="Pre-defined layer structure for composite generation",
    )


# --- Image response schemas ---


class ImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt: str
    refined_prompt: str | None = None
    user_id: uuid.UUID
    market_id: uuid.UUID
    template_id: uuid.UUID | None = None
    ai_provider: str
    ai_model: str | None = None
    status: str
    layers: list[dict] | None = None
    composite_url: str | None = None
    width: int | None = None
    height: int | None = None
    format: str | None = None
    file_size_bytes: int | None = None
    generation_params: dict | None = None
    created_at: datetime


class ImageDetailResponse(ImageResponse):
    """Extended image response including related layers, reviews, and QA results."""

    image_layers: list[LayerResponse] = Field(default_factory=list)
    reviews: list["ImageReviewResponse"] = Field(default_factory=list)
    qa_score: float | None = None


class ImageBrief(BaseModel):
    """Lightweight image reference for lists."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt: str
    status: str
    composite_url: str | None = None
    width: int | None = None
    height: int | None = None
    ai_provider: str
    created_at: datetime


class ImageListResponse(BaseModel):
    items: list[ImageBrief]
    total: int
    page: int
    page_size: int


# --- Review schemas ---


class ImageReviewCreate(BaseModel):
    image_id: uuid.UUID
    score: int | None = Field(default=None, ge=1, le=5)
    thumbs: bool | None = None
    feedback_text: str | None = Field(default=None, max_length=4000)


class ImageReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    reviewer_id: uuid.UUID
    score: int | None = None
    thumbs: bool | None = None
    feedback_text: str | None = None
    created_at: datetime


# --- Export schemas ---


class ImageExportRequest(BaseModel):
    image_id: uuid.UUID
    format: str = Field(
        ...,
        pattern=r"^(png|jpg|webp|svg|pdf)$",
    )
    width: int = Field(..., gt=0, le=10000)
    height: int = Field(..., gt=0, le=10000)
    preset_name: str | None = Field(
        default=None,
        description="Export preset name (e.g. 'facebook_story', 'email_header')",
    )
    quality: int = Field(
        default=90, ge=1, le=100, description="Compression quality (for jpg/webp)"
    )


class ImageExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    format: str
    width: int
    height: int
    preset_name: str | None = None
    file_url: str | None = None
    file_size_bytes: int | None = None
    created_at: datetime


# Rebuild forward refs for ImageDetailResponse
ImageDetailResponse.model_rebuild()
