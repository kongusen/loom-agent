"""Content block types for multimodal support

Supports text, images, and documents (PDFs) in messages.
Compatible with Anthropic, OpenAI, and Gemini providers.
"""

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class TextBlock:
    """Text content block"""
    type: Literal["text"] = "text"
    text: str = ""


@dataclass
class ImageBlock:
    """Image content block

    Supports both base64-encoded images and URLs.

    Example base64 source:
        {"type": "base64", "media_type": "image/png", "data": "iVBORw0KG..."}

    Example URL source:
        {"type": "url", "url": "https://example.com/image.jpg"}
    """
    type: Literal["image"] = "image"
    source: dict[str, str] = field(default_factory=dict)


@dataclass
class DocumentBlock:
    """Document content block (PDF)

    Example source:
        {"type": "base64", "media_type": "application/pdf", "data": "JVBERi0x..."}
    """
    type: Literal["document"] = "document"
    source: dict[str, str] = field(default_factory=dict)


ContentBlock = TextBlock | ImageBlock | DocumentBlock
MessageContent = str | list[ContentBlock]


# Helper functions

def create_text_block(text: str) -> TextBlock:
    """Create a text content block

    Args:
        text: Text content

    Returns:
        TextBlock instance
    """
    return TextBlock(type="text", text=text)


def create_image_block_from_file(
    file_path: str | Path,
    media_type: Literal["image/png", "image/jpeg", "image/gif", "image/webp"] = "image/png",
    validate: bool = True,
    provider: Literal["anthropic", "openai", "gemini"] = "anthropic"
) -> ImageBlock:
    """Create an image content block from a file

    Args:
        file_path: Path to image file
        media_type: MIME type of the image
        validate: Whether to validate file size and format (default: True)
        provider: Provider name for validation limits (default: "anthropic")

    Returns:
        ImageBlock instance with base64-encoded data

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
        ValidationError: If validation fails
    """
    path = Path(file_path)

    # Validate if requested
    if validate:
        from .validation import validate_image_file, validate_media_type
        validate_image_file(path, provider=provider)
        validate_media_type(media_type, content_type="image")

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    return ImageBlock(
        type="image",
        source={
            "type": "base64",
            "media_type": media_type,
            "data": data
        }
    )


def create_image_block_from_url(url: str) -> ImageBlock:
    """Create an image content block from a URL

    Args:
        url: URL to the image

    Returns:
        ImageBlock instance with URL source
    """
    return ImageBlock(
        type="image",
        source={
            "type": "url",
            "url": url
        }
    )


def create_document_block_from_file(
    file_path: str | Path,
    media_type: Literal["application/pdf"] = "application/pdf",
    validate: bool = True,
    provider: Literal["anthropic", "openai", "gemini"] = "anthropic"
) -> DocumentBlock:
    """Create a document content block from a file

    Args:
        file_path: Path to PDF file
        media_type: MIME type of the document
        validate: Whether to validate file size and format (default: True)
        provider: Provider name for validation limits (default: "anthropic")

    Returns:
        DocumentBlock instance with base64-encoded data

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
        ValidationError: If validation fails
    """
    path = Path(file_path)

    # Validate if requested
    if validate:
        from .validation import validate_document_file, validate_media_type
        validate_document_file(path, provider=provider)
        validate_media_type(media_type, content_type="document")

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    return DocumentBlock(
        type="document",
        source={
            "type": "base64",
            "media_type": media_type,
            "data": data
        }
    )
