"""Brand guidelines engine for BrandForge (Betano)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Default Betano brand configuration
# ------------------------------------------------------------------

BETANO_BRAND_CONFIG: dict[str, Any] = {
    "brand_name": "Betano",
    "colors": {
        "primary": "#FF6600",
        "dark_bg": "#1A1A2E",
        "white": "#FFFFFF",
        "accent_gold": "#FFD700",
    },
    "typography": {
        "headline_style": "bold",
        "body_style": "clean sans-serif",
        "recommended_fonts": ["Montserrat", "Roboto", "Open Sans"],
    },
    "imagery": {
        "style": "sports-focused",
        "mood": "energetic, dynamic",
        "subjects": ["athletes", "stadium", "action shots", "celebrations"],
    },
    "persistent_elements": [
        {
            "type": "logo",
            "description": "Betano logo",
            "placement": "top-left or bottom-right",
            "required": True,
        },
    ],
    "legal_defaults": {
        "default_text": "18+ Terms & Conditions Apply",
        "position": "bottom-center",
        "font_size": 12,
        "color": "#FFFFFF",
    },
}


# ------------------------------------------------------------------
# Market-specific brand tweaks
# ------------------------------------------------------------------

_MARKET_BRAND_RULES: dict[str, dict[str, Any]] = {
    "ON": {
        "restrictions": [
            "Do not depict real tournament trophies (e.g. World Cup Trophy, Stanley Cup).",
            "No imagery suggesting guaranteed wins.",
        ],
        "legal_overlay": {
            "text": "18+ Terms & Conditions Apply",
            "position": "bottom-center",
        },
    },
    "DE": {
        "restrictions": [
            "Avoid imagery glorifying excessive gambling.",
        ],
        "legal_overlay": {
            "text": "Gambling can be addictive. Play responsibly.",
            "position": "bottom-center",
        },
    },
    "BR": {
        "restrictions": [],
        "legal_overlay": {
            "text": "18+ Jogue com responsabilidade",
            "position": "bottom-center",
        },
    },
    "GR": {
        "restrictions": [],
        "legal_overlay": {
            "text": "\u0395\u0395\u0395\u03a0 - \u03a0\u03b1\u03af\u03be\u03b5 \u03a5\u03c0\u03b5\u03cd\u03b8\u03c5\u03bd\u03b1",
            "position": "bottom-center",
        },
    },
    "PT": {
        "restrictions": [],
        "legal_overlay": None,
    },
}


class BrandGuidelinesEngine:
    """Enriches user prompts with Betano brand identity and validates content."""

    def __init__(self, brand_config: dict[str, Any] | None = None) -> None:
        self.config = brand_config or BETANO_BRAND_CONFIG

    # ------------------------------------------------------------------
    # Prompt enhancement
    # ------------------------------------------------------------------

    def enhance_prompt(
        self,
        prompt: str,
        market_id: str | None = None,
        db_guidelines: list | None = None,
    ) -> str:
        """Enrich a raw user prompt with brand context.

        Parameters
        ----------
        prompt:
            The original user prompt.
        market_id:
            Optional ISO-style market code (e.g. ``"ON"``, ``"DE"``).
        db_guidelines:
            Optional list of guideline dicts loaded from the database.

        Returns
        -------
        str
            A prompt string enriched with color, typography, and style cues.
        """
        parts: list[str] = [prompt.strip()]

        # Colors
        colors = self.config.get("colors", {})
        color_str = ", ".join(
            f"{name}: {value}" for name, value in colors.items()
        )
        parts.append(f"Brand color palette: {color_str}.")

        # Typography
        typo = self.config.get("typography", {})
        parts.append(
            f"Typography: {typo.get('headline_style', 'bold')} headlines, "
            f"{typo.get('body_style', 'clean sans-serif')} body text."
        )

        # Imagery style
        imagery = self.config.get("imagery", {})
        parts.append(
            f"Imagery style: {imagery.get('style', 'sports-focused')}, "
            f"{imagery.get('mood', 'energetic, dynamic')}."
        )

        # Market-specific additions
        if market_id:
            market_rules = _MARKET_BRAND_RULES.get(market_id, {})
            restrictions = market_rules.get("restrictions", [])
            if restrictions:
                parts.append("Market restrictions: " + "; ".join(restrictions))

        # DB-sourced guidelines
        if db_guidelines:
            for guideline in db_guidelines:
                rules = guideline if isinstance(guideline, str) else guideline.get("rule", "")
                if rules:
                    parts.append(f"Guideline: {rules}")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Content validation
    # ------------------------------------------------------------------

    def validate_content(
        self,
        prompt: str,
        market_id: str,
        market_rules: list[dict] | None = None,
    ) -> list[str]:
        """Check a prompt against market restrictions.

        Returns a list of violation descriptions.  An empty list means the
        prompt passes validation.
        """
        violations: list[str] = []
        prompt_lower = prompt.lower()

        # Built-in market rules
        builtin = _MARKET_BRAND_RULES.get(market_id, {})
        restrictions: list[str] = builtin.get("restrictions", [])

        # Heuristic keyword matching against known restriction themes
        _KEYWORD_MAP: dict[str, list[str]] = {
            "Do not depict real tournament trophies": [
                "world cup trophy",
                "stanley cup",
                "champions league trophy",
                "ballon d'or",
            ],
            "No imagery suggesting guaranteed wins": [
                "guaranteed win",
                "sure bet",
                "100% win",
                "certain profit",
            ],
            "Avoid imagery glorifying excessive gambling": [
                "big jackpot",
                "unlimited betting",
                "all-in",
                "bet everything",
            ],
        }

        for restriction in restrictions:
            keywords = _KEYWORD_MAP.get(restriction, [])
            for kw in keywords:
                if kw in prompt_lower:
                    violations.append(
                        f"Market {market_id} restriction violated: {restriction} "
                        f"(matched keyword: {kw!r})"
                    )

        # Additional rules passed from the caller / database
        if market_rules:
            for rule in market_rules:
                forbidden: list[str] = rule.get("forbidden_keywords", [])
                for kw in forbidden:
                    if kw.lower() in prompt_lower:
                        violations.append(
                            f"Rule '{rule.get('name', 'custom')}' violated: "
                            f"forbidden keyword {kw!r} found in prompt."
                        )

        return violations

    # ------------------------------------------------------------------
    # Persistent elements
    # ------------------------------------------------------------------

    def get_persistent_elements(
        self, market_id: str | None = None
    ) -> list[dict]:
        """Return elements that must appear on every promotional material.

        Currently the Betano logo is always required.
        """
        elements = list(self.config.get("persistent_elements", []))

        # Market-specific overrides could add or modify elements here
        if market_id:
            overlay = self.get_legal_overlay(market_id)
            if overlay:
                elements.append(
                    {
                        "type": "legal_text",
                        "description": overlay["text"],
                        "placement": overlay["position"],
                        "required": True,
                    }
                )

        return elements

    # ------------------------------------------------------------------
    # Legal overlay
    # ------------------------------------------------------------------

    def get_legal_overlay(
        self,
        market_id: str,
        market_config: dict | None = None,
    ) -> dict | None:
        """Return required legal text and its positioning for a market.

        Returns ``None`` when no overlay is required.
        """
        if market_config and market_config.get("legal_overlay"):
            return market_config["legal_overlay"]

        market_rules = _MARKET_BRAND_RULES.get(market_id)
        if not market_rules:
            return None

        return market_rules.get("legal_overlay")
