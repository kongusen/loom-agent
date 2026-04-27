"""Multimodal Demo - Images and PDFs with Loom Agent

Demonstrates multimodal support with content blocks:
- TextBlock: Plain text content
- ImageBlock: Images from files or URLs
- DocumentBlock: PDF documents

This demo shows the type system and validation without requiring API keys.

Run:
    python examples/multimodal_demo.py
"""

import asyncio
from pathlib import Path

from loom.types import (
    create_image_block_from_file,
    create_image_block_from_url,
    create_text_block,
)


async def demo_content_blocks():
    """Demo: Creating different types of content blocks"""
    print("=" * 60)
    print("Demo 1: Creating Content Blocks")
    print("=" * 60)

    # 1. Text block
    print("\n1. Text Block:")
    text_block = create_text_block("Hello, this is a text block")
    print(f"   Type: {text_block.type}")
    print(f"   Text: {text_block.text}")

    # 2. Image block from URL
    print("\n2. Image Block (URL):")
    image_url_block = create_image_block_from_url("https://example.com/image.jpg")
    print(f"   Type: {image_url_block.type}")
    print(f"   Source type: {image_url_block.source['type']}")
    print(f"   URL: {image_url_block.source['url']}")

    # 3. Image block from file
    print("\n3. Image Block (File):")
    test_image_path = Path("test_image.png")

    # Create a minimal PNG (1x1 red pixel)
    import base64

    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )
    test_image_path.write_bytes(png_data)
    print(f"   ✓ Created test image: {test_image_path}")

    try:
        image_file_block = create_image_block_from_file(
            test_image_path, media_type="image/png", validate=True
        )
        print(f"   Type: {image_file_block.type}")
        print(f"   Source type: {image_file_block.source['type']}")
        print(f"   Media type: {image_file_block.source['media_type']}")
        print(f"   Data length: {len(image_file_block.source['data'])} bytes (base64)")
    finally:
        if test_image_path.exists():
            test_image_path.unlink()

    print("\n✓ All content blocks created successfully!")


async def demo_validation():
    """Demo: Validation of image files"""
    print("\n" + "=" * 60)
    print("Demo 2: Image Validation")
    print("=" * 60)

    # Create a test image
    test_image_path = Path("test_image.png")
    import base64

    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )
    test_image_path.write_bytes(png_data)

    try:
        # Valid image with validation
        print("\n1. Valid image (with validation):")
        block = create_image_block_from_file(
            test_image_path, media_type="image/png", validate=True, provider="anthropic"
        )
        print(f"   ✓ Created image block: {len(block.source['data'])} bytes")

        # Without validation
        print("\n2. Without validation:")
        block = create_image_block_from_file(
            test_image_path, media_type="image/png", validate=False
        )
        print(f"   ✓ Created image block (no validation): {len(block.source['data'])} bytes")

        # Test validation error (non-existent file)
        print("\n3. Testing validation error (non-existent file):")
        try:
            block = create_image_block_from_file("nonexistent.png", validate=True)
        except FileNotFoundError:
            print("   ✓ Caught expected error: FileNotFoundError")

        # Test different provider limits
        print("\n4. Provider-specific validation:")
        for provider in ["anthropic", "openai", "gemini"]:
            block = create_image_block_from_file(test_image_path, validate=True, provider=provider)
            print(f"   ✓ {provider}: validated successfully")

    finally:
        if test_image_path.exists():
            test_image_path.unlink()

    print("\n✓ Validation tests completed!")


async def demo_multimodal_message():
    """Demo: Creating multimodal messages"""
    print("\n" + "=" * 60)
    print("Demo 3: Multimodal Messages")
    print("=" * 60)

    # Create test image
    test_image_path = Path("test_image.png")
    import base64

    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )
    test_image_path.write_bytes(png_data)

    try:
        # 1. Text only message (backward compatible)
        print("\n1. Text-only message (backward compatible):")
        text_message = "What is 2+2?"
        print(f"   Content: {text_message}")
        print("   Type: str")

        # 2. Text block message
        print("\n2. Text block message:")
        text_blocks = [create_text_block("What is 3+3?")]
        print("   Content: list[ContentBlock]")
        print(f"   Blocks: {len(text_blocks)}")
        print(f"   Block 0: {text_blocks[0].type} - {text_blocks[0].text}")

        # 3. Text + Image message
        print("\n3. Text + Image message:")
        multimodal_content = [
            create_text_block("What color is this image?"),
            create_image_block_from_file(test_image_path, media_type="image/png"),
        ]
        print("   Content: list[ContentBlock]")
        print(f"   Blocks: {len(multimodal_content)}")
        print(f"   Block 0: {multimodal_content[0].type}")
        print(f"   Block 1: {multimodal_content[1].type}")

        # 4. Multiple images
        print("\n4. Multiple images message:")
        multi_image_content = [
            create_text_block("Compare these images"),
            create_image_block_from_file(test_image_path, media_type="image/png"),
            create_image_block_from_url("https://example.com/image2.jpg"),
        ]
        print("   Content: list[ContentBlock]")
        print(f"   Blocks: {len(multi_image_content)}")
        print(f"   Block 0: {multi_image_content[0].type}")
        print(f"   Block 1: {multi_image_content[1].type} (from file)")
        print(f"   Block 2: {multi_image_content[2].type} (from URL)")

        print("\n✓ All message types created successfully!")

    finally:
        if test_image_path.exists():
            test_image_path.unlink()


async def demo_provider_formats():
    """Demo: How content blocks are converted for different providers"""
    print("\n" + "=" * 60)
    print("Demo 4: Provider Format Conversion")
    print("=" * 60)

    from loom.providers.anthropic import AnthropicProvider
    from loom.providers.gemini import GeminiProvider
    from loom.providers.openai import OpenAIProvider

    # Create test content
    test_image_path = Path("test_image.png")
    import base64

    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )
    test_image_path.write_bytes(png_data)

    try:
        content_blocks = [
            create_text_block("What's in this image?"),
            create_image_block_from_file(test_image_path, media_type="image/png"),
        ]

        # Convert to dict format (as used internally)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": content_blocks[1].source["data"],
                        },
                    },
                ],
            }
        ]

        # 1. Anthropic format
        print("\n1. Anthropic Provider:")
        provider = AnthropicProvider(api_key="dummy")
        _, converted = provider._convert_messages(messages)
        print(f"   Messages: {len(converted)}")
        print(f"   Content blocks: {len(converted[0]['content'])}")
        print(f"   Block 0 type: {converted[0]['content'][0]['type']}")
        print(f"   Block 1 type: {converted[0]['content'][1]['type']}")

        # 2. OpenAI format
        print("\n2. OpenAI Provider:")
        provider = OpenAIProvider(api_key="dummy")
        converted = provider._convert_messages(messages)
        print(f"   Messages: {len(converted)}")
        print(f"   Content parts: {len(converted[0]['content'])}")
        print(f"   Part 0 type: {converted[0]['content'][0]['type']}")
        print(f"   Part 1 type: {converted[0]['content'][1]['type']}")

        # 3. Gemini format
        print("\n3. Gemini Provider:")
        provider = GeminiProvider(api_key="dummy")
        converted = provider._convert_messages(messages)
        print(f"   Messages: {len(converted)}")
        print(f"   Parts: {len(converted[0]['parts'])}")
        print(f"   Part 0 has 'text': {'text' in converted[0]['parts'][0]}")
        print(f"   Part 1 has 'inline_data': {'inline_data' in converted[0]['parts'][1]}")

        print("\n✓ All providers convert content blocks correctly!")

    finally:
        if test_image_path.exists():
            test_image_path.unlink()


async def main():
    """Run all demos"""
    print("\n🎨 Loom Multimodal Support Demo\n")

    # Run demos
    await demo_content_blocks()
    await demo_validation()
    await demo_multimodal_message()
    await demo_provider_formats()

    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print("✅ ContentBlock types: TextBlock, ImageBlock, DocumentBlock")
    print("✅ Helper functions: create_*_block_from_file/url")
    print("✅ Validation: File size, format, provider-specific limits")
    print("✅ Provider support: Anthropic, OpenAI, Gemini")
    print("✅ Backward compatible: String content still works")
    print("\n✅ All demos completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
