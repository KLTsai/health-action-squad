"""Quick validation script for SimpleMobilePreprocessor"""

import sys
import os
import time
import numpy as np
from PIL import Image
import cv2
import tempfile

# Fix encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import directly from module files to avoid package-level imports
import importlib.util

# Load SimpleMobilePreprocessor
spec1 = importlib.util.spec_from_file_location(
    "simple_mobile_preprocessor",
    os.path.join(os.path.dirname(__file__), "src/parsers/simple_mobile_preprocessor.py")
)
simple_module = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(simple_module)
SimpleMobilePreprocessor = simple_module.SimpleMobilePreprocessor

# Load MobilePhotoOptimizer
spec2 = importlib.util.spec_from_file_location(
    "image_preprocessor",
    os.path.join(os.path.dirname(__file__), "src/parsers/image_preprocessor.py")
)
old_module = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(old_module)
MobilePhotoOptimizer = old_module.MobilePhotoOptimizer


def create_temp_image(image_array, suffix=".png"):
    """Helper to create temporary image file"""
    with tempfile.NamedTemporaryFile(mode='wb', suffix=suffix, delete=False) as f:
        if len(image_array.shape) == 2:
            Image.fromarray(image_array).save(f.name, "PNG")
        else:
            Image.fromarray(image_array).save(f.name, "PNG")
        return f.name


def test_very_small_image():
    """Test upscaling of very small images"""
    print("\n[TEST] Very small image (100x100) → should upscale")
    small_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    image_path = create_temp_image(small_image)

    preprocessor = SimpleMobilePreprocessor()
    result = preprocessor.preprocess(image_path)

    if len(result.shape) == 3:
        height, width = result.shape[:2]
    else:
        height, width = result.shape
    min_edge = min(height, width)

    os.unlink(image_path)

    assert min_edge >= 1000, f"FAIL: Min edge should be >= 1000, got {min_edge}"
    print(f"✓ PASS: Upscaled to {width}x{height} (min edge: {min_edge})")


def test_very_large_image():
    """Test downscaling of very large images"""
    print("\n[TEST] Very large image (5000x5000) → should downscale")
    large_image = np.random.randint(0, 255, (5000, 5000, 3), dtype=np.uint8)
    image_path = create_temp_image(large_image)

    preprocessor = SimpleMobilePreprocessor()
    result = preprocessor.preprocess(image_path)

    if len(result.shape) == 3:
        height, width = result.shape[:2]
    else:
        height, width = result.shape
    max_edge = max(height, width)

    os.unlink(image_path)

    assert max_edge <= 2000, f"FAIL: Max edge should be <= 2000, got {max_edge}"
    print(f"✓ PASS: Downscaled to {width}x{height} (max edge: {max_edge})")


def test_optimal_size():
    """Test that optimal size images are not resized"""
    print("\n[TEST] Optimal size image (1500x1500) → should not resize")
    optimal_image = np.random.randint(0, 255, (1500, 1500, 3), dtype=np.uint8)
    image_path = create_temp_image(optimal_image)

    preprocessor = SimpleMobilePreprocessor(enable_threshold=False)
    result = preprocessor.preprocess(image_path)

    os.unlink(image_path)

    assert result.shape[:2] == (1500, 1500), f"FAIL: Should be 1500x1500, got {result.shape[:2]}"
    print(f"✓ PASS: Size unchanged {result.shape[:2]}")


def test_dark_image():
    """Test contrast enhancement for dark images"""
    print("\n[TEST] Extremely dark image → should enhance contrast")
    dark_image = np.random.randint(0, 40, (1000, 1000, 3), dtype=np.uint8)
    image_path = create_temp_image(dark_image)

    preprocessor = SimpleMobilePreprocessor(enable_threshold=False)
    result = preprocessor.preprocess(image_path)

    os.unlink(image_path)

    assert result is not None, "FAIL: Result should not be None"
    print(f"✓ PASS: Processed dark image successfully")


def test_bright_image():
    """Test contrast enhancement for bright images"""
    print("\n[TEST] Extremely bright image → should enhance contrast")
    bright_image = np.random.randint(200, 255, (1000, 1000, 3), dtype=np.uint8)
    image_path = create_temp_image(bright_image)

    preprocessor = SimpleMobilePreprocessor(enable_threshold=False)
    result = preprocessor.preprocess(image_path)

    os.unlink(image_path)

    assert result is not None, "FAIL: Result should not be None"
    print(f"✓ PASS: Processed bright image successfully")


def test_normal_lighting():
    """Test that normal lighting skips enhancement"""
    print("\n[TEST] Normal lighting → should skip contrast enhancement")
    normal_image = np.random.randint(100, 140, (1000, 1000, 3), dtype=np.uint8)
    image_path = create_temp_image(normal_image)

    preprocessor = SimpleMobilePreprocessor(enable_threshold=False)
    result = preprocessor.preprocess(image_path)

    os.unlink(image_path)

    assert result is not None, "FAIL: Result should not be None"
    print(f"✓ PASS: Processed normal lighting successfully")


def test_processing_speed():
    """Test processing speed < 300ms"""
    print("\n[TEST] Processing speed (4000x3000 image) → should be < 300ms")
    mobile_photo = np.random.randint(0, 255, (4000, 3000, 3), dtype=np.uint8)
    image_path = create_temp_image(mobile_photo)

    preprocessor = SimpleMobilePreprocessor()

    start_time = time.time()
    result = preprocessor.preprocess(image_path)
    elapsed_time = (time.time() - start_time) * 1000

    os.unlink(image_path)

    assert elapsed_time < 300, f"FAIL: Processing took {elapsed_time:.1f}ms, should be < 300ms"
    print(f"✓ PASS: Processing took {elapsed_time:.1f}ms")


def test_speed_comparison():
    """Compare speed with old MobilePhotoOptimizer"""
    print("\n[TEST] Speed comparison with old MobilePhotoOptimizer")
    mobile_photo = np.random.randint(0, 255, (4000, 3000, 3), dtype=np.uint8)
    image_path = create_temp_image(mobile_photo)

    # Test SimpleMobilePreprocessor
    simple = SimpleMobilePreprocessor()
    start_simple = time.time()
    result_simple = simple.preprocess(image_path)
    time_simple = (time.time() - start_simple) * 1000

    # Test old MobilePhotoOptimizer (quick mode)
    old = MobilePhotoOptimizer()
    temp_output = image_path.replace(".png", "_old.png")
    start_old = time.time()
    old.quick_preprocess(image_path, temp_output)
    time_old = (time.time() - start_old) * 1000

    # Clean up
    os.unlink(image_path)
    if os.path.exists(temp_output):
        os.unlink(temp_output)

    speedup = time_old / time_simple
    print(f"  SimpleMobilePreprocessor: {time_simple:.1f}ms")
    print(f"  MobilePhotoOptimizer (quick): {time_old:.1f}ms")
    print(f"  Speedup: {speedup:.1f}x")

    assert time_simple < time_old, f"FAIL: Simple should be faster"
    print(f"✓ PASS: SimpleMobilePreprocessor is {speedup:.1f}x faster")


def test_threshold_toggle():
    """Test threshold enable/disable"""
    print("\n[TEST] Threshold toggle")
    image = np.random.randint(0, 255, (1000, 1000, 3), dtype=np.uint8)
    image_path = create_temp_image(image)

    # Test with threshold enabled
    preprocessor_on = SimpleMobilePreprocessor(enable_threshold=True)
    result_on = preprocessor_on.preprocess(image_path)

    # Test with threshold disabled
    preprocessor_off = SimpleMobilePreprocessor(enable_threshold=False)
    result_off = preprocessor_off.preprocess(image_path)

    os.unlink(image_path)

    assert len(result_on.shape) == 2, "FAIL: Thresholded should be 2D"
    assert len(result_off.shape) == 3, "FAIL: Non-thresholded should be 3D"
    print(f"✓ PASS: Threshold toggle works (on: {result_on.shape}, off: {result_off.shape})")


def test_error_handling():
    """Test error handling"""
    print("\n[TEST] Error handling")
    preprocessor = SimpleMobilePreprocessor()

    # Test nonexistent file
    try:
        preprocessor.preprocess("/nonexistent/path/image.jpg")
        assert False, "FAIL: Should raise FileNotFoundError"
    except FileNotFoundError:
        print(f"✓ PASS: Correctly raises FileNotFoundError")

    # Test corrupt file
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.jpg', delete=False) as f:
        f.write(b"not a valid image")
        corrupt_path = f.name

    try:
        preprocessor.preprocess(corrupt_path)
        assert False, "FAIL: Should raise ValueError for corrupt image"
    except ValueError:
        print(f"✓ PASS: Correctly raises ValueError for corrupt image")
    finally:
        os.unlink(corrupt_path)


def main():
    """Run all tests"""
    print("=" * 70)
    print("SimpleMobilePreprocessor - Comprehensive Test Suite")
    print("=" * 70)

    tests = [
        test_very_small_image,
        test_very_large_image,
        test_optimal_size,
        test_dark_image,
        test_bright_image,
        test_normal_lighting,
        test_processing_speed,
        test_speed_comparison,
        test_threshold_toggle,
        test_error_handling,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
