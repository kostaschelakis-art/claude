"""OpenAI DALL-E AI provider for BrandForge."""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any

import openai

from app.ai.provider import AIProvider, GenerationResult
from app.config import settings

logger = logging.getLogger(__name__)

# Cost in cents (DALL-E 3)
_COST_1024 = 4  # $0.04
_COST_LARGE = 8  # $0.08  (1024x1792 / 1792x1024)


class OpenAIDalleProvider(AIProvider):
    """AI provider backed by OpenAI DALL-E 3 and GPT-4 Vision."""

    def __init__(self) -> None:
        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self._dalle_model = "dall-e-3"
        self._vision_model = "gpt-4o"

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
        """Generate images with DALL-E 3."""
        try:
            size = self._map_size(width, height)
            enhanced_prompt = self._build_prompt(prompt, style)
            cost_per = _COST_LARGE if max(width, height) > 1024 else _COST_1024

            images: list[bytes] = []
            # DALL-E 3 only supports n=1 per call
            for _ in range(num_images):
                response = await self._client.images.generate(
                    model=self._dalle_model,
                    prompt=enhanced_prompt,
                    n=1,
                    size=size,
                    response_format="b64_json",
                    quality="hd",
                )
                b64_data = response.data[0].b64_json
                images.append(base64.b64decode(b64_data))

            return GenerationResult(
                images=images,
                layers=[],
                model_used=self._dalle_model,
                generation_params={
                    "prompt": enhanced_prompt,
                    "width": width,
                    "height": height,
                    "size": size,
                    "num_images": num_images,
                    "style": style,
                },
                cost_cents=cost_per * num_images,
            )
        except Exception:
            logger.exception("OpenAI DALL-E generation failed")
            raise

    async def generate_layers(
        self,
        prompt: str,
        width: int,
        height: int,
        layer_descriptions: list[str],
    ) -> GenerationResult:
        """Generate layers by issuing separate DALL-E calls per layer."""
        try:
            size = self._map_size(width, height)
            cost_per = _COST_LARGE if max(width, height) > 1024 else _COST_1024

            images: list[bytes] = []
            layers: list[dict] = []

            for idx, layer_desc in enumerate(layer_descriptions):
                if idx == 0:
                    layer_prompt = (
                        f"Background layer for a promotional banner: {layer_desc}. "
                        f"Full coverage, no text."
                    )
                else:
                    layer_prompt = (
                        f"Isolated element on a pure white background: {layer_desc}. "
                        f"The subject should be cleanly separated from the background "
                        f"for compositing."
                    )

                response = await self._client.images.generate(
                    model=self._dalle_model,
                    prompt=layer_prompt,
                    n=1,
                    size=size,
                    response_format="b64_json",
                    quality="hd",
                )

                b64_data = response.data[0].b64_json
                layer_bytes = base64.b64decode(b64_data)
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
                model_used=self._dalle_model,
                generation_params={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "layer_descriptions": layer_descriptions,
                },
                cost_cents=cost_per * len(layer_descriptions),
            )
        except Exception:
            logger.exception("OpenAI DALL-E layer generation failed")
            raise

    async def analyze_image(self, image_data: bytes) -> dict:
        """Use GPT-4 Vision to analyze an image."""
        try:
            b64_image = base64.b64encode(image_data).decode("utf-8")

            response = await self._client.chat.completions.create(
                model=self._vision_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a design analysis assistant. Analyze the image "
                            "and return ONLY a JSON object (no markdown fences)."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Analyze this image and return a JSON object with:\n"
                                    '1. "layout_zones": list of {zone, x_pct, y_pct, w_pct, h_pct, description}\n'
                                    '2. "dominant_colors": list of hex color strings\n'
                                    '3. "typography_style": {style, weight, estimated_fonts}\n'
                                    '4. "element_positions": list of {element, x_pct, y_pct, w_pct, h_pct}\n'
                                    '5. "overall_style": brief description of the visual style'
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64_image}",
                                    "detail": "high",
                                },
                            },
                        ],
                    },
                ],
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            return self._parse_json_response(
                response.choices[0].message.content or "{}"
            )
        except Exception:
            logger.exception("OpenAI Vision analysis failed")
            raise

    async def generate_variations(
        self,
        image_data: bytes,
        prompt: str,
        num_variations: int = 3,
    ) -> GenerationResult:
        """Generate variations using GPT-4V description + DALL-E re-generation."""
        try:
            # Describe the source image with GPT-4 Vision
            b64_image = base64.b64encode(image_data).decode("utf-8")
            desc_response = await self._client.chat.completions.create(
                model=self._vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Describe this image concisely for re-generation. "
                                    "Focus on composition, colors, and key elements."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64_image}",
                                    "detail": "low",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=500,
            )
            base_description = desc_response.choices[0].message.content or ""

            # Generate variations
            images: list[bytes] = []
            cost_per = _COST_1024

            for i in range(num_variations):
                variation_prompt = (
                    f"Create variation {i + 1} inspired by: {base_description}. "
                    f"{prompt}. Make it visually distinct but brand-consistent."
                )
                response = await self._client.images.generate(
                    model=self._dalle_model,
                    prompt=variation_prompt,
                    n=1,
                    size="1024x1024",
                    response_format="b64_json",
                    quality="hd",
                )
                b64_data = response.data[0].b64_json
                images.append(base64.b64decode(b64_data))

            return GenerationResult(
                images=images,
                layers=[],
                model_used=self._dalle_model,
                generation_params={
                    "prompt": prompt,
                    "base_description": base_description,
                    "num_variations": num_variations,
                },
                cost_cents=cost_per * num_variations,
            )
        except Exception:
            logger.exception("OpenAI DALL-E variation generation failed")
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_size(width: int, height: int) -> str:
        """Map requested dimensions to a supported DALL-E 3 size string."""
        ratio = width / height
        if ratio > 1.3:
            return "1792x1024"
        elif ratio < 0.7:
            return "1024x1792"
        return "1024x1024"

    @staticmethod
    def _build_prompt(prompt: str, style: dict | None) -> str:
        parts = [prompt]
        if style:
            if style.get("mood"):
                parts.append(f"Mood: {style['mood']}.")
            if style.get("color_palette"):
                parts.append(f"Color palette: {', '.join(style['color_palette'])}.")
            if style.get("art_style"):
                parts.append(f"Art style: {style['art_style']}.")
        return " ".join(parts)

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Vision JSON response")
            return {"raw_response": text}
