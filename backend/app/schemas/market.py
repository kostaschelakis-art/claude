import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LegalDisclaimer(BaseModel):
    """A single legal disclaimer entry for a market."""

    text: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(..., min_length=2, max_length=10)
    placement: str = Field(
        default="footer",
        description="Where the disclaimer should appear (e.g. footer, overlay, banner)",
    )
    is_required: bool = True


class RestrictedContentRule(BaseModel):
    """A single restricted content rule for a market."""

    rule: str = Field(..., min_length=1, max_length=2000)
    category: str = Field(
        ...,
        description="Category of restriction (e.g. minors, alcohol, gambling_imagery)",
    )
    severity: str = Field(
        default="block",
        pattern=r"^(block|warn|review)$",
        description="Action to take when rule is violated",
    )


class MarketBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=2, max_length=10)
    display_name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    legal_disclaimers: list[LegalDisclaimer] = Field(default_factory=list)
    restricted_content_rules: list[RestrictedContentRule] = Field(default_factory=list)
    data_region: str | None = None
    storage_bucket: str | None = None


class MarketCreate(MarketBase):
    pass


class MarketUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=2, max_length=10)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    legal_disclaimers: list[LegalDisclaimer] | None = None
    restricted_content_rules: list[RestrictedContentRule] | None = None
    data_region: str | None = None
    storage_bucket: str | None = None


class MarketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    display_name: str
    is_active: bool
    legal_disclaimers: list[dict] | None = None
    restricted_content_rules: list[dict] | None = None
    data_region: str | None = None
    storage_bucket: str | None = None
    created_at: datetime


class MarketBrief(BaseModel):
    """Lightweight market representation for embedding in other responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    display_name: str


class MarketListResponse(BaseModel):
    items: list[MarketResponse]
    total: int


# --- MarketBrandOverride schemas ---


class MarketBrandOverrideBase(BaseModel):
    market_id: uuid.UUID
    brand_guideline_id: uuid.UUID
    override_config: dict = Field(default_factory=dict)


class MarketBrandOverrideCreate(MarketBrandOverrideBase):
    pass


class MarketBrandOverrideUpdate(BaseModel):
    override_config: dict


class MarketBrandOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    market_id: uuid.UUID
    brand_guideline_id: uuid.UUID
    override_config: dict | None = None
