"""Seed data for the Betano brand system.

Centralises the distinctive brand assets (DBAs), colour palettes,
typography rules, and imagery guidance so that every AI generation can
consistently encode the idea of "Playful Confidence".

This data is applied in two places:
    1. Persisted into the ``brand_guidelines`` table on startup so that
       admins can browse it via the UI.
    2. Used directly by :mod:`app.brand.prompt_builder` to enrich every
       AI generation prompt.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BrandGuideline,
    BrandGuidelineCategory,
    BrandGuidelineScope,
    Market,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Betano brand definition (the source of truth used across the app)
# --------------------------------------------------------------------------- #

BETANO_BRAND: dict[str, Any] = {
    "brand_idea": "Playful Confidence",
    "attributes": [
        "Confidence",
        "Optimism",
        "Playfulness",
        "For all the players",
        "Artistic Flair",
    ],
    "voice": (
        "Bold, confident, optimistic and playful. Speaks to sports fans "
        "and casino players alike with energy and warmth."
    ),
    # ------------------------------------------------------------------ #
    # Colours
    # ------------------------------------------------------------------ #
    "colours": {
        "primary_sportsbook": {
            "orange": {"hex": "#FF3C00", "rgb": [255, 60, 0]},
            "off_white": {"hex": "#FAF5F0", "rgb": [250, 245, 240]},
            "pink_accent": {"hex": "#FF0078", "rgb": [255, 0, 120]},
        },
        "primary_casino": {
            "blue": {"hex": "#0F0F23", "rgb": [15, 15, 35]},
            "off_white": {"hex": "#FAF5F0", "rgb": [250, 245, 240]},
            "orange": {"hex": "#FF3C00", "rgb": [255, 60, 0]},
        },
        "tonal": {
            "tonal_orange": {"hex": "#FF5019", "rgb": [255, 80, 25]},
            "tonal_grey": {"hex": "#F0F0F0", "rgb": [240, 240, 240]},
            "tonal_blue": {"hex": "#191932", "rgb": [25, 25, 50]},
        },
        "betano_gradient": {
            "from": {"name": "pink", "hex": "#FF0078", "stop_pct": 30},
            "to": {"name": "orange", "hex": "#FF3C00", "stop_pct": 70},
            "notes": (
                "Gradient is used sparingly — only on typography "
                "(both modes) and bolt graphics (Casino only). "
                "Pink occupies 30% (top / left), orange 70% (bottom / right)."
            ),
        },
        "secondary_palette": [
            {"name": "Teal", "hex": "#00DCB4"},
            {"name": "Cyan", "hex": "#00B4E1"},
            {"name": "Light Blue", "hex": "#0A41D7"},
            {"name": "Purple", "hex": "#8214E6"},
            {"name": "Light Teal", "hex": "#6EF5D7"},
            {"name": "Light Cyan", "hex": "#41D2FF"},
            {"name": "Lighter Blue", "hex": "#649BEB"},
            {"name": "Light Purple", "hex": "#B973F0"},
            {"name": "Pastel Blue", "hex": "#BEF0EB"},
            {"name": "Pastel Lilac", "hex": "#E6E1F5"},
            {"name": "Pink", "hex": "#FF69B4"},
            {"name": "Red", "hex": "#F51E1E"},
            {"name": "Orange (secondary)", "hex": "#FF7800"},
            {"name": "Yellow", "hex": "#FFB900"},
            {"name": "Light Pink", "hex": "#FFA5D7"},
            {"name": "Light Red", "hex": "#FA7D7D"},
            {"name": "Light Orange", "hex": "#FFAA50"},
            {"name": "Light Yellow", "hex": "#FFE169"},
            {"name": "Pastel Pink", "hex": "#FFD2EB"},
            {"name": "Pastel Orange", "hex": "#FAE6D2"},
            {"name": "Lime", "hex": "#82C328"},
            {"name": "Green", "hex": "#0F910F"},
            {"name": "Brown", "hex": "#A5644B"},
            {"name": "Grey", "hex": "#646469"},
            {"name": "Light Lime", "hex": "#AFDC7D"},
            {"name": "Light Green", "hex": "#5FBE69"},
            {"name": "Light Brown", "hex": "#D7AFA0"},
            {"name": "Light Grey", "hex": "#D7D7DC"},
            {"name": "Pastel Green", "hex": "#E6FFE6"},
            {"name": "Off Grey", "hex": "#EBEBEB"},
        ],
        "ratios": {
            "sportsbook": (
                "Orange and off-white dominate; orange accents carry focus. "
                "Pink only as a restricted accent."
            ),
            "casino": (
                "Blue backdrop is dominant; off-white for copy; orange used "
                "as a playful accent; the Betano gradient appears only on "
                "typography and bolt graphics."
            ),
        },
    },
    # ------------------------------------------------------------------ #
    # Typography
    # ------------------------------------------------------------------ #
    "typography": {
        "headline": {
            "family": "Betano Nichrome Dark",
            "usage": "Primary headlines, uppercase. Bold, confident statements.",
            "tracking": "0-20",
            "leading_pct": "80-85",
        },
        "headline_sportsbook_accent": {
            "family": "Betano Nichrome Bold / Bold Oblique",
            "usage": "Sportsbook only — moments of impact, athletic energy.",
        },
        "subheadline": {
            "family": "Betano Nichrome Dark",
            "usage": "Sentence case supporting copy. Leading 100%.",
        },
        "body": {
            "family": "Haffer Regular",
            "usage": "Body copy. Leading 110-130%. Sentence case.",
        },
        "annotation": {
            "family": "Haffer Medium",
            "usage": "Small details, uppercase. Tracking 60%.",
        },
        "cta": {
            "family": "Haffer Semibold",
            "usage": "Buttons and CTAs. Title case. Tracking 10.",
        },
    },
    # ------------------------------------------------------------------ #
    # Distinctive Brand Assets (DBAs)
    # ------------------------------------------------------------------ #
    "distinctive_assets": {
        "wordmark": (
            "Betano wordmark — white text on solid orange background is the "
            "primary application. Never distort, recolour, or crowd it."
        ),
        "bolted_b": (
            "The 'Bolted B' symbol — a stylised capital B pierced by a bolt. "
            "Used when the full wordmark cannot fit (sleeve patch, app icon)."
        ),
        "bolt_fluent_device": (
            "The bolt acts as a fluent device — it shows up as dividers, "
            "directional accents, and angular graphic shapes."
        ),
        "angular_shapes": (
            "Angular graphic shapes motivated by the bolt — sharp cuts, "
            "diagonal edges, and kinetic geometry support the brand energy."
        ),
    },
    # ------------------------------------------------------------------ #
    # Imagery
    # ------------------------------------------------------------------ #
    "imagery_styles": {
        "full_colour": (
            "Authentic, natural sporting imagery — action on the pitch, "
            "portraits of players and managers. Can be full-bleed or cut out."
        ),
        "spotlight": (
            "Single subject against a clean uncluttered background. "
            "Epic, immersive, dramatic focal point."
        ),
        "monotone": (
            "Blue monotone treatment for bold, graphic sportsbook feel. "
            "Can be full-bleed or cut out on a blue background."
        ),
        "casino_key_art": (
            "Bright, colourful character key art bringing the energy and "
            "excitement of casino games into brand communications."
        ),
    },
    "illustration_principles": [
        "Blue base with gradient as a 'pop' colour.",
        "Limit each illustration to one or two secondary-palette colours.",
        "Strokes between shapes cut out to reveal the background.",
        "Embrace 'Playful Confidence' — energy and character always.",
    ],
    "motion": (
        "Electric Elasticity — every movement in the system should feel "
        "snappy, bouncy, and deliberate."
    ),
    "usage_rule": (
        "In case of doubt, use the DBAs plenty. Consistently, abundantly "
        "and shamelessly. Less is not more here."
    ),
}


# --------------------------------------------------------------------------- #
# Seed markets
# --------------------------------------------------------------------------- #

_DEFAULT_MARKETS: list[dict[str, Any]] = [
    {
        "code": "GLOBAL",
        "name": "Global",
        "display_name": "Global (Betano HQ)",
        "data_region": "eu-west-1",
        "legal_disclaimers": [
            {"text": "18+ | Play Responsibly", "position": "bottom", "required": True}
        ],
    },
    {
        "code": "ON",
        "name": "Ontario",
        "display_name": "Ontario, Canada",
        "data_region": "ca-central-1",
        "legal_disclaimers": [
            {"text": "19+ T&C Apply. ConnexOntario 1-866-531-2600", "position": "bottom", "required": True}
        ],
        "restricted_content_rules": [
            {"rule": "no_world_cup_trophy", "description": "Cannot depict the real FIFA World Cup Trophy."},
            {"rule": "no_active_athletes_non_casino", "description": "Cannot show active athletes in non-casino promos."},
        ],
    },
    {
        "code": "BR",
        "name": "Brazil",
        "display_name": "Brazil",
        "data_region": "sa-east-1",
        "legal_disclaimers": [
            {"text": "Jogue com responsabilidade. Proibido para menores de 18 anos.", "position": "bottom", "required": True}
        ],
    },
]


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #


async def seed_markets(session: AsyncSession) -> Market:
    """Seed default markets if none exist. Returns the Global market."""
    result = await session.execute(select(Market).where(Market.code == "GLOBAL"))
    global_market = result.scalar_one_or_none()

    if global_market is None:
        for spec in _DEFAULT_MARKETS:
            market = Market(
                id=uuid.uuid4(),
                code=spec["code"],
                name=spec["name"],
                display_name=spec["display_name"],
                data_region=spec.get("data_region"),
                legal_disclaimers=spec.get("legal_disclaimers", []),
                restricted_content_rules=spec.get("restricted_content_rules", []),
                is_active=True,
            )
            session.add(market)
            if spec["code"] == "GLOBAL":
                global_market = market
        await session.flush()
        logger.info("Seeded %d markets", len(_DEFAULT_MARKETS))

    return global_market  # type: ignore[return-value]


async def seed_brand_guidelines(session: AsyncSession) -> None:
    """Seed Betano brand guidelines if none exist."""
    result = await session.execute(
        select(BrandGuideline).where(BrandGuideline.scope == BrandGuidelineScope.GLOBAL)
    )
    existing = result.scalars().first()
    if existing is not None:
        return

    guidelines: list[dict[str, Any]] = [
        {
            "name": "Betano Primary Colour Palette",
            "category": BrandGuidelineCategory.COLOR,
            "priority": 100,
            "rules": {
                "sportsbook": BETANO_BRAND["colours"]["primary_sportsbook"],
                "casino": BETANO_BRAND["colours"]["primary_casino"],
                "tonal": BETANO_BRAND["colours"]["tonal"],
                "gradient": BETANO_BRAND["colours"]["betano_gradient"],
                "ratios": BETANO_BRAND["colours"]["ratios"],
            },
        },
        {
            "name": "Betano Secondary Colour Palette",
            "category": BrandGuidelineCategory.COLOR,
            "priority": 50,
            "rules": {
                "palette": BETANO_BRAND["colours"]["secondary_palette"],
                "usage": (
                    "Supports the core colours. Never compete with the primary "
                    "palette — use to add range in illustrations and special apps."
                ),
            },
        },
        {
            "name": "Betano Typography System",
            "category": BrandGuidelineCategory.TYPOGRAPHY,
            "priority": 90,
            "rules": BETANO_BRAND["typography"],
        },
        {
            "name": "Betano Logo & Wordmark",
            "category": BrandGuidelineCategory.LOGO,
            "priority": 100,
            "rules": {
                "primary": "White wordmark on solid orange background.",
                "secondary": "Reverse (orange on off-white) — use sparingly.",
                "bolted_b": "Stacked 'Bolted B' symbol — app icons, patches.",
                "clear_space": "Always enough space to breathe. Never crowd the logo.",
                "minimum_size": "Never reduce below legible size.",
                "backgrounds": {
                    "orange": "Off-white wordmark.",
                    "off_white": "Orange wordmark (avoid where possible).",
                    "blue": "Alternative off-white or orange version.",
                },
            },
        },
        {
            "name": "Betano Distinctive Brand Assets",
            "category": BrandGuidelineCategory.GRAPHICS,
            "priority": 95,
            "rules": {
                "assets": BETANO_BRAND["distinctive_assets"],
                "usage_rule": BETANO_BRAND["usage_rule"],
            },
        },
        {
            "name": "Betano Imagery Styles",
            "category": BrandGuidelineCategory.IMAGERY,
            "priority": 80,
            "rules": {
                "styles": BETANO_BRAND["imagery_styles"],
                "default": "full_colour",
            },
        },
        {
            "name": "Betano Illustration Principles",
            "category": BrandGuidelineCategory.ILLUSTRATION,
            "priority": 70,
            "rules": {
                "principles": BETANO_BRAND["illustration_principles"],
            },
        },
        {
            "name": "Motion: Electric Elasticity",
            "category": BrandGuidelineCategory.MOTION,
            "priority": 40,
            "rules": {"description": BETANO_BRAND["motion"]},
        },
        {
            "name": "Brand Idea: Playful Confidence",
            "category": BrandGuidelineCategory.POSITIONING,
            "priority": 100,
            "rules": {
                "idea": BETANO_BRAND["brand_idea"],
                "attributes": BETANO_BRAND["attributes"],
                "voice": BETANO_BRAND["voice"],
            },
        },
    ]

    for spec in guidelines:
        g = BrandGuideline(
            id=uuid.uuid4(),
            name=spec["name"],
            category=spec["category"],
            scope=BrandGuidelineScope.GLOBAL,
            market_id=None,
            rules=spec["rules"],
            examples=[],
            priority=spec["priority"],
            is_active=True,
        )
        session.add(g)

    await session.flush()
    logger.info("Seeded %d Betano brand guidelines", len(guidelines))
