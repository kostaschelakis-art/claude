"""Abstract AI provider interface and factory for BrandForge."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GenerationResult:
    """Result of an AI image generation call."""

    images: list[bytes]
    layers: list[dict]
    model_used: str
    generation_params: dict
    cost_cents: int


class AIProvider(ABC):
    """Base class that every AI image provider must implement."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        num_images: int = 1,
        style: dict | None = None,
    ) -> GenerationResult:
        """Generate images from a text prompt."""
        ...

    @abstractmethod
    async def generate_layers(
        self,
        prompt: str,
        width: int,
        height: int,
        layer_descriptions: list[str],
    ) -> GenerationResult:
        """Generate separate image layers from individual descriptions."""
        ...

    @abstractmethod
    async def analyze_image(self, image_data: bytes) -> dict:
        """Analyze an image and return structured layout/color/typography info."""
        ...

    @abstractmethod
    async def generate_variations(
        self,
        image_data: bytes,
        prompt: str,
        num_variations: int = 3,
    ) -> GenerationResult:
        """Generate visual variations of a reference image."""
        ...


def get_provider(provider_name: str) -> AIProvider:
    """Factory that returns a concrete AIProvider instance by name.

    Supported names: ``"google"``, ``"openai"``, ``"stability"``.
    """
    from app.ai.google_imagen import GoogleImagenProvider
    from app.ai.openai_dalle import OpenAIDalleProvider
    from app.ai.stability_ai import StabilityAIProvider

    providers: dict[str, type[AIProvider]] = {
        "google": GoogleImagenProvider,
        "openai": OpenAIDalleProvider,
        "stability": StabilityAIProvider,
    }

    cls = providers.get(provider_name)
    if not cls:
        raise ValueError(
            f"Unknown provider: {provider_name!r}. "
            f"Available: {', '.join(providers)}"
        )
    return cls()
