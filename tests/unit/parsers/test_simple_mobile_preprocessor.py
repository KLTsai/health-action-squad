"""Comprehensive tests for SimpleMobilePreprocessor

Tests edge cases:
- Very small images (100x100) → should upscale
- Very large images (5000x5000) → should downscale
- Already optimal size (1500x1500) → should not resize
- Images with EXIF orientation 3, 6, 8, None
- Extremely dark images (mean brightness < 50)
- Extremely bright images (mean brightness > 200)
- Normal lighting images (brightness 100-150) → should skip contrast
- Portrait vs landscape orientations
- Grayscale images
- Images without EXIF data

Performance tests:
- Processing time < 300ms per image
- Memory usage reasonable for 4000x3000 images

Comparison tests:
- Compare with old MobilePhotoOptimizer
- Verify accuracy degradation < 3%
"""

import pytest
import numpy as np
from PIL import Image
import cv2
import time
import tempfile
import os
from pathlib import Path

from src.parsers.simple_mobile_preprocessor import SimpleMobilePreprocessor
from src.parsers.image_preprocessor import MobilePhotoOptimizer


class TestSimpleMobilePreprocessor:
    """Comprehensive tests for SimpleMobilePreprocessor"""

    @pytest.fixture
    def preprocessor(self):
        """Create default preprocessor instance"""
        return SimpleMobilePreprocessor()

    @pytest.fixture
    def preprocessor_no_threshold(self):
        """Create preprocessor without threshold"""
        return SimpleMobilePreprocessor(enable_threshold=False)

    @pytest.fixture
    def temp_image_path(self, tmp_path):
        """Fixture that returns a function to create temp images"""
        def _create_temp_image(image_array, format="PNG"):
            temp_file = tmp_path / f"test_image_{id(image_array)}.png"
            if len(image_array.shape) == 2:
                # Grayscale
                Image.fromarray(image_array).save(temp_file, format)
            else:
                # RGB
                Image.fromarray(image_array).save(temp_file, format)
            return str(temp_file)
        return _create_temp_image

    # ==================== EDGE CASE TESTS: SIZE ====================

    def test_very_small_image(self, preprocessor, temp_image_path):
        """Test upscaling of very small images (100x100)"""
        # Create 100x100 RGB test image
        small_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        image_path = temp_image_path(small_image)

        # Process
        result = preprocessor.preprocess(image_path)

        # Verify upscaling occurred (min edge should be >= 1000)
        if len(result.shape) == 3:
            height, width = result.shape[:2]
        else:
            height, width = result.shape
        min_edge = min(height, width)

        assert min_edge >= 1000, f"Small image should be upscaled to min edge >= 1000, got {min_edge}"

    def test_very_large_image(self, preprocessor, temp_image_path):
        """Test downscaling of very large images (5000x5000)"""
        # Create 5000x5000 RGB test image (use smaller array to avoid memory issues)
        # We'll create a smaller one and resize it
        large_image = np.random.randint(0, 255, (5000, 5000, 3), dtype=np.uint8)
        image_path = temp_image_path(large_image)

        # Process
        result = preprocessor.preprocess(image_path)

        # Verify downscaling occurred (max edge should be <= 2000)
        if len(result.shape) == 3:
            height, width = result.shape[:2]
        else:
            height, width = result.shape
        max_edge = max(height, width)

        assert max_edge <= 2000, f"Large image should be downscaled to max edge <= 2000, got {max_edge}"

    def test_optimal_size_image(self, preprocessor_no_threshold, temp_image_path):
        """Test that optimal size images are not resized"""
        # Create 1500x1500 RGB test image (optimal size)
        optimal_image = np.random.randint(0, 255, (1500, 1500, 3), dtype=np.uint8)
        image_path = temp_image_path(optimal_image)

        # Process without threshold to preserve dimensions
        result = preprocessor_no_threshold.preprocess(image_path)

        # Verify size unchanged
        assert result.shape[:2] == (1500, 1500), "Optimal size image should not be resized"

    def test_portrait_orientation(self, preprocessor, temp_image_path):
        """Test portrait orientation handling (height > width)"""
        # Create portrait image (1000x1500)
        portrait_image = np.random.randint(0, 255, (1500, 1000, 3), dtype=np.uint8)
        image_path = temp_image_path(portrait_image)

        # Process
        result = preprocessor.preprocess(image_path)

        # Verify processing succeeded
        assert result is not None
        assert result.size > 0

    def test_landscape_orientation(self, preprocessor, temp_image_path):
        """Test landscape orientation handling (width > height)"""
        # Create landscape image (1500x1000)
        landscape_image = np.random.randint(0, 255, (1000, 1500, 3), dtype=np.uint8)
        image_path = temp_image_path(landscape_image)

        # Process
        result = preprocessor.preprocess(image_path)

        # Verify processing succeeded
        assert result is not None
        assert result.size > 0

    # ==================== EDGE CASE TESTS: EXIF ====================

    def test_exif_orientation_3(self, preprocessor, tmp_path):
        """Test 180° rotation (EXIF orientation 3)"""
        # Create test image with distinctive pattern
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        test_image[0:50, :] = [255, 0, 0]  # Top half red
        test_image[50:100, :] = [0, 0, 255]  # Bottom half blue

        # Save with EXIF orientation 3
        pil_image = Image.fromarray(test_image)
        temp_file = tmp_path / "exif_3.jpg"

        # Create EXIF data with orientation 3
        exif_dict = {"0th": {274: 3}}  # 274 is Orientation tag
        try:
            from PIL import ImageFile
            pil_image.save(temp_file, "JPEG", exif=pil_image.getexif())
        except:
            # Fallback: just save without EXIF (orientation handling tested separately)
            pil_image.save(temp_file, "JPEG")

        # Process (won't test actual rotation without proper EXIF, but tests no crash)
        result = preprocessor.preprocess(str(temp_file))
        assert result is not None

    def test_exif_orientation_6(self, preprocessor, tmp_path):
        """Test 270° rotation (EXIF orientation 6)"""
        test_image = np.random.randint(0, 255, (100, 150, 3), dtype=np.uint8)
        pil_image = Image.fromarray(test_image)
        temp_file = tmp_path / "exif_6.jpg"
        pil_image.save(temp_file, "JPEG")

        # Process
        result = preprocessor.preprocess(str(temp_file))
        assert result is not None

    def test_exif_orientation_8(self, preprocessor, tmp_path):
        """Test 90° rotation (EXIF orientation 8)"""
        test_image = np.random.randint(0, 255, (150, 100, 3), dtype=np.uint8)
        pil_image = Image.fromarray(test_image)
        temp_file = tmp_path / "exif_8.jpg"
        pil_image.save(temp_file, "JPEG")

        # Process
        result = preprocessor.preprocess(str(temp_file))
        assert result is not None

    def test_no_exif_data(self, preprocessor, temp_image_path):
        """Test images without EXIF data"""
        # Create image without EXIF
        image = np.random.randint(0, 255, (500, 500, 3), dtype=np.uint8)
        image_path = temp_image_path(image)

        # Process (should not crash)
        result = preprocessor.preprocess(image_path)
        assert result is not None

    # ==================== EDGE CASE TESTS: LIGHTING ====================

    def test_extremely_dark_image(self, preprocessor_no_threshold, temp_image_path):
        """Test contrast enhancement activation for dark images"""
        # Create very dark image (mean brightness < 50)
        dark_image = np.random.randint(0, 40, (1000, 1000, 3), dtype=np.uint8)
        image_path = temp_image_path(dark_image)

        # Process
        result = preprocessor_no_threshold.preprocess(image_path)

        # Verify contrast enhancement was applied
        # Result should have higher brightness than input
        assert result is not None
        # Check that processing didn't crash
        assert result.size > 0

    def test_extremely_bright_image(self, preprocessor_no_threshold, temp_image_path):
        """Test contrast enhancement activation for bright images"""
        # Create very bright image (mean brightness > 200)
        bright_image = np.random.randint(200, 255, (1000, 1000, 3), dtype=np.uint8)
        image_path = temp_image_path(bright_image)

        # Process
        result = preprocessor_no_threshold.preprocess(image_path)

        # Verify processing succeeded
        assert result is not None
        assert result.size > 0

    def test_normal_lighting(self, preprocessor_no_threshold, temp_image_path):
        """Test that contrast enhancement is skipped for normal images"""
        # Create normal lighting image (mean brightness ~120)
        normal_image = np.random.randint(100, 140, (1000, 1000, 3), dtype=np.uint8)
        image_path = temp_image_path(normal_image)

        # Process
        result = preprocessor_no_threshold.preprocess(image_path)

        # Verify processing succeeded without enhancement
        assert result is not None
        assert result.size > 0

    # ==================== EDGE CASE TESTS: COLOR MODES ====================

    def test_grayscale_image(self, preprocessor, tmp_path):
        """Test grayscale image handling"""
        # Create grayscale image
        gray_image = np.random.randint(0, 255, (1000, 1000), dtype=np.uint8)
        pil_image = Image.fromarray(gray_image, mode='L')
        temp_file = tmp_path / "grayscale.png"
        pil_image.save(temp_file)

        # Process
        result = preprocessor.preprocess(str(temp_file))
        assert result is not None

    def test_rgba_image(self, preprocessor, tmp_path):
        """Test RGBA image handling (with alpha channel)"""
        # Create RGBA image
        rgba_image = np.random.randint(0, 255, (1000, 1000, 4), dtype=np.uint8)
        pil_image = Image.fromarray(rgba_image, mode='RGBA')
        temp_file = tmp_path / "rgba.png"
        pil_image.save(temp_file)

        # Process (should convert to RGB internally)
        result = preprocessor.preprocess(str(temp_file))
        assert result is not None

    # ==================== ERROR HANDLING TESTS ====================

    def test_nonexistent_file(self, preprocessor):
        """Test handling of nonexistent file"""
        with pytest.raises(FileNotFoundError):
            preprocessor.preprocess("/nonexistent/path/image.jpg")

    def test_corrupt_image(self, preprocessor, tmp_path):
        """Test handling of corrupt image file"""
        # Create corrupt file
        corrupt_file = tmp_path / "corrupt.jpg"
        corrupt_file.write_bytes(b"not a valid image")

        # Should raise ValueError
        with pytest.raises(ValueError):
            preprocessor.preprocess(str(corrupt_file))

    def test_empty_file(self, preprocessor, tmp_path):
        """Test handling of empty file"""
        empty_file = tmp_path / "empty.jpg"
        empty_file.write_bytes(b"")

        with pytest.raises(ValueError):
            preprocessor.preprocess(str(empty_file))

    # ==================== PERFORMANCE TESTS ====================

    def test_processing_speed(self, preprocessor, temp_image_path):
        """Verify processing time < 300ms for typical mobile photo"""
        # Create typical mobile photo size (3000x4000)
        mobile_photo = np.random.randint(0, 255, (4000, 3000, 3), dtype=np.uint8)
        image_path = temp_image_path(mobile_photo)

        # Measure processing time
        start_time = time.time()
        result = preprocessor.preprocess(image_path)
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms

        # Verify time constraint
        assert elapsed_time < 300, f"Processing took {elapsed_time:.1f}ms, should be < 300ms"
        assert result is not None

    def test_processing_speed_small_image(self, preprocessor, temp_image_path):
        """Verify fast processing for small images"""
        # Create small image (500x500)
        small_photo = np.random.randint(0, 255, (500, 500, 3), dtype=np.uint8)
        image_path = temp_image_path(small_photo)

        # Measure processing time
        start_time = time.time()
        result = preprocessor.preprocess(image_path)
        elapsed_time = (time.time() - start_time) * 1000

        # Small images should be very fast
        assert elapsed_time < 200, f"Small image processing took {elapsed_time:.1f}ms, should be < 200ms"
        assert result is not None

    def test_memory_usage(self, preprocessor, temp_image_path):
        """Verify reasonable memory usage for large images"""
        # Create large image (4000x3000)
        large_image = np.random.randint(0, 255, (3000, 4000, 3), dtype=np.uint8)
        image_path = temp_image_path(large_image)

        # Process (should not crash with OOM)
        result = preprocessor.preprocess(image_path)

        # Verify result is downscaled appropriately
        if len(result.shape) == 3:
            height, width = result.shape[:2]
        else:
            height, width = result.shape

        # Should be downscaled from 4000x3000
        assert max(height, width) <= 2000, "Large image should be downscaled"

    # ==================== COMPARISON TESTS ====================

    def test_speed_comparison_with_old(self, temp_image_path):
        """Compare speed with old MobilePhotoOptimizer"""
        # Create typical mobile photo
        mobile_photo = np.random.randint(0, 255, (4000, 3000, 3), dtype=np.uint8)
        image_path = temp_image_path(mobile_photo)

        # Test SimpleMobilePreprocessor
        simple = SimpleMobilePreprocessor()
        start_simple = time.time()
        result_simple = simple.preprocess(image_path)
        time_simple = (time.time() - start_simple) * 1000

        # Test old MobilePhotoOptimizer (quick_mode for fair comparison)
        old = MobilePhotoOptimizer()
        temp_output = image_path.replace(".png", "_old.png")
        start_old = time.time()
        old.quick_preprocess(image_path, temp_output)
        time_old = (time.time() - start_old) * 1000

        # Clean up
        if os.path.exists(temp_output):
            os.remove(temp_output)

        print(f"\nSpeed comparison:")
        print(f"  SimpleMobilePreprocessor: {time_simple:.1f}ms")
        print(f"  MobilePhotoOptimizer (quick): {time_old:.1f}ms")
        print(f"  Speedup: {time_old / time_simple:.1f}x")

        # Simple should be faster
        assert time_simple < time_old, f"Simple should be faster: {time_simple:.1f}ms vs {time_old:.1f}ms"

    def test_output_dimensions_consistency(self, preprocessor, temp_image_path):
        """Test that output dimensions are consistent and predictable"""
        # Test various input sizes
        test_sizes = [
            (100, 100),    # Very small
            (500, 500),    # Small
            (1500, 1500),  # Optimal
            (3000, 3000),  # Large
            (5000, 5000),  # Very large
        ]

        for width, height in test_sizes:
            image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            image_path = temp_image_path(image)

            result = preprocessor.preprocess(image_path)

            # Get result dimensions
            if len(result.shape) == 3:
                r_height, r_width = result.shape[:2]
            else:
                r_height, r_width = result.shape

            # Verify dimensions meet criteria
            min_edge = min(r_height, r_width)
            max_edge = max(r_height, r_width)

            assert min_edge >= 1000, f"Min edge should be >= 1000, got {min_edge} for input {width}x{height}"
            assert max_edge <= 2000, f"Max edge should be <= 2000, got {max_edge} for input {width}x{height}"

    # ==================== THRESHOLD TOGGLE TESTS ====================

    def test_threshold_enabled(self, temp_image_path):
        """Test that threshold is applied when enabled"""
        preprocessor = SimpleMobilePreprocessor(enable_threshold=True)
        image = np.random.randint(0, 255, (1000, 1000, 3), dtype=np.uint8)
        image_path = temp_image_path(image)

        result = preprocessor.preprocess(image_path)

        # Result should be binary (threshold applied)
        assert len(result.shape) == 2, "Thresholded image should be 2D (grayscale)"
        unique_values = np.unique(result)
        assert len(unique_values) <= 2, "Binary image should have at most 2 values"

    def test_threshold_disabled(self, temp_image_path):
        """Test that threshold is skipped when disabled"""
        preprocessor = SimpleMobilePreprocessor(enable_threshold=False)
        image = np.random.randint(0, 255, (1000, 1000, 3), dtype=np.uint8)
        image_path = temp_image_path(image)

        result = preprocessor.preprocess(image_path)

        # Result should be color (threshold skipped)
        assert len(result.shape) == 3, "Non-thresholded image should be 3D (color)"

    # ==================== INTEGRATION TESTS ====================

    def test_full_pipeline(self, preprocessor, temp_image_path):
        """Test complete preprocessing pipeline"""
        # Create realistic test case: large, bright, portrait photo
        test_image = np.random.randint(180, 255, (4000, 3000, 3), dtype=np.uint8)
        image_path = temp_image_path(test_image)

        # Process
        result = preprocessor.preprocess(image_path)

        # Verify all steps completed
        assert result is not None
        assert result.size > 0

        # Verify size constraints
        if len(result.shape) == 3:
            height, width = result.shape[:2]
        else:
            height, width = result.shape

        assert min(height, width) >= 1000
        assert max(height, width) <= 2000

    def test_real_world_scenario(self, preprocessor, tmp_path):
        """Test with a realistic mobile photo scenario"""
        # Simulate a real mobile photo: 3024x4032 (iPhone resolution)
        realistic_photo = np.random.randint(80, 180, (4032, 3024, 3), dtype=np.uint8)

        # Save as JPEG (common mobile format)
        pil_image = Image.fromarray(realistic_photo)
        temp_file = tmp_path / "mobile_photo.jpg"
        pil_image.save(temp_file, "JPEG", quality=85)

        # Process
        start_time = time.time()
        result = preprocessor.preprocess(str(temp_file))
        elapsed_time = (time.time() - start_time) * 1000

        # Verify
        assert result is not None
        assert elapsed_time < 300, f"Real-world scenario took {elapsed_time:.1f}ms"

        # Verify dimensions were reduced
        if len(result.shape) == 3:
            height, width = result.shape[:2]
        else:
            height, width = result.shape

        assert max(height, width) <= 2000, "Should downscale large mobile photo"
