"""Image editor routes: compositing, text, effects, and safe areas."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.middleware import get_current_user
from app.models import User

router = APIRouter(prefix="/editor", tags=["editor"])


# --------------------------------------------------------------------------- #
# Request / Response schemas
# --------------------------------------------------------------------------- #


class LayerConfig(BaseModel):
    layer_type: str = Field(
        ...,
        pattern=r"^(background|subject|text|logo|overlay|effect)$",
    )
    content_url: str | None = None
    properties: dict = Field(default_factory=dict)
    position: dict = Field(
        default_factory=lambda: {"x": 0, "y": 0},
        description="Layer position: {x, y}",
    )
    size: dict = Field(
        default_factory=lambda: {"width": 100, "height": 100},
        description="Layer size: {width, height}",
    )
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    blend_mode: str = Field(default="normal")


class CompositeRequest(BaseModel):
    image_id: uuid.UUID
    layers: list[LayerConfig]
    output_width: int = Field(..., gt=0, le=10000)
    output_height: int = Field(..., gt=0, le=10000)
    output_format: str = Field(default="png", pattern=r"^(png|jpg|webp)$")


class AddTextRequest(BaseModel):
    image_id: uuid.UUID
    text: str = Field(..., min_length=1, max_length=2000)
    font_family: str = Field(default="Arial")
    font_size: int = Field(default=24, gt=0, le=500)
    font_weight: str = Field(default="normal", pattern=r"^(normal|bold|light)$")
    color: str = Field(default="#000000", pattern=r"^#[0-9a-fA-F]{6}$")
    position: dict = Field(
        default_factory=lambda: {"x": 0, "y": 0},
        description="Text position: {x, y}",
    )
    alignment: str = Field(default="left", pattern=r"^(left|center|right)$")
    max_width: int | None = Field(default=None, gt=0, le=10000)
    rotation: float = Field(default=0.0, ge=-360.0, le=360.0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)


class ApplyEffectRequest(BaseModel):
    image_id: uuid.UUID
    layer_id: uuid.UUID | None = None
    effect_type: str = Field(
        ...,
        pattern=r"^(blur|brightness|contrast|saturation|hue_rotate|grayscale|sepia|drop_shadow|glow|vignette)$",
    )
    params: dict = Field(
        default_factory=dict,
        description="Effect parameters (type-specific). E.g., {radius: 5} for blur.",
    )


class SafeAreaDefinition(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    w: int = Field(..., gt=0)
    h: int = Field(..., gt=0)
    label: str = Field(..., min_length=1, max_length=100)
    type: str = Field(
        default="exclude",
        pattern=r"^(exclude|include|text_only|logo_only)$",
        description="Safe area type: exclude (keep clear), include (must fill), text_only, logo_only",
    )


class SafeAreasRequest(BaseModel):
    image_id: uuid.UUID
    safe_areas: list[SafeAreaDefinition]


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.post("/composite")
async def composite_layers(
    body: CompositeRequest,
    current_user: User = Depends(get_current_user),
):
    """Accept layer configs and return a composited image URL.

    This is a placeholder -- a production implementation would use Pillow/Cairo
    or a dedicated compositing service to merge layers into a final image.
    """
    composite_id = uuid.uuid4()
    return {
        "composite_id": str(composite_id),
        "image_id": str(body.image_id),
        "composite_url": f"/composites/{composite_id}/output.{body.output_format}",
        "output_width": body.output_width,
        "output_height": body.output_height,
        "output_format": body.output_format,
        "layer_count": len(body.layers),
        "status": "completed",
        "note": "This is a placeholder. A production implementation would perform actual image compositing.",
    }


@router.post("/add-text")
async def add_text_layer(
    body: AddTextRequest,
    current_user: User = Depends(get_current_user),
):
    """Accept text parameters and return layer info.

    Placeholder -- a production implementation would render the text onto a
    transparent layer and return the layer URL.
    """
    layer_id = uuid.uuid4()
    return {
        "layer_id": str(layer_id),
        "image_id": str(body.image_id),
        "layer_type": "text",
        "content_url": f"/layers/{layer_id}/text_render.png",
        "properties": {
            "text": body.text,
            "font_family": body.font_family,
            "font_size": body.font_size,
            "font_weight": body.font_weight,
            "color": body.color,
            "alignment": body.alignment,
            "max_width": body.max_width,
            "rotation": body.rotation,
            "opacity": body.opacity,
        },
        "position": body.position,
        "is_editable": True,
        "status": "created",
    }


@router.post("/apply-effect")
async def apply_effect(
    body: ApplyEffectRequest,
    current_user: User = Depends(get_current_user),
):
    """Accept effect parameters and apply to an image or layer.

    Placeholder -- a production implementation would process the effect and
    return the modified image/layer URL.
    """
    effect_id = uuid.uuid4()
    return {
        "effect_id": str(effect_id),
        "image_id": str(body.image_id),
        "layer_id": str(body.layer_id) if body.layer_id else None,
        "effect_type": body.effect_type,
        "params": body.params,
        "result_url": f"/effects/{effect_id}/result.png",
        "status": "applied",
        "note": "This is a placeholder. A production implementation would apply the image effect.",
    }


@router.post("/safe-areas")
async def define_safe_areas(
    body: SafeAreasRequest,
    current_user: User = Depends(get_current_user),
):
    """Define safe areas for an image.

    Safe areas indicate regions that should be kept clear of content (exclude)
    or must contain specific element types (text_only, logo_only).
    """
    return {
        "image_id": str(body.image_id),
        "safe_areas": [
            {
                "id": str(uuid.uuid4()),
                "x": sa.x,
                "y": sa.y,
                "w": sa.w,
                "h": sa.h,
                "label": sa.label,
                "type": sa.type,
            }
            for sa in body.safe_areas
        ],
        "total": len(body.safe_areas),
        "status": "defined",
    }
