"""Stability AI provider for BrandForge."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx

from app.ai.provider import AIProvider, GenerationResult
from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.stability.ai"
_COST_PER_IMAGE_CENTS = 1  # credit-based, ~$0.01 per image


class StabilityAIProvider(AIProvider):
    """AI provider backed by Stability AI REST API."""

    def __init__(self) -> None:
        self._api_key = settings.stability_api_key
        self._engine_id = "stable-diffusion-xl-1024-v1-0"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

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
        """Generate images via the Stability text-to-image endpoint."""
        try:
            w, h = self._snap_dimensions(width, height)
            enhanced_prompt = self._build_prompt(prompt, style)

            payload = {
                "text_prompts": [{"text": enhanced_prompt, "weight": 1.0}],
                "cfg_scale": 7,
                "width": w,
                "height": h,
                "samples": num_images,
                "steps": 30,
            }
            if style and style.get("negative_prompt"):
                payload["text_prompts"].append(
                    {"text": style["negative_prompt"], "weight": -1.0}
                )

            url = f"{_BASE_URL}/v1/generation/{self._engine_id}/text-to-image"

            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    url, json=payload, headers=self._headers()
                )
                response.raise_for_status()

            data = response.json()
            images = [
                base64.b64decode(artifact["base64"])
                for artifact in data.get("artifacts", [])
                if artifact.get("finishReason") == "SUCCESS"
            ]

            return GenerationResult(
                images=images,
                layers=[],
                model_used=self._engine_id,
                generation_params={
                    "prompt": enhanced_prompt,
                    "width": w,
                    "height": h,
                    "num_images": num_images,
                    "style": style,
                    "cfg_scale": 7,
                    "steps": 30,
                },
                cost_cents=_COST_PER_IMAGE_CENTS * num_images,
            )
        except Exception:
            logger.exception("Stability AI generation failed")
            raise

    async def generate_layers(
        self,
        prompt: str,
        width: int,
        height: int,
        layer_descriptions: list[str],
    ) -> GenerationResult:
        """Generate separate layers by issuing one call per description."""
        try:
            w, h = self._snap_dimensions(width, height)
            images: list[bytes] = []
            layers: list[dict] = []

            for idx, layer_desc in enumerate(layer_descriptions):
                if idx == 0:
                    layer_prompt = (
                        f"Background layer: {layer_desc}. "
                        f"Seamless background, no isolated subjects."
                    )
                else:
                    layer_prompt = (
                        f"Isolated element on transparent background: {layer_desc}. "
                        f"Clean edges for compositing."
                    )

                payload = {
                    "text_prompts": [{"text": layer_prompt, "weight": 1.0}],
                    "cfg_scale": 7,
                    "width": w,
                    "height": h,
                    "samples": 1,
                    "steps": 30,
                }

                url = f"{_BASE_URL}/v1/generation/{self._engine_id}/text-to-image"

                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(
                        url, json=payload, headers=self._headers()
                    )
                    response.raise_for_status()

                data = response.json()
                for artifact in data.get("artifacts", []):
                    if artifact.get("finishReason") == "SUCCESS":
                        images.append(base64.b64decode(artifact["base64"]))
                        break

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
                model_used=self._engine_id,
                generation_params={
                    "prompt": prompt,
                    "width": w,
                    "height": h,
                    "layer_descriptions": layer_descriptions,
                },
                cost_cents=_COST_PER_IMAGE_CENTS * len(layer_descriptions),
            )
        except Exception:
            logger.exception("Stability AI layer generation failed")
            raise

    async def analyze_image(self, image_data: bytes) -> dict:
        """Basic image analysis via Stability AI.

        Stability AI does not have a dedicated analysis endpoint comparable
        to Gemini / GPT-4V, so we return structural metadata derived from
        the image bytes themselves (dimensions, estimated palette) and flag
        that deeper analysis should use a multimodal provider.
        """
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))
            w, h = img.size

            # Extract dominant colors via quantization
            quantized = img.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
            palette = quantized.getpalette() or []
            colors: list[str] = []
            for i in range(min(6, len(palette) // 3)):
                r, g, b = palette[i * 3 : i * 3 + 3]
                colors.append(f"#{r:02x}{g:02x}{b:02x}")

            return {
                "width": w,
                "height": h,
                "dominant_colors": colors,
                "layout_zones": [],
                "typography_style": {},
                "element_positions": [],
                "overall_style": "Analysis limited – use Google or OpenAI provider for full multimodal analysis.",
            }
        except Exception:
            logger.exception("Stability AI image analysis failed")
            raise

    async def generate_variations(
        self,
        image_data: bytes,
        prompt: str,
        num_variations: int = 3,
    ) -> GenerationResult:
        """Generate variations using the image-to-image endpoint."""
        try:
            url = f"{_BASE_URL}/v1/generation/{self._engine_id}/image-to-image"

            images: list[bytes] = []
            for i in range(num_variations):
                variation_prompt = (
                    f"Variation {i + 1}: {prompt}. "
                    f"Visually distinct yet consistent in style."
                )

                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Accept": "application/json",
                        },
                        data={
                            "text_prompts[0][text]": variation_prompt,
                            "text_prompts[0][weight]": "1.0",
                            "init_image_mode": "IMAGE_STRENGTH",
                            "image_strength": "0.35",
                            "cfg_scale": "7",
                            "samples": "1",
                            "steps": "30",
                        },
                        files={
                            "init_image": ("image.png", image_data, "image/png"),
                        },
                    )
                    response.raise_for_status()

                data = response.json()
                for artifact in data.get("artifacts", []):
                    if artifact.get("finishReason") == "SUCCESS":
                        images.append(base64.b64decode(artifact["base64"]))
                        break

            return GenerationResult(
                images=images,
                layers=[],
                model_used=self._engine_id,
                generation_params={
                    "prompt": prompt,
                    "num_variations": num_variations,
                    "image_strength": 0.35,
                },
                cost_cents=_COST_PER_IMAGE_CENTS * num_variations,
            )
        except Exception:
            logger.exception("Stability AI variation generation failed")
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _snap_dimensions(width: int, height: int) -> tuple[int, int]:
        """Snap dimensions to multiples of 64 (SDXL requirement)."""
        w = max(512, min(width, 1536))
        h = max(512, min(height, 1536))
        w = (w // 64) * 64
        h = (h // 64) * 64
        return w, h

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
