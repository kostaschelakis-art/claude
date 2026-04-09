"""Celery application configuration and async tasks for BrandForge."""

from __future__ import annotations

import logging
import uuid

from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Celery app
# ------------------------------------------------------------------

celery_app = Celery(
    "brandforge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


# ------------------------------------------------------------------
# Tasks
# ------------------------------------------------------------------


@celery_app.task(bind=True, name="brandforge.generate_image", max_retries=3)
def generate_image_task(
    self,
    image_id: str,
    prompt: str,
    market_id: str,
    user_id: str,
    width: int,
    height: int,
    ai_provider: str | None = None,
    template_id: str | None = None,
    style_preferences: dict | None = None,
) -> dict:
    """Celery task that drives asynchronous image generation.

    This is a placeholder that delegates to the synchronous entrypoint of
    :class:`~app.services.image_generation.ImageGenerationService`.  In
    production the task would open its own DB session via
    ``async_session_factory`` and run the async service inside an event loop.
    """
    import asyncio

    from app.database import async_session_factory
    from app.services.image_generation import ImageGenerationService

    async def _run() -> str:
        service = ImageGenerationService()
        async with async_session_factory() as session:
            try:
                result_id = await service.generate(
                    prompt=prompt,
                    market_id=market_id,
                    user_id=user_id,
                    width=width,
                    height=height,
                    ai_provider=ai_provider,
                    template_id=template_id,
                    style_preferences=style_preferences,
                    db_session=session,
                )
                await session.commit()
                return result_id
            except Exception:
                await session.rollback()
                raise

    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        result_id = loop.run_until_complete(_run())
        logger.info("Task completed for image %s -> %s", image_id, result_id)
        return {"image_id": result_id, "status": "completed"}
    except Exception as exc:
        logger.exception("Task failed for image %s", image_id)
        raise self.retry(exc=exc, countdown=30)
