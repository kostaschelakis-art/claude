"""Inject Betano brand context into AI image-generation prompts.

The prompt builder takes a user's raw prompt (e.g. "sports promo banner
with football theme") and wraps it in a structured brand brief that
re-states the distinctive brand assets and aesthetic codes.  The idea is
that every request arrives at the AI provider fully primed with
"Playful Confidence".
"""

from __future__ import annotations

from app.seed.brand_seed import BETANO_BRAND


def _detect_surface(prompt: str) -> str:
    """Heuristically classify the prompt as 'casino' or 'sportsbook'."""
    p = prompt.lower()
    casino_terms = ("casino", "slot", "roulette", "poker", "blackjack", "jackpot", "wheel")
    for term in casino_terms:
        if term in p:
            return "casino"
    return "sportsbook"


def build_brand_prompt(
    user_prompt: str,
    width: int,
    height: int,
    style_preferences: dict | None = None,
    market_disclaimers: list[dict] | None = None,
) -> str:
    """Wrap *user_prompt* with explicit Betano brand context.

    Returns a single multi-line string that the AI provider can consume
    as-is.  The structure is deliberately instruction-heavy and bullet-
    ish — diffusion-style models respond well to enumerations of visual
    attributes.
    """
    surface = _detect_surface(user_prompt)

    if surface == "casino":
        palette = BETANO_BRAND["colours"]["primary_casino"]
        palette_desc = (
            f"dark blue {palette['blue']['hex']} backdrop, off-white "
            f"{palette['off_white']['hex']} for type, and orange "
            f"{palette['orange']['hex']} as a playful accent"
        )
        ratio = BETANO_BRAND["colours"]["ratios"]["casino"]
        imagery = BETANO_BRAND["imagery_styles"]["casino_key_art"]
    else:
        palette = BETANO_BRAND["colours"]["primary_sportsbook"]
        palette_desc = (
            f"vibrant orange {palette['orange']['hex']} and off-white "
            f"{palette['off_white']['hex']}, optionally with pink accent "
            f"{palette['pink_accent']['hex']} for restricted highlights"
        )
        ratio = BETANO_BRAND["colours"]["ratios"]["sportsbook"]
        imagery = BETANO_BRAND["imagery_styles"]["full_colour"]

    tonal = BETANO_BRAND["colours"]["tonal"]
    brand_idea = BETANO_BRAND["brand_idea"]
    attributes = ", ".join(BETANO_BRAND["attributes"])
    headline_font = BETANO_BRAND["typography"]["headline"]["family"]
    body_font = BETANO_BRAND["typography"]["body"]["family"]

    lines: list[str] = [
        "=== BETANO BRAND BRIEF ===",
        f"Brand idea: {brand_idea}. Attributes: {attributes}.",
        f"Surface: {surface.upper()}.",
        f"Colour palette: {palette_desc}.",
        f"Tonal support: tonal orange {tonal['tonal_orange']['hex']}, "
        f"tonal grey {tonal['tonal_grey']['hex']}, tonal blue {tonal['tonal_blue']['hex']}.",
        f"Colour ratio: {ratio}",
        f"Imagery style: {imagery}",
        f"Typography feel: headlines in {headline_font} (bold uppercase), "
        f"body in {body_font}.",
        "Distinctive Brand Assets to honour: the Betano wordmark, the "
        "Bolted B symbol, and angular bolt-inspired graphic shapes used "
        "as dividers, accents, and kinetic geometry.",
        "Aesthetic codes: sharp diagonal edges, dynamic composition, "
        "confident negative space, high contrast, energetic motion lines.",
        "Forbidden: generic stock-photo feel, muted pastels as the main "
        "palette, cluttered compositions, low-contrast type.",
        f"Target dimensions: {width}x{height} px.",
        "=== CREATIVE REQUEST ===",
        user_prompt.strip(),
    ]

    if style_preferences:
        mood = style_preferences.get("mood")
        if mood:
            lines.append(f"Mood: {mood}.")
        art_style = style_preferences.get("art_style")
        if art_style:
            lines.append(f"Art direction: {art_style}.")
        extra_palette = style_preferences.get("color_palette")
        if extra_palette:
            lines.append(f"Additional accent colours: {', '.join(extra_palette)}.")

    if market_disclaimers:
        required = [d for d in market_disclaimers if d.get("required")]
        if required:
            disclaimer_texts = "; ".join(d["text"] for d in required)
            lines.append(
                f"Reserve clear bottom-area space for legal disclaimer(s): {disclaimer_texts}."
            )

    lines.append(
        "Final note: if in doubt, lean INTO the brand — use the DBAs "
        "abundantly and shamelessly. Less is not more here."
    )
    return "\n".join(lines)
