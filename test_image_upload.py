"""Test script for image upload workflow."""

import asyncio
import sys
import io
from pathlib import Path

# Fix Windows console encoding for emoji support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.parsers import HealthReportParser
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_single_image():
    """Test parsing a single health report image."""
    print("=" * 80)
    print("Testing Single Image Upload: S__91693062_0.jpg")
    print("=" * 80)

    parser = HealthReportParser(
        min_completeness_threshold=0.7,
        use_llm_fallback=True,
        preprocess_images=True,
    )

    result = await parser.parse("S__91693062_0.jpg")

    print(f"\n✅ Parsing Result:")
    print(f"  - Completeness: {result['completeness']:.2%}")
    print(f"  - Source: {result['source']}")
    print(f"  - Fields extracted: {len(result['data'])}")
    print(f"\n📊 Extracted Data:")
    for key, value in result['data'].items():
        print(f"  - {key}: {value}")

    return result


async def test_batch_images():
    """Test batch parsing of multiple images."""
    print("\n" + "=" * 80)
    print("Testing Batch Image Upload: Both images")
    print("=" * 80)

    parser = HealthReportParser(
        min_completeness_threshold=0.7,
        use_llm_fallback=True,
        preprocess_images=True,
    )

    file_paths = ["S__91693062_0.jpg", "S__91693063_0.jpg"]
    batch_result = await parser.parse_batch(file_paths, merge_results=True)

    print(f"\n✅ Batch Parsing Result:")
    print(f"  - Overall Completeness: {batch_result['overall_completeness']:.2%}")
    print(f"  - Files processed: {len(batch_result['results'])}")
    print(f"  - Merged fields: {len(batch_result['merged_data'])}")

    print(f"\n📊 Merged Data:")
    for key, value in batch_result['merged_data'].items():
        print(f"  - {key}: {value}")

    return batch_result


async def main():
    """Run all tests."""
    try:
        # Test 1: Single image
        single_result = await test_single_image()

        # Test 2: Batch images
        batch_result = await test_batch_images()

        print("\n" + "=" * 80)
        print("✅ All Tests Completed Successfully!")
        print("=" * 80)

        # Summary
        print(f"\n📋 Summary:")
        print(f"  - Single image completeness: {single_result['completeness']:.2%}")
        print(f"  - Batch overall completeness: {batch_result['overall_completeness']:.2%}")
        print(f"  - OCR extraction working: {'Yes' if single_result['completeness'] > 0 else 'No'}")

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
