import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SafeArea(BaseModel):
    """Rectangular safe area within a template."""

    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    w: int = Field(..., gt=0)
    h: int = Field(..., gt=0)
    label: str | None = Field(
        default=None, description="Optional label (e.g. 'logo_zone', 'text_area')"
    )


class PersistentElement(BaseModel):
    """An element that always appears on the template (logo, watermark, etc.)."""

    element_type: str = Field(
        ..., description="Type of element (e.g. 'logo', 'watermark', 'disclaimer')"
    )
    asset_url: str
    position: dict = Field(
        ..., description="Position config: {x, y, anchor}"
    )
    size: dict = Field(
        ..., description="Size config: {width, height}"
    )
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    locked: bool = True


class TemplateBase(BaseModel):
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
    safe_areas: list[SafeArea] = Field(default_factory=list)
    persistent_elements: list[PersistentElement] = Field(default_factory=list)
    is_ai_generated: bool = False
    source_image_url: str | None = None


class TemplateCreate(TemplateBase):
    created_by: uuid.UUID


class TemplateUpdate(BaseModel):
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
    safe_areas: list[SafeArea] | None = None
    persistent_elements: list[PersistentElement] | None = None
    is_ai_generated: bool | None = None
    source_image_url: str | None = None


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    category: str
    market_id: uuid.UUID | None = None
    created_by: uuid.UUID
    layout_config: dict | None = None
    dimensions_width: int
    dimensions_height: int
    safe_areas: list[dict] | None = None
    persistent_elements: list[dict] | None = None
    is_ai_generated: bool
    source_image_url: str | None = None
    created_at: datetime


class TemplateBrief(BaseModel):
    """Lightweight template representation for lists."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    dimensions_width: int
    dimensions_height: int
    market_id: uuid.UUID | None = None


class TemplateListResponse(BaseModel):
    items: list[TemplateBrief]
    total: int
    page: int
    page_size: int


# --- TemplateVariation schemas ---


class TemplateVariationBase(BaseModel):
    variation_config: dict = Field(default_factory=dict)
    preview_url: str | None = None


class TemplateVariationCreate(TemplateVariationBase):
    template_id: uuid.UUID


class TemplateVariationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    template_id: uuid.UUID
    variation_config: dict | None = None
    preview_url: str | None = None
    created_at: datetime


# --- Template analysis (upload image to extract template) ---


class TemplateAnalysisRequest(BaseModel):
    """Request to analyze an uploaded image and extract template structure."""

    image_url: str = Field(
        ..., description="URL of the uploaded image to analyze"
    )
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(
        ...,
        pattern=r"^(email|story|push|slider|promo_banner|in_app|newsletter|casino|sports|custom)$",
    )
    market_id: uuid.UUID | None = None
    detect_safe_areas: bool = Field(
        default=True,
        description="Whether to auto-detect safe areas from the image",
    )
    detect_persistent_elements: bool = Field(
        default=True,
        description="Whether to auto-detect logos and watermarks",
    )


class TemplateAnalysisResponse(BaseModel):
    template: TemplateResponse
    detected_safe_areas: list[SafeArea] = Field(default_factory=list)
    detected_elements: list[PersistentElement] = Field(default_factory=list)
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score of the analysis"
    )
