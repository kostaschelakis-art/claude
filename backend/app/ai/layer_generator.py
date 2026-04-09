"""Image layer composition utilities using Pillow."""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


@dataclass
class LayerData:
    """Description of a single compositing layer."""

    image_data: bytes
    layer_type: str  # background, subject, text, logo, overlay, effect
    z_index: int
    x: int = 0
    y: int = 0
    width: int | None = None
    height: int | None = None
    opacity: float = 1.0
    blend_mode: str = "normal"
    effects: list[dict] | None = None


# ------------------------------------------------------------------
# Layer composition
# ------------------------------------------------------------------


def compose_layers(layers: list[LayerData], width: int, height: int) -> bytes:
    """Composite *layers* (sorted by ``z_index``) onto an RGBA canvas.

    Returns the final image as PNG bytes.
    """
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    sorted_layers = sorted(layers, key=lambda l: l.z_index)

    for layer in sorted_layers:
        img = Image.open(io.BytesIO(layer.image_data)).convert("RGBA")

        # Resize if explicit dimensions are given
        target_w = layer.width or img.width
        target_h = layer.height or img.height
        if (target_w, target_h) != img.size:
            img = img.resize((target_w, target_h), Image.LANCZOS)

        # Apply per-layer effects before compositing
        if layer.effects:
            for effect_def in layer.effects:
                effect_name = effect_def.get("effect", "")
                params = {k: v for k, v in effect_def.items() if k != "effect"}
                buf = _image_to_bytes(img)
                buf = apply_effect(buf, effect_name, params)
                img = Image.open(io.BytesIO(buf)).convert("RGBA")

        # Apply opacity
        if layer.opacity < 1.0:
            alpha = img.split()[3]
            alpha = alpha.point(lambda p: int(p * layer.opacity))
            img.putalpha(alpha)

        # Paste onto canvas
        canvas.paste(img, (layer.x, layer.y), img)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


# ------------------------------------------------------------------
# Effects
# ------------------------------------------------------------------

_EFFECT_HANDLERS: dict[str, object] = {}  # populated below


def apply_effect(image_data: bytes, effect: str, params: dict) -> bytes:
    """Apply a visual *effect* to an image.

    Supported effects:
        blur, sharpen, brightness, contrast, saturation,
        color_overlay, drop_shadow, grayscale.
    """
    img = Image.open(io.BytesIO(image_data)).convert("RGBA")

    if effect == "blur":
        radius = params.get("radius", 2)
        img = img.filter(ImageFilter.GaussianBlur(radius=radius))

    elif effect == "sharpen":
        factor = params.get("factor", 2.0)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(factor)

    elif effect == "brightness":
        factor = params.get("factor", 1.2)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(factor)

    elif effect == "contrast":
        factor = params.get("factor", 1.2)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(factor)

    elif effect == "saturation":
        factor = params.get("factor", 1.3)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(factor)

    elif effect == "color_overlay":
        color = params.get("color", "#FF6600")
        overlay_opacity = params.get("opacity", 0.3)
        overlay = Image.new("RGBA", img.size, _hex_to_rgba(color, overlay_opacity))
        img = Image.alpha_composite(img, overlay)

    elif effect == "drop_shadow":
        offset_x = params.get("offset_x", 5)
        offset_y = params.get("offset_y", 5)
        shadow_color = params.get("color", "#000000")
        blur_radius = params.get("blur", 5)
        r, g, b = _hex_to_rgb(shadow_color)

        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shadow_layer = Image.new("RGBA", img.size, (r, g, b, 120))
        shadow.paste(shadow_layer, (offset_x, offset_y), img.split()[3])
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        shadow = Image.alpha_composite(shadow, img)
        img = shadow

    elif effect == "grayscale":
        gray = img.convert("LA").convert("RGBA")
        img = gray

    else:
        pass  # Unknown effect -- return image unchanged

    return _image_to_bytes(img)


# ------------------------------------------------------------------
# Text layer
# ------------------------------------------------------------------


def add_text_layer(
    width: int,
    height: int,
    text: str,
    font_size: int = 24,
    color: str = "white",
    position: tuple[int, int] = (0, 0),
    font_family: str | None = None,
    rotation: int = 0,
    stroke_color: str | None = None,
    stroke_width: int = 0,
) -> bytes:
    """Render *text* onto a transparent RGBA canvas and return PNG bytes."""
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    try:
        if font_family:
            font = ImageFont.truetype(font_family, font_size)
        else:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    draw_kwargs: dict = {
        "xy": position,
        "text": text,
        "fill": color,
        "font": font,
    }
    if stroke_color and stroke_width > 0:
        draw_kwargs["stroke_fill"] = stroke_color
        draw_kwargs["stroke_width"] = stroke_width

    draw.text(**draw_kwargs)

    if rotation:
        canvas = canvas.rotate(rotation, expand=False, resample=Image.BICUBIC)

    return _image_to_bytes(canvas)


# ------------------------------------------------------------------
# Logo layer
# ------------------------------------------------------------------


def add_logo_layer(
    logo_data: bytes,
    canvas_w: int,
    canvas_h: int,
    position: dict,
    size: dict,
    opacity: float = 1.0,
) -> bytes:
    """Place a logo image on a transparent canvas at *position* with *size*.

    ``position`` should be ``{"x": int, "y": int}``.
    ``size`` should be ``{"width": int, "height": int}``.
    """
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    logo = Image.open(io.BytesIO(logo_data)).convert("RGBA")

    target_w = size.get("width", logo.width)
    target_h = size.get("height", logo.height)
    logo = logo.resize((target_w, target_h), Image.LANCZOS)

    if opacity < 1.0:
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        logo.putalpha(alpha)

    x = position.get("x", 0)
    y = position.get("y", 0)
    canvas.paste(logo, (x, y), logo)

    return _image_to_bytes(canvas)


# ------------------------------------------------------------------
# Resize
# ------------------------------------------------------------------


def resize_image(
    image_data: bytes,
    width: int,
    height: int,
    mode: str = "fit",
) -> bytes:
    """Resize an image.

    Modes:
        * ``fit``   -- scale to fit within *width* x *height*, preserving aspect ratio.
        * ``fill``  -- scale & crop to exactly fill *width* x *height*.
        * ``stretch`` -- distort to exactly *width* x *height*.
    """
    img = Image.open(io.BytesIO(image_data)).convert("RGBA")

    if mode == "fit":
        img.thumbnail((width, height), Image.LANCZOS)
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        offset_x = (width - img.width) // 2
        offset_y = (height - img.height) // 2
        canvas.paste(img, (offset_x, offset_y), img)
        img = canvas

    elif mode == "fill":
        src_ratio = img.width / img.height
        dst_ratio = width / height
        if src_ratio > dst_ratio:
            # Wider than target -- fit height, crop width
            new_h = height
            new_w = int(height * src_ratio)
        else:
            new_w = width
            new_h = int(width / src_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        img = img.crop((left, top, left + width, top + height))

    elif mode == "stretch":
        img = img.resize((width, height), Image.LANCZOS)

    return _image_to_bytes(img)


# ------------------------------------------------------------------
# Safe areas
# ------------------------------------------------------------------


def get_safe_areas(width: int, height: int) -> list[dict]:
    """Return recommended safe areas based on canvas dimensions.

    Always includes *title safe* (80 % center) and *action safe* (90 % center).
    """
    areas: list[dict] = []

    # Title safe -- 80 % center
    tw = int(width * 0.8)
    th = int(height * 0.8)
    areas.append(
        {
            "x": (width - tw) // 2,
            "y": (height - th) // 2,
            "w": tw,
            "h": th,
            "label": "title_safe",
        }
    )

    # Action safe -- 90 % center
    aw = int(width * 0.9)
    ah = int(height * 0.9)
    areas.append(
        {
            "x": (width - aw) // 2,
            "y": (height - ah) // 2,
            "w": aw,
            "h": ah,
            "label": "action_safe",
        }
    )

    return areas


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _image_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _hex_to_rgba(hex_color: str, opacity: float) -> tuple[int, int, int, int]:
    r, g, b = _hex_to_rgb(hex_color)
    return (r, g, b, int(255 * opacity))
