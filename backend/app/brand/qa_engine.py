"""Quality-assurance scoring engine for generated images."""

from __future__ import annotations

import io
import logging
import math
from dataclasses import dataclass, field

from PIL import Image

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------


@dataclass
class CategoryScore:
    """Score for a single QA category."""

    score: float  # 0-100
    weight: float
    details: list[str]


@dataclass
class Violation:
    """A single QA violation."""

    category: str
    severity: str  # critical, major, minor
    description: str
    recommendation: str


@dataclass
class QAScore:
    """Aggregate QA result."""

    overall_score: float
    category_scores: dict[str, CategoryScore]
    violations: list[Violation]
    suggestions: list[str]
    explanation: str


# ------------------------------------------------------------------
# Weights
# ------------------------------------------------------------------

_WEIGHTS: dict[str, float] = {
    "color": 0.20,
    "composition": 0.15,
    "logo": 0.20,
    "typography": 0.10,
    "legal": 0.25,
    "content": 0.10,
}


class QAEngine:
    """Scores a generated image against brand guidelines."""

    def score_image(
        self,
        image_data: bytes,
        brand_config: dict,
        market_id: str | None = None,
        legal_rules: list | None = None,
    ) -> QAScore:
        """Run all QA checks and return an aggregate score."""
        brand_colors: list[str] = list(
            brand_config.get("colors", {}).values()
        )

        scores: dict[str, CategoryScore] = {}
        violations: list[Violation] = []
        suggestions: list[str] = []

        # --- Color ---
        scores["color"] = self._score_colors(image_data, brand_colors)
        if scores["color"].score < 50:
            violations.append(
                Violation(
                    category="color",
                    severity="major",
                    description="Image colors deviate significantly from brand palette.",
                    recommendation="Adjust color grading to align with brand colors.",
                )
            )
            suggestions.append(
                "Consider applying a brand-color overlay or adjusting saturation."
            )

        # --- Composition ---
        scores["composition"] = self._score_composition(image_data)
        if scores["composition"].score < 40:
            violations.append(
                Violation(
                    category="composition",
                    severity="minor",
                    description="Composition appears unbalanced.",
                    recommendation="Re-frame or reposition key elements for better balance.",
                )
            )

        # --- Logo ---
        scores["logo"] = self._score_logo_presence(image_data)
        if scores["logo"].score < 30:
            violations.append(
                Violation(
                    category="logo",
                    severity="critical",
                    description="No logo detected in expected placement areas.",
                    recommendation="Add the Betano logo to the top-left or bottom-right corner.",
                )
            )

        # --- Typography (placeholder) ---
        scores["typography"] = CategoryScore(
            score=70.0,
            weight=_WEIGHTS["typography"],
            details=["Typography scoring is heuristic-only in this version."],
        )

        # --- Legal compliance ---
        scores["legal"] = self._score_legal_compliance(market_id, legal_rules)
        if scores["legal"].score < 50:
            violations.append(
                Violation(
                    category="legal",
                    severity="critical",
                    description="Required legal text may be missing.",
                    recommendation="Ensure the market-required disclaimer is present.",
                )
            )

        # --- Content (placeholder) ---
        scores["content"] = CategoryScore(
            score=75.0,
            weight=_WEIGHTS["content"],
            details=["Content appropriateness assumed acceptable (no AI analysis in this pass)."],
        )

        # --- Aggregate ---
        overall = sum(
            cs.score * _WEIGHTS.get(cat, 0)
            for cat, cs in scores.items()
        )

        explanation = self.explain_score(
            QAScore(
                overall_score=overall,
                category_scores=scores,
                violations=violations,
                suggestions=suggestions,
                explanation="",
            )
        )

        return QAScore(
            overall_score=round(overall, 2),
            category_scores=scores,
            violations=violations,
            suggestions=suggestions,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Category scorers
    # ------------------------------------------------------------------

    def _score_colors(
        self, image_data: bytes, brand_colors: list[str]
    ) -> CategoryScore:
        """Score how closely the image's dominant colors match the brand palette."""
        details: list[str] = []

        try:
            img = Image.open(io.BytesIO(image_data)).convert("RGB")
            # Quantize to extract dominant colors
            quantized = img.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
            palette = quantized.getpalette() or []

            dominant: list[tuple[int, int, int]] = []
            for i in range(min(8, len(palette) // 3)):
                dominant.append(
                    (palette[i * 3], palette[i * 3 + 1], palette[i * 3 + 2])
                )

            brand_rgb = [_hex_to_rgb(c) for c in brand_colors if c.startswith("#")]
            if not brand_rgb:
                return CategoryScore(score=50.0, weight=_WEIGHTS["color"], details=["No brand colors to compare."])

            # For each brand color, find the closest dominant color
            match_count = 0
            for bc in brand_rgb:
                min_dist = min(
                    (_color_distance(bc, dc) for dc in dominant),
                    default=999,
                )
                if min_dist < 80:  # threshold for "close enough"
                    match_count += 1
                    details.append(
                        f"Brand color #{bc[0]:02x}{bc[1]:02x}{bc[2]:02x} found (distance={min_dist:.0f})."
                    )
                else:
                    details.append(
                        f"Brand color #{bc[0]:02x}{bc[1]:02x}{bc[2]:02x} NOT matched (min distance={min_dist:.0f})."
                    )

            score = (match_count / len(brand_rgb)) * 100 if brand_rgb else 50
        except Exception:
            logger.exception("Color scoring failed")
            score = 50
            details.append("Color analysis encountered an error.")

        return CategoryScore(score=round(score, 2), weight=_WEIGHTS["color"], details=details)

    def _score_composition(self, image_data: bytes) -> CategoryScore:
        """Score composition via aspect ratio check and quadrant brightness balance."""
        details: list[str] = []

        try:
            img = Image.open(io.BytesIO(image_data)).convert("L")  # grayscale
            w, h = img.size

            # Aspect ratio sanity
            ratio = w / h
            if 0.5 <= ratio <= 2.0:
                ratio_score = 100
                details.append(f"Aspect ratio {ratio:.2f} is within acceptable range.")
            else:
                ratio_score = 50
                details.append(f"Aspect ratio {ratio:.2f} is unusual.")

            # Quadrant brightness balance
            mid_x, mid_y = w // 2, h // 2
            quadrants = [
                img.crop((0, 0, mid_x, mid_y)),
                img.crop((mid_x, 0, w, mid_y)),
                img.crop((0, mid_y, mid_x, h)),
                img.crop((mid_x, mid_y, w, h)),
            ]
            means = []
            for q in quadrants:
                pixels = list(q.getdata())
                means.append(sum(pixels) / len(pixels) if pixels else 128)

            avg_mean = sum(means) / 4
            max_dev = max(abs(m - avg_mean) for m in means)
            # Lower deviation = better balance
            balance_score = max(0, 100 - (max_dev / 2.55) * 2)
            details.append(f"Quadrant brightness deviation: {max_dev:.1f}/255.")

            score = (ratio_score + balance_score) / 2
        except Exception:
            logger.exception("Composition scoring failed")
            score = 50
            details.append("Composition analysis encountered an error.")

        return CategoryScore(score=round(score, 2), weight=_WEIGHTS["composition"], details=details)

    def _score_logo_presence(self, image_data: bytes) -> CategoryScore:
        """Heuristic check for content in typical logo placement areas.

        This is a basic brightness-variance heuristic, not actual logo detection.
        """
        details: list[str] = []

        try:
            img = Image.open(io.BytesIO(image_data)).convert("L")
            w, h = img.size

            # Check top-left and bottom-right corners (common logo spots)
            corner_size_w = max(1, w // 6)
            corner_size_h = max(1, h // 6)

            regions = {
                "top-left": img.crop((0, 0, corner_size_w, corner_size_h)),
                "bottom-right": img.crop(
                    (w - corner_size_w, h - corner_size_h, w, h)
                ),
            }

            found_in: list[str] = []
            for name, region in regions.items():
                pixels = list(region.getdata())
                if not pixels:
                    continue
                mean_val = sum(pixels) / len(pixels)
                variance = sum((p - mean_val) ** 2 for p in pixels) / len(pixels)
                # High variance may indicate a logo or graphical element
                if variance > 800:
                    found_in.append(name)

            if found_in:
                score = 80.0
                details.append(
                    f"Potential logo/graphic content detected in: {', '.join(found_in)}."
                )
            else:
                score = 20.0
                details.append(
                    "No high-variance content found in typical logo areas."
                )
        except Exception:
            logger.exception("Logo presence scoring failed")
            score = 50
            details.append("Logo detection encountered an error.")

        return CategoryScore(score=round(score, 2), weight=_WEIGHTS["logo"], details=details)

    def _score_legal_compliance(
        self,
        market_id: str | None,
        legal_rules: list | None,
    ) -> CategoryScore:
        """Score whether required legal elements are needed and presumably present.

        Without OCR, this check is policy-based: if a market requires legal
        text, the score is lowered unless the caller has indicated that legal
        overlay was applied.
        """
        details: list[str] = []

        if not market_id:
            return CategoryScore(
                score=100.0,
                weight=_WEIGHTS["legal"],
                details=["No market specified; legal check skipped."],
            )

        from app.brand.guidelines import _MARKET_BRAND_RULES

        market_rules = _MARKET_BRAND_RULES.get(market_id, {})
        overlay = market_rules.get("legal_overlay")

        if overlay is None:
            score = 100.0
            details.append(f"Market {market_id} does not require legal text.")
        elif legal_rules is not None:
            # Caller explicitly provided legal rules, assume overlay was applied
            score = 90.0
            details.append(
                f"Legal overlay expected for market {market_id}: {overlay.get('text', '')}. "
                f"Assuming applied (caller provided rules)."
            )
        else:
            score = 40.0
            details.append(
                f"Market {market_id} requires legal text: {overlay.get('text', '')}. "
                f"Cannot confirm presence without OCR."
            )

        return CategoryScore(score=round(score, 2), weight=_WEIGHTS["legal"], details=details)

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------

    @staticmethod
    def explain_score(qa_score: QAScore) -> str:
        """Generate a human-readable explanation of a QA score."""
        lines: list[str] = [
            f"Overall QA Score: {qa_score.overall_score:.1f}/100",
            "",
        ]

        for cat, cs in qa_score.category_scores.items():
            lines.append(f"  {cat.upper()} ({cs.weight * 100:.0f}% weight): {cs.score:.1f}/100")
            for detail in cs.details:
                lines.append(f"    - {detail}")

        if qa_score.violations:
            lines.append("")
            lines.append("Violations:")
            for v in qa_score.violations:
                lines.append(f"  [{v.severity.upper()}] {v.category}: {v.description}")
                lines.append(f"    Recommendation: {v.recommendation}")

        if qa_score.suggestions:
            lines.append("")
            lines.append("Suggestions:")
            for s in qa_score.suggestions:
                lines.append(f"  - {s}")

        return "\n".join(lines)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _color_distance(
    c1: tuple[int, int, int], c2: tuple[int, int, int]
) -> float:
    """Euclidean distance in RGB space."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))
