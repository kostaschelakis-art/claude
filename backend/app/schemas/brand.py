import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- BrandGuideline schemas ---


class BrandGuidelineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(
        ...,
        pattern=r"^(color|typography|logo|graphics|illustration|imagery|positioning|motion)$",
    )
    scope: str = Field(
        default="global",
        pattern=r"^(global|market)$",
    )
    market_id: uuid.UUID | None = None
    rules: dict = Field(
        default_factory=dict,
        description=(
            "Guideline rules. Structure depends on category. "
            "Example for color: {primary: '#FF0000', secondary: '#00FF00', "
            "forbidden: ['#000000'], contrast_ratio_min: 4.5}"
        ),
    )
    examples: list[str] = Field(
        default_factory=list,
        description="List of example image URLs demonstrating correct usage",
    )
    priority: int = Field(
        default=0,
        description="Higher priority guidelines override lower ones (0 = lowest)",
    )
    is_active: bool = True


class BrandGuidelineCreate(BrandGuidelineBase):
    pass


class BrandGuidelineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(
        default=None,
        pattern=r"^(color|typography|logo|graphics|illustration|imagery|positioning|motion)$",
    )
    scope: str | None = Field(
        default=None,
        pattern=r"^(global|market)$",
    )
    market_id: uuid.UUID | None = None
    rules: dict | None = None
    examples: list[str] | None = None
    priority: int | None = None
    is_active: bool | None = None


class BrandGuidelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    scope: str
    market_id: uuid.UUID | None = None
    rules: dict | None = None
    examples: list | None = None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BrandGuidelineListResponse(BaseModel):
    items: list[BrandGuidelineResponse]
    total: int


# --- BrandAsset schemas ---


class BrandAssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    asset_type: str = Field(
        ...,
        pattern=r"^(logo|font|graphic|icon|pattern)$",
    )
    file_url: str
    metadata_: dict = Field(
        default_factory=dict,
        alias="metadata",
        description=(
            "Asset metadata: {dimensions: {w, h}, colors: [...], "
            "usage_rules: {min_size: 48, clear_space: 16, ...}}"
        ),
    )
    market_id: uuid.UUID | None = None


class BrandAssetCreate(BrandAssetBase):
    pass


class BrandAssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_type: str | None = Field(
        default=None,
        pattern=r"^(logo|font|graphic|icon|pattern)$",
    )
    file_url: str | None = None
    metadata_: dict | None = Field(default=None, alias="metadata")
    market_id: uuid.UUID | None = None


class BrandAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    asset_type: str
    file_url: str
    metadata_: dict | None = Field(default=None, alias="metadata")
    market_id: uuid.UUID | None = None
    created_at: datetime


class BrandAssetListResponse(BaseModel):
    items: list[BrandAssetResponse]
    total: int


# --- QAResult schemas ---


class QAViolation(BaseModel):
    """A single brand guideline violation detected in QA."""

    guideline_id: uuid.UUID | None = None
    category: str = Field(
        ..., description="Violation category (e.g. 'color', 'logo', 'typography')"
    )
    severity: str = Field(
        ...,
        pattern=r"^(critical|major|minor|info)$",
    )
    description: str
    location: dict | None = Field(
        default=None, description="Where in the image: {x, y, w, h}"
    )
    expected: str | None = None
    actual: str | None = None


class QASuggestion(BaseModel):
    """A suggestion for improving brand compliance."""

    category: str
    description: str
    auto_fixable: bool = False
    fix_action: dict | None = Field(
        default=None,
        description="Automated fix definition if auto_fixable is True",
    )


class QACategoryScore(BaseModel):
    """Score breakdown for a single QA category."""

    category: str
    score: float = Field(..., ge=0.0, le=100.0)
    weight: float = Field(
        default=1.0, ge=0.0, description="Weight of this category in overall score"
    )
    explanation: str = Field(
        default="", description="Human-readable explanation of the score"
    )


class QAResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    overall_score: float
    category_scores: dict | None = None
    violations: list | None = None
    suggestions: list | None = None
    evaluated_at: datetime


class QAResultDetailResponse(BaseModel):
    """Detailed QA result with structured breakdowns and explanations."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    overall_score: float = Field(..., ge=0.0, le=100.0)
    category_breakdown: list[QACategoryScore] = Field(
        default_factory=list,
        description="Score breakdown by category with explanations",
    )
    violations: list[QAViolation] = Field(default_factory=list)
    suggestions: list[QASuggestion] = Field(default_factory=list)
    pass_threshold: float = Field(
        default=70.0, description="Minimum score to pass QA"
    )
    passed: bool = Field(
        ..., description="Whether the image passed QA"
    )
    evaluated_at: datetime


# --- FeedbackLoop schemas ---


class FeedbackLoopCreate(BaseModel):
    image_id: uuid.UUID
    qa_result_id: uuid.UUID
    user_rating: int = Field(..., ge=1, le=5)


class FeedbackLoopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    qa_result_id: uuid.UUID
    user_rating: int
    used_in_training: bool
    created_at: datetime
