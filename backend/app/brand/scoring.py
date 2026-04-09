"""Feedback collection and aggregation for generated images."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import ImageReview

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Records and retrieves user feedback on generated images."""

    async def record_feedback(
        self,
        image_id: uuid.UUID | str,
        user_id: uuid.UUID | str,
        score: int | None,
        thumbs_up: bool | None,
        feedback_text: str | None,
        db_session: AsyncSession,
    ) -> None:
        """Persist a single piece of feedback to the database."""
        if isinstance(image_id, str):
            image_id = uuid.UUID(image_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        review = ImageReview(
            image_id=image_id,
            reviewer_id=user_id,
            score=score,
            thumbs=thumbs_up,
            feedback_text=feedback_text,
        )

        db_session.add(review)
        await db_session.flush()
        logger.info(
            "Recorded feedback for image %s by user %s (score=%s, thumbs=%s)",
            image_id,
            user_id,
            score,
            thumbs_up,
        )

    async def get_feedback_stats(
        self,
        db_session: AsyncSession,
        market_id: uuid.UUID | str | None = None,
    ) -> dict:
        """Return aggregate feedback statistics.

        Parameters
        ----------
        db_session:
            Active async database session.
        market_id:
            Optional market UUID to filter reviews by associated image market.

        Returns
        -------
        dict
            Keys: ``total_reviews``, ``average_score``, ``thumbs_up_count``,
            ``thumbs_down_count``, ``thumbs_up_rate``.
        """
        from app.models.image import GeneratedImage

        base_query = select(
            func.count(ImageReview.id).label("total"),
            func.avg(ImageReview.score).label("avg_score"),
            func.count(ImageReview.id).filter(ImageReview.thumbs.is_(True)).label("thumbs_up"),
            func.count(ImageReview.id).filter(ImageReview.thumbs.is_(False)).label("thumbs_down"),
        )

        if market_id:
            if isinstance(market_id, str):
                market_id = uuid.UUID(market_id)
            base_query = base_query.join(
                GeneratedImage, GeneratedImage.id == ImageReview.image_id
            ).where(GeneratedImage.market_id == market_id)

        result = await db_session.execute(base_query)
        row = result.one()

        total = row.total or 0
        avg_score = float(row.avg_score) if row.avg_score is not None else 0.0
        thumbs_up = row.thumbs_up or 0
        thumbs_down = row.thumbs_down or 0
        thumbs_up_rate = (thumbs_up / total * 100) if total > 0 else 0.0

        return {
            "total_reviews": total,
            "average_score": round(avg_score, 2),
            "thumbs_up_count": thumbs_up,
            "thumbs_down_count": thumbs_down,
            "thumbs_up_rate": round(thumbs_up_rate, 2),
        }
