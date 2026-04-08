"""Validation utilities for multimodal content"""

from pathlib import Path
from typing import Literal

# Image size limits (in bytes)
ANTHROPIC_IMAGE_SIZE_LIMIT = 5 * 1024 * 1024  # 5MB
OPENAI_IMAGE_SIZE_LIMIT = 20 * 1024 * 1024    # 20MB
GEMINI_IMAGE_SIZE_LIMIT = 4 * 1024 * 1024     # 4MB

# Document size limits (in bytes)
ANTHROPIC_PDF_SIZE_LIMIT = 32 * 1024 * 1024   # 32MB

# Supported formats
SUPPORTED_IMAGE_FORMATS = {"image/png", "image/jpeg", "image/gif", "image/webp"}
SUPPORTED_DOCUMENT_FORMATS = {"application/pdf"}


class ValidationError(Exception):
    """Raised when content validation fails"""
    pass


def validate_image_file(
    file_path: str | Path,
    provider: Literal["anthropic", "openai", "gemini"] = "anthropic"
) -> None:
    """Validate image file before encoding

    Args:
        file_path: Path to image file
        provider: Provider name for size limit checking

    Raises:
        ValidationError: If validation fails
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {file_path}")

    # Check file size
    file_size = path.stat().st_size

    size_limits = {
        "anthropic": ANTHROPIC_IMAGE_SIZE_LIMIT,
        "openai": OPENAI_IMAGE_SIZE_LIMIT,
        "gemini": GEMINI_IMAGE_SIZE_LIMIT,
    }

    limit = size_limits.get(provider, ANTHROPIC_IMAGE_SIZE_LIMIT)

    if file_size > limit:
        limit_mb = limit / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        raise ValidationError(
            f"Image file too large: {actual_mb:.2f}MB exceeds {provider} limit of {limit_mb:.0f}MB"
        )

    # Check format by extension (basic check)
    suffix = path.suffix.lower()
    valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

    if suffix not in valid_extensions:
        raise ValidationError(
            f"Unsupported image format: {suffix}. Supported: {', '.join(valid_extensions)}"
        )


def validate_document_file(
    file_path: str | Path,
    provider: Literal["anthropic", "openai", "gemini"] = "anthropic"
) -> None:
    """Validate document file before encoding

    Args:
        file_path: Path to document file
        provider: Provider name for size limit checking

    Raises:
        ValidationError: If validation fails
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document file not found: {file_path}")

    # Check file size (currently only Anthropic supports PDFs)
    if provider == "anthropic":
        file_size = path.stat().st_size

        if file_size > ANTHROPIC_PDF_SIZE_LIMIT:
            limit_mb = ANTHROPIC_PDF_SIZE_LIMIT / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise ValidationError(
                f"PDF file too large: {actual_mb:.2f}MB exceeds Anthropic limit of {limit_mb:.0f}MB"
            )
    else:
        raise ValidationError(f"Provider {provider} does not support PDF documents")

    # Check format
    suffix = path.suffix.lower()
    if suffix != ".pdf":
        raise ValidationError(f"Unsupported document format: {suffix}. Only PDF is supported.")


def validate_media_type(media_type: str, content_type: Literal["image", "document"]) -> None:
    """Validate media type string

    Args:
        media_type: MIME type string
        content_type: Type of content (image or document)

    Raises:
        ValidationError: If media type is not supported
    """
    if content_type == "image":
        if media_type not in SUPPORTED_IMAGE_FORMATS:
            raise ValidationError(
                f"Unsupported image media type: {media_type}. "
                f"Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}"
            )
    elif content_type == "document" and media_type not in SUPPORTED_DOCUMENT_FORMATS:
        raise ValidationError(
            f"Unsupported document media type: {media_type}. "
            f"Supported: {', '.join(SUPPORTED_DOCUMENT_FORMATS)}"
        )
