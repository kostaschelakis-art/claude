"""Template analysis and variation service."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import get_provider
from app.config import settings
from app.models.template import Template, TemplateVariation

logger = logging.getLogger(__name__)


class TemplateService:
    """Handles template analysis from uploaded images and variation generation."""

    async def analyze_upload(
        self,
        image_data: bytes,
        ai_provider_name: str = "google",
    ) -> dict:
        """Analyze an uploaded image and extract template structure.

        Uses the specified AI provider's ``analyze_image`` method to infer
        layout zones, dominant colors, typography hints, and element positions.

        Parameters
        ----------
        image_data:
            Raw bytes of the uploaded image.
        ai_provider_name:
            AI provider to use for the analysis.

        Returns
        -------
        dict
            Structured analysis result from the AI provider, typically containing
            ``layout_zones``, ``dominant_colors``, ``typography_style``,
            ``element_positions``, and ``overall_style``.
        """
        provider = get_provider(ai_provider_name)

        try:
            analysis = await provider.analyze_image(image_data)
            logger.info("Template analysis completed via %s", ai_provider_name)
            return analysis
        except Exception:
            logger.exception(
                "Template analysis failed with provider %s", ai_provider_name
            )
            raise

    async def generate_variations(
        self,
        template_id: str,
        num_variations: int,
        db_session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Generate visual variations of an existing template.

        Parameters
        ----------
        template_id:
            UUID of the source template.
        num_variations:
            How many variations to produce.
        db_session:
            Active async database session.

        Returns
        -------
        list[dict]
            List of variation metadata dicts, each containing ``id``,
            ``template_id``, and ``variation_config``.
        """
        # Load the template
        stmt = select(Template).where(Template.id == uuid.UUID(template_id))
        result = await db_session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        provider_name = settings.default_ai_provider
        provider = get_provider(provider_name)

        # Build a descriptive prompt from template metadata
        description_parts = [template.name]
        if template.description:
            description_parts.append(template.description)
        if template.layout_config:
            description_parts.append(f"Layout: {template.layout_config}")

        base_prompt = ". ".join(description_parts)

        try:
            # If the template has a source image, generate image-based variations
            # Otherwise, fall back to prompt-based generation
            gen_result = await provider.generate(
                prompt=base_prompt,
                width=template.dimensions_width,
                height=template.dimensions_height,
                num_images=num_variations,
            )

            variations: list[dict[str, Any]] = []
            for i in range(min(num_variations, len(gen_result.images))):
                variation = TemplateVariation(
                    template_id=template.id,
                    variation_config={
                        "index": i,
                        "model_used": gen_result.model_used,
                        "generation_params": gen_result.generation_params,
                    },
                )
                db_session.add(variation)
                await db_session.flush()

                variations.append(
                    {
                        "id": str(variation.id),
                        "template_id": str(variation.template_id),
                        "variation_config": variation.variation_config,
                    }
                )

            logger.info(
                "Generated %d variations for template %s",
                len(variations),
                template_id,
            )
            return variations

        except Exception:
            logger.exception(
                "Variation generation failed for template %s", template_id
            )
            raise
