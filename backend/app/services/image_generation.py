"""High-level image generation orchestration service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import GenerationResult, get_provider
from app.brand.guidelines import BETANO_BRAND_CONFIG, BrandGuidelinesEngine
from app.brand.qa_engine import QAEngine
from app.config import settings
from app.models.image import GeneratedImage, ImageLayer, ImageStatus, LayerType

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """Orchestrates the full image generation pipeline.

    1. Enhance prompt with brand guidelines.
    2. Validate prompt against market rules.
    3. Generate image(s) via AI provider.
    4. Run QA scoring.
    5. Persist results to the database.
    """

    def __init__(self) -> None:
        self._brand_engine = BrandGuidelinesEngine()
        self._qa_engine = QAEngine()

    async def generate(
        self,
        prompt: str,
        market_id: str,
        user_id: str,
        width: int,
        height: int,
        ai_provider: str | None = None,
        template_id: str | None = None,
        style_preferences: dict | None = None,
        db_session: AsyncSession | None = None,
    ) -> str:
        """Run the full generation flow and return the image ID.

        Parameters
        ----------
        prompt:
            Raw user prompt.
        market_id:
            UUID (as string) of the target market.
        user_id:
            UUID (as string) of the requesting user.
        width, height:
            Desired output dimensions.
        ai_provider:
            Provider name override (``"google"``, ``"openai"``, ``"stability"``).
            Falls back to ``settings.default_ai_provider``.
        template_id:
            Optional template UUID to associate with the generation.
        style_preferences:
            Optional dict of style hints forwarded to the AI provider.
        db_session:
            Optional async database session.  When provided the image record
            is persisted; otherwise the generation runs in-memory only.

        Returns
        -------
        str
            The UUID of the newly created ``GeneratedImage`` record.
        """
        image_id = uuid.uuid4()
        provider_name = ai_provider or settings.default_ai_provider

        # -- 1. Create initial DB record (pending) --
        if db_session:
            image_record = GeneratedImage(
                id=image_id,
                prompt=prompt,
                user_id=uuid.UUID(user_id),
                market_id=uuid.UUID(market_id),
                template_id=uuid.UUID(template_id) if template_id else None,
                ai_provider=provider_name,
                status=ImageStatus.PENDING,
                width=width,
                height=height,
                generation_params=style_preferences,
            )
            db_session.add(image_record)
            await db_session.flush()

        try:
            # -- 2. Enhance prompt --
            enhanced_prompt = self._brand_engine.enhance_prompt(
                prompt, market_id=None  # market_id here is a UUID, not a code
            )

            # -- 3. Validate --
            violations = self._brand_engine.validate_content(
                enhanced_prompt, market_id=""
            )
            if violations:
                logger.warning(
                    "Content violations detected for image %s: %s",
                    image_id,
                    violations,
                )

            # -- 4. Update status to GENERATING --
            if db_session:
                image_record.status = ImageStatus.GENERATING
                image_record.refined_prompt = enhanced_prompt
                await db_session.flush()

            # -- 5. Generate via AI provider --
            provider = get_provider(provider_name)
            result: GenerationResult = await provider.generate(
                prompt=enhanced_prompt,
                width=width,
                height=height,
                num_images=1,
                style=style_preferences,
            )

            # -- 6. Persist layers --
            if db_session and result.layers:
                for idx, layer_meta in enumerate(result.layers):
                    layer = ImageLayer(
                        image_id=image_id,
                        layer_index=idx,
                        layer_type=LayerType(layer_meta.get("layer_type", "background")),
                        properties=layer_meta,
                    )
                    db_session.add(layer)

            # -- 7. QA scoring --
            if result.images:
                qa_score = self._qa_engine.score_image(
                    image_data=result.images[0],
                    brand_config=BETANO_BRAND_CONFIG,
                )
                logger.info(
                    "QA score for image %s: %.1f",
                    image_id,
                    qa_score.overall_score,
                )

            # -- 8. Mark completed --
            if db_session:
                image_record.status = ImageStatus.COMPLETED
                image_record.ai_model = result.model_used
                image_record.generation_params = result.generation_params
                if result.images:
                    image_record.file_size_bytes = len(result.images[0])
                await db_session.flush()

        except Exception:
            logger.exception("Image generation failed for %s", image_id)
            if db_session:
                image_record.status = ImageStatus.FAILED
                await db_session.flush()
            raise

        return str(image_id)

    async def get_generation_status(
        self,
        image_id: str,
        db_session: AsyncSession,
    ) -> dict:
        """Return the current status of a generation request.

        Returns
        -------
        dict
            Keys: ``id``, ``status``, ``prompt``, ``refined_prompt``,
            ``ai_provider``, ``width``, ``height``, ``composite_url``,
            ``created_at``.
        """
        stmt = select(GeneratedImage).where(
            GeneratedImage.id == uuid.UUID(image_id)
        )
        result = await db_session.execute(stmt)
        image = result.scalar_one_or_none()

        if not image:
            return {"id": image_id, "status": "not_found"}

        return {
            "id": str(image.id),
            "status": image.status.value,
            "prompt": image.prompt,
            "refined_prompt": image.refined_prompt,
            "ai_provider": image.ai_provider,
            "ai_model": image.ai_model,
            "width": image.width,
            "height": image.height,
            "composite_url": image.composite_url,
            "created_at": image.created_at.isoformat() if image.created_at else None,
        }
