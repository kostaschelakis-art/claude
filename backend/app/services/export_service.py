"""Image export and format conversion service."""

from __future__ import annotations

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)


class ExportService:
    """Handles image resizing and format conversion for export."""

    async def export_image(
        self,
        image_data: bytes,
        format: str,
        width: int,
        height: int,
        quality: int = 95,
    ) -> bytes:
        """Resize and convert an image to the requested format.

        Parameters
        ----------
        image_data:
            Source image as raw bytes.
        format:
            Target format: ``"png"``, ``"jpg"``, ``"webp"``, or ``"pdf"``.
        width, height:
            Desired output dimensions.
        quality:
            Compression quality (1-100), used for JPEG and WebP.

        Returns
        -------
        bytes
            The exported image in the requested format.
        """
        img = Image.open(io.BytesIO(image_data))

        # Resize
        if (width, height) != img.size:
            img = img.resize((width, height), Image.LANCZOS)

        buf = io.BytesIO()
        fmt = format.lower()

        if fmt == "png":
            img = img.convert("RGBA")
            img.save(buf, format="PNG", optimize=True)

        elif fmt in ("jpg", "jpeg"):
            # JPEG does not support alpha
            img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=quality, optimize=True)

        elif fmt == "webp":
            img.save(buf, format="WEBP", quality=quality)

        elif fmt == "pdf":
            img = img.convert("RGB")
            img.save(buf, format="PDF", resolution=150.0)

        else:
            raise ValueError(f"Unsupported export format: {format!r}")

        result = buf.getvalue()
        logger.info(
            "Exported image as %s (%dx%d, %d bytes)",
            fmt,
            width,
            height,
            len(result),
        )
        return result
