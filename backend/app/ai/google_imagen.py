"""Google Imagen / Gemini AI provider for BrandForge."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.ai.provider import AIProvider, GenerationResult
from app.config import settings

logger = logging.getLogger(__name__)

# Cost estimate in cents per image generation call
_COST_PER_IMAGE_CENTS = 2


class GoogleImagenProvider(AIProvider):
    """AI provider backed by Google Imagen (image gen) and Gemini (analysis)."""

    def __init__(self) -> None:
        genai.configure(api_key=settings.google_ai_api_key)
        self._imagen_model = "imagen-3.0-generate-002"
        self._gemini_model = "gemini-2.0-flash"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        num_images: int = 1,
        style: dict | None = None,
    ) -> GenerationResult:
        """Generate images from a text prompt using Imagen."""
        try:
            enhanced_prompt = self._build_prompt(prompt, width, height, style)
            imagen = genai.ImageGenerationModel(self._imagen_model)

            response = imagen.generate_images(
                prompt=enhanced_prompt,
                number_of_images=num_images,
                aspect_ratio=self._aspect_ratio(width, height),
            )

            images: list[bytes] = []
            for generated_image in response.images:
                images.append(generated_image._image_bytes)

            return GenerationResult(
                images=images,
                layers=[],
                model_used=self._imagen_model,
                generation_params={
                    "prompt": enhanced_prompt,
                    "width": width,
                    "height": height,
                    "num_images": num_images,
                    "style": style,
                },
                cost_cents=_COST_PER_IMAGE_CENTS * num_images,
            )
        except Exception:
            logger.exception("Google Imagen generation failed")
            raise

    async def generate_layers(
        self,
        prompt: str,
        width: int,
        height: int,
        layer_descriptions: list[str],
    ) -> GenerationResult:
        """Generate separate layers by issuing one call per layer description."""
        try:
            imagen = genai.ImageGenerationModel(self._imagen_model)
            images: list[bytes] = []
            layers: list[dict] = []

            for idx, layer_desc in enumerate(layer_descriptions):
                if idx == 0:
                    layer_prompt = (
                        f"Background layer: {layer_desc}. "
                        f"Create a seamless background suitable for a "
                        f"{width}x{height} composition."
                    )
                else:
                    layer_prompt = (
                        f"Foreground element with transparent background: "
                        f"{layer_desc}. The element should be isolated on a "
                        f"clean transparent or solid-color background for easy "
                        f"compositing."
                    )

                response = imagen.generate_images(
                    prompt=layer_prompt,
                    number_of_images=1,
                    aspect_ratio=self._aspect_ratio(width, height),
                )

                layer_bytes = response.images[0]._image_bytes
                images.append(layer_bytes)
                layers.append(
                    {
                        "index": idx,
                        "description": layer_desc,
                        "prompt_used": layer_prompt,
                        "layer_type": "background" if idx == 0 else "subject",
                    }
                )

            return GenerationResult(
                images=images,
                layers=layers,
                model_used=self._imagen_model,
                generation_params={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "layer_descriptions": layer_descriptions,
                },
                cost_cents=_COST_PER_IMAGE_CENTS * len(layer_descriptions),
            )
        except Exception:
            logger.exception("Google Imagen layer generation failed")
            raise

    async def analyze_image(self, image_data: bytes) -> dict:
        """Use Gemini to analyse an image and extract structured layout info."""
        try:
            model = genai.GenerativeModel(self._gemini_model)

            analysis_prompt = (
                "Analyze this image in detail and return a JSON object with:\n"
                '1. "layout_zones": list of {zone, x_pct, y_pct, w_pct, h_pct, description}\n'
                '2. "dominant_colors": list of hex color strings\n'
                '3. "typography_style": {style, weight, estimated_fonts}\n'
                '4. "element_positions": list of {element, x_pct, y_pct, w_pct, h_pct}\n'
                '5. "overall_style": brief description of the visual style\n'
                "Return ONLY valid JSON, no markdown fences."
            )

            image_part = {
                "mime_type": "image/png",
                "data": base64.b64encode(image_data).decode("utf-8"),
            }

            response = model.generate_content(
                [analysis_prompt, image_part],
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                ),
            )

            return self._parse_json_response(response.text)
        except Exception:
            logger.exception("Google Gemini image analysis failed")
            raise

    async def generate_variations(
        self,
        image_data: bytes,
        prompt: str,
        num_variations: int = 3,
    ) -> GenerationResult:
        """Generate prompt-based variations of an image."""
        try:
            # Use Gemini to understand the source image first
            model = genai.GenerativeModel(self._gemini_model)
            image_part = {
                "mime_type": "image/png",
                "data": base64.b64encode(image_data).decode("utf-8"),
            }
            desc_response = model.generate_content(
                [
                    "Describe this image concisely for re-generation, "
                    "focusing on composition, colors, and key elements.",
                    image_part,
                ],
            )
            base_description = desc_response.text

            # Generate variations via Imagen with tweaked prompts
            imagen = genai.ImageGenerationModel(self._imagen_model)
            variation_prompts = [
                f"Variation {i + 1} of: {base_description}. {prompt}. "
                f"Create a distinct yet brand-consistent alternative."
                for i in range(num_variations)
            ]

            images: list[bytes] = []
            for vp in variation_prompts:
                response = imagen.generate_images(
                    prompt=vp,
                    number_of_images=1,
                )
                images.append(response.images[0]._image_bytes)

            return GenerationResult(
                images=images,
                layers=[],
                model_used=self._imagen_model,
                generation_params={
                    "prompt": prompt,
                    "base_description": base_description,
                    "num_variations": num_variations,
                },
                cost_cents=_COST_PER_IMAGE_CENTS * num_variations,
            )
        except Exception:
            logger.exception("Google Imagen variation generation failed")
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        prompt: str, width: int, height: int, style: dict | None
    ) -> str:
        parts = [prompt]
        if style:
            if style.get("mood"):
                parts.append(f"Mood: {style['mood']}.")
            if style.get("color_palette"):
                parts.append(f"Color palette: {', '.join(style['color_palette'])}.")
            if style.get("art_style"):
                parts.append(f"Art style: {style['art_style']}.")
        parts.append(f"Target dimensions: {width}x{height}.")
        return " ".join(parts)

    @staticmethod
    def _aspect_ratio(width: int, height: int) -> str:
        """Map dimensions to a supported Imagen aspect-ratio string."""
        ratio = width / height
        if abs(ratio - 1.0) < 0.1:
            return "1:1"
        elif ratio > 1.4:
            return "16:9"
        elif ratio > 1.1:
            return "4:3"
        elif ratio < 0.7:
            return "9:16"
        elif ratio < 0.9:
            return "3:4"
        return "1:1"

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
            logger.warning("Failed to parse Gemini JSON, returning raw text")
            return {"raw_response": text}
