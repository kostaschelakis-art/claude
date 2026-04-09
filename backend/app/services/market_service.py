"""Market-specific configuration and legal overlay service."""

from __future__ import annotations

import io
import logging
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Default market configurations
# ------------------------------------------------------------------

DEFAULT_MARKET_CONFIGS: dict[str, dict[str, Any]] = {
    "PT": {
        "name": "Portugal",
        "legal": [],
    },
    "DE": {
        "name": "Germany",
        "legal": ["Gambling can be addictive. Play responsibly."],
    },
    "ON": {
        "name": "Ontario",
        "legal": ["18+ Terms & Conditions Apply"],
        "restrictions": ["No real tournament trophies (e.g. World Cup Trophy)"],
    },
    "BR": {
        "name": "Brazil",
        "legal": ["18+ Jogue com responsabilidade"],
    },
    "GR": {
        "name": "Greece",
        "legal": ["\u0395\u0395\u0395\u03a0 - \u03a0\u03b1\u03af\u03be\u03b5 \u03a5\u03c0\u03b5\u03cd\u03b8\u03c5\u03bd\u03b1"],
    },
}


class MarketService:
    """Provides market-specific legal requirements and overlay application."""

    def get_legal_requirements(self, market_code: str) -> list[dict]:
        """Return legal requirements for the given market code.

        Parameters
        ----------
        market_code:
            Two-letter market code (e.g. ``"ON"``, ``"DE"``).

        Returns
        -------
        list[dict]
            Each dict has ``text`` and optional ``position`` keys.
        """
        config = DEFAULT_MARKET_CONFIGS.get(market_code, {})
        legal_texts: list[str] = config.get("legal", [])
        restrictions: list[str] = config.get("restrictions", [])

        requirements: list[dict] = []
        for text in legal_texts:
            requirements.append(
                {
                    "text": text,
                    "type": "disclaimer",
                    "position": "bottom-center",
                    "required": True,
                }
            )
        for restriction in restrictions:
            requirements.append(
                {
                    "text": restriction,
                    "type": "restriction",
                    "required": True,
                }
            )

        return requirements

    def apply_legal_overlay(
        self,
        image_data: bytes,
        market_code: str,
        width: int,
        height: int,
    ) -> bytes:
        """Add required legal text overlay to an image.

        The text is rendered at the bottom center of the image with a
        semi-transparent background strip for readability.

        Parameters
        ----------
        image_data:
            Raw image bytes.
        market_code:
            Two-letter market code.
        width, height:
            Canvas dimensions (used for positioning).

        Returns
        -------
        bytes
            PNG image bytes with the legal overlay applied.
        """
        config = DEFAULT_MARKET_CONFIGS.get(market_code, {})
        legal_texts: list[str] = config.get("legal", [])

        if not legal_texts:
            return image_data  # No overlay needed

        try:
            img = Image.open(io.BytesIO(image_data)).convert("RGBA")

            # Resize to target dimensions if they differ
            if img.size != (width, height):
                img = img.resize((width, height), Image.LANCZOS)

            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            # Font
            font_size = max(12, height // 40)
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size
                )
            except (OSError, IOError):
                font = ImageFont.load_default()

            combined_text = " | ".join(legal_texts)

            # Measure text
            bbox = draw.textbbox((0, 0), combined_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # Semi-transparent background strip at the bottom
            strip_padding = 8
            strip_h = text_h + strip_padding * 2
            strip_y = height - strip_h

            draw.rectangle(
                [(0, strip_y), (width, height)],
                fill=(0, 0, 0, 160),
            )

            # Center the text
            text_x = (width - text_w) // 2
            text_y = strip_y + strip_padding

            draw.text(
                (text_x, text_y),
                combined_text,
                fill=(255, 255, 255, 255),
                font=font,
            )

            result = Image.alpha_composite(img, overlay)

            buf = io.BytesIO()
            result.save(buf, format="PNG")
            return buf.getvalue()

        except Exception:
            logger.exception(
                "Failed to apply legal overlay for market %s", market_code
            )
            return image_data  # Return original on failure
