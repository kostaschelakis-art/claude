"""Google Gemini image generation + vision provider.

Uses the ``google-genai`` SDK which supports:

    * ``gemini-2.5-flash-image`` / ``gemini-2.5-flash-image-preview`` —
      free-tier image generation (great for hobby / demo scale).
    * ``gemini-2.5-flash`` / ``gemini-2.0-flash`` — multimodal analysis
      used to inspect uploaded reference images.

The previous implementation targeted Imagen-3 via the legacy
``google-generativeai`` package, which required a paid AI Studio tier
and exposed an API surface (``ImageGenerationModel``) that has since
been removed.  This module replaces it and is safe to call with a free
``GOOGLE_AI_API_KEY`` generated from https://aistudio.google.com.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.ai.provider import AIProvider, GenerationResult
from app.config import settings

logger = logging.getLogger(__name__)

# Free-tier Gemini image generation.
_IMAGE_MODEL = "gemini-2.5-flash-image"
_IMAGE_MODEL_FALLBACK = "gemini-2.0-flash-preview-image-generation"
_TEXT_MODEL = "gemini-2.5-flash"

# Cost estimate in cents per image — essentially free tier, track a nominal 0.
_COST_PER_IMAGE_CENTS = 0


class GoogleImagenProvider(AIProvider):
    """AI provider backed by Google's Gemini multimodal API."""

    def __init__(self) -> None:
        if not settings.google_ai_api_key:
            raise RuntimeError(
                "GOOGLE_AI_API_KEY is not configured. "
                "Generate one at https://aistudio.google.com and put it in .env."
            )
        self._client = genai.Client(api_key=settings.google_ai_api_key)

    # ------------------------------------------------------------------
    # Core image generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        num_images: int = 1,
        style: dict | None = None,
    ) -> GenerationResult:
        """Generate one or more images from a text prompt."""
        images: list[bytes] = []
        model_used = _IMAGE_MODEL

        for _ in range(max(1, num_images)):
            image_bytes = await asyncio.to_thread(self._call_image_model, prompt)
            images.append(image_bytes)

        return GenerationResult(
            images=images,
            layers=[],
            model_used=model_used,
            generation_params={
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_images": num_images,
                "style": style,
            },
            cost_cents=_COST_PER_IMAGE_CENTS * num_images,
        )

    async def generate_layers(
        self,
        prompt: str,
        width: int,
        height: int,
        layer_descriptions: list[str],
    ) -> GenerationResult:
        """Generate each layer with a separate call.

        Gemini image gen does not natively support transparent subjects,
        so we request each layer with explicit instructions to isolate
        the subject on a neutral background.
        """
        images: list[bytes] = []
        layers: list[dict] = []

        for idx, desc in enumerate(layer_descriptions):
            if idx == 0:
                layer_prompt = (
                    f"{prompt}\n\nLayer brief — background only: {desc}. "
                    "Create a seamless background suitable for layering "
                    "foreground elements on top."
                )
            else:
                layer_prompt = (
                    f"{prompt}\n\nLayer brief — foreground element: {desc}. "
                    "Isolate the subject clearly on a plain neutral "
                    "background so it can be composited later."
                )

            image_bytes = await asyncio.to_thread(self._call_image_model, layer_prompt)
            images.append(image_bytes)
            layers.append(
                {
                    "index": idx,
                    "description": desc,
                    "prompt_used": layer_prompt,
                    "layer_type": "background" if idx == 0 else "subject",
                }
            )

        return GenerationResult(
            images=images,
            layers=layers,
            model_used=_IMAGE_MODEL,
            generation_params={
                "prompt": prompt,
                "width": width,
                "height": height,
                "layer_descriptions": layer_descriptions,
            },
            cost_cents=_COST_PER_IMAGE_CENTS * len(layer_descriptions),
        )

    async def analyze_image(self, image_data: bytes) -> dict:
        """Use Gemini to analyse an image and extract structured info."""
        analysis_prompt = (
            "Analyse this marketing image and return a JSON object with:\n"
            '1. "layout_zones": list of {zone, x_pct, y_pct, w_pct, h_pct, description}\n'
            '2. "dominant_colors": list of {hex, role} where role is one of '
            '"background", "accent", "foreground"\n'
            '3. "typography_style": {style, weight, uppercase, estimated_family}\n'
            '4. "element_positions": list of {element, x_pct, y_pct, w_pct, h_pct}\n'
            '5. "suggested_category": one of email, story, push, slider, '
            "promo_banner, in_app, newsletter, casino, sports, custom\n"
            '6. "overall_style": brief description\n'
            "Return ONLY valid JSON, no markdown fences."
        )

        def _call() -> str:
            response = self._client.models.generate_content(
                model=_TEXT_MODEL,
                contents=[
                    analysis_prompt,
                    genai_types.Part.from_bytes(data=image_data, mime_type="image/png"),
                ],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return response.text or ""

        text = await asyncio.to_thread(_call)
        return self._parse_json_response(text)

    async def generate_variations(
        self,
        image_data: bytes,
        prompt: str,
        num_variations: int = 3,
    ) -> GenerationResult:
        """Describe the source image, then generate variations from the description."""
        def _describe() -> str:
            desc_response = self._client.models.generate_content(
                model=_TEXT_MODEL,
                contents=[
                    "Describe this image concisely for re-generation — focus on "
                    "composition, colour palette, and key visual elements.",
                    genai_types.Part.from_bytes(data=image_data, mime_type="image/png"),
                ],
            )
            return (desc_response.text or "").strip()

        base_description = await asyncio.to_thread(_describe)

        variation_prompts = [
            f"Variation {i + 1} of: {base_description}\n\n"
            f"User request: {prompt}\n"
            "Create a distinct yet brand-consistent alternative."
            for i in range(num_variations)
        ]

        images: list[bytes] = []
        for vp in variation_prompts:
            images.append(await asyncio.to_thread(self._call_image_model, vp))

        return GenerationResult(
            images=images,
            layers=[],
            model_used=_IMAGE_MODEL,
            generation_params={
                "prompt": prompt,
                "base_description": base_description,
                "num_variations": num_variations,
            },
            cost_cents=_COST_PER_IMAGE_CENTS * num_variations,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_image_model(self, prompt: str) -> bytes:
        """Invoke the Gemini image model and return the first image's bytes.

        Tries the stable model first; if it's unavailable (e.g. region
        restriction), falls back to the preview model id.
        """
        errors: list[str] = []
        for model_id in (_IMAGE_MODEL, _IMAGE_MODEL_FALLBACK):
            try:
                response = self._client.models.generate_content(
                    model=model_id,
                    contents=[prompt],
                    config=genai_types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                    ),
                )
                image_bytes = self._extract_first_image(response)
                if image_bytes is not None:
                    return image_bytes
                errors.append(f"{model_id}: no inline image in response")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{model_id}: {exc}")
                logger.warning("Gemini image call on %s failed: %s", model_id, exc)

        raise RuntimeError(
            "Gemini image generation failed on all models: " + "; ".join(errors)
        )

    @staticmethod
    def _extract_first_image(response: Any) -> bytes | None:
        """Walk the Gemini response and return the first inline image bytes."""
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            parts = getattr(content, "parts", None) or []
            for part in parts:
                inline = getattr(part, "inline_data", None)
                if inline is None:
                    continue
                data = getattr(inline, "data", None)
                if isinstance(data, (bytes, bytearray)):
                    return bytes(data)
                if isinstance(data, str):
                    try:
                        return base64.b64decode(data)
                    except Exception:  # noqa: BLE001
                        continue
        return None

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        """Best-effort parse of a JSON response from Gemini."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini JSON; returning raw text")
            return {"raw_response": text}
