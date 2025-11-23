"""Image Preprocessing Module for Mobile Photo Quality Optimization

Handles common mobile photo issues:
- Blur detection and sharpening
- Auto-rotation (based on EXIF orientation)
- Contrast enhancement
- Perspective correction
- Noise reduction

Optimized for hand-held phone photos of health reports.
"""

import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocessor for mobile photo quality optimization"""

    def __init__(
        self,
        target_dpi: int = 300,
        auto_rotate: bool = True,
        denoise: bool = True,
        enhance_contrast: bool = True,
        sharpen: bool = True,
        correct_perspective: bool = True,
    ):
        """
        Initialize image preprocessor

        Args:
            target_dpi: Target DPI for OCR (default 300 for optimal accuracy)
            auto_rotate: Enable EXIF-based auto-rotation
            denoise: Enable noise reduction
            enhance_contrast: Enable contrast enhancement
            sharpen: Enable sharpening for blur reduction
            correct_perspective: Enable perspective correction
        """
        self.target_dpi = target_dpi
        self.auto_rotate = auto_rotate
        self.denoise = denoise
        self.enhance_contrast = enhance_contrast
        self.sharpen = sharpen
        self.correct_perspective = correct_perspective

    def preprocess(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        Preprocess image for optimal OCR accuracy

        Args:
            image_path: Path to input image
            output_path: Path to save preprocessed image (optional)

        Returns:
            Path to preprocessed image
        """
        logger.info(f"Preprocessing image: {image_path}")

        # Load image with PIL (for EXIF handling)
        pil_image = Image.open(image_path)

        # Step 1: Auto-rotate based on EXIF orientation
        if self.auto_rotate:
            pil_image = self._auto_rotate_exif(pil_image)

        # Convert to OpenCV format for advanced processing
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # Step 2: Resize to target DPI if needed
        cv_image = self._resize_to_target_dpi(cv_image, pil_image)

        # Step 3: Denoise (remove camera noise)
        if self.denoise:
            cv_image = self._denoise_image(cv_image)

        # Step 4: Perspective correction (for angled photos)
        if self.correct_perspective:
            cv_image = self._correct_perspective(cv_image)

        # Step 5: Enhance contrast (for poor lighting)
        if self.enhance_contrast:
            cv_image = self._enhance_contrast(cv_image)

        # Step 6: Sharpen (reduce blur from hand movement)
        if self.sharpen:
            cv_image = self._sharpen_image(cv_image)

        # Step 7: Binarization (convert to black/white for OCR)
        cv_image = self._adaptive_threshold(cv_image)

        # Save preprocessed image
        if output_path is None:
            output_path = image_path.replace(".", "_preprocessed.")

        cv2.imwrite(output_path, cv_image)
        logger.info(f"Preprocessed image saved to: {output_path}")

        return output_path

    def _auto_rotate_exif(self, image: Image.Image) -> Image.Image:
        """Auto-rotate image based on EXIF orientation tag"""
        try:
            exif = image._getexif()
            if exif is not None:
                for tag, value in exif.items():
                    tag_name = TAGS.get(tag, tag)
                    if tag_name == "Orientation":
                        if value == 3:
                            image = image.rotate(180, expand=True)
                        elif value == 6:
                            image = image.rotate(270, expand=True)
                        elif value == 8:
                            image = image.rotate(90, expand=True)
                        logger.info(f"Auto-rotated image (EXIF orientation: {value})")
        except (AttributeError, KeyError, IndexError):
            logger.debug("No EXIF orientation data found")

        return image

    def _resize_to_target_dpi(
        self, cv_image: np.ndarray, pil_image: Image.Image
    ) -> np.ndarray:
        """Resize image to target DPI for optimal OCR"""
        # Get current DPI
        dpi = pil_image.info.get("dpi", (72, 72))
        current_dpi = dpi[0] if isinstance(dpi, tuple) else dpi

        # Calculate scale factor
        scale_factor = self.target_dpi / current_dpi

        # Resize if needed (skip if already close to target)
        if abs(scale_factor - 1.0) > 0.1:
            new_width = int(cv_image.shape[1] * scale_factor)
            new_height = int(cv_image.shape[0] * scale_factor)
            cv_image = cv2.resize(
                cv_image, (new_width, new_height), interpolation=cv2.INTER_CUBIC
            )
            logger.info(
                f"Resized image from {current_dpi} DPI to {self.target_dpi} DPI"
            )

        return cv_image

    def _denoise_image(self, image: np.ndarray) -> np.ndarray:
        """Remove camera noise using Non-Local Means Denoising"""
        # Use fastNlMeansDenoisingColored for color images
        denoised = cv2.fastNlMeansDenoisingColored(
            image,
            None,
            h=10,  # Filter strength (higher = more denoising)
            hColor=10,  # Filter strength for color components
            templateWindowSize=7,
            searchWindowSize=21,
        )
        logger.debug("Applied denoising")
        return denoised

    def _correct_perspective(self, image: np.ndarray) -> np.ndarray:
        """
        Detect and correct perspective distortion (for angled photos)

        Uses edge detection + contour finding to detect document boundaries

        Performance optimization: Downscale large images before processing
        """
        # PERFORMANCE OPTIMIZATION: Downscale if image is too large
        # Perspective detection works fine on smaller images and is MUCH faster
        original_shape = image.shape
        max_dimension = 2000  # Max width/height for perspective detection

        if max(image.shape[0], image.shape[1]) > max_dimension:
            scale = max_dimension / max(image.shape[0], image.shape[1])
            small_width = int(image.shape[1] * scale)
            small_height = int(image.shape[0] * scale)
            working_image = cv2.resize(image, (small_width, small_height), interpolation=cv2.INTER_AREA)
            logger.info(f"Downscaled image for perspective detection: {original_shape[:2]} -> {working_image.shape[:2]}")
        else:
            working_image = image
            scale = 1.0

        # Convert to grayscale
        gray = cv2.cvtColor(working_image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Find largest rectangular contour (likely the document)
        max_area = 0
        best_contour = None

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area and area > 0.1 * working_image.shape[0] * working_image.shape[1]:
                # Approximate contour to polygon
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

                # Check if it's a quadrilateral
                if len(approx) == 4:
                    max_area = area
                    best_contour = approx

        # Apply perspective transform if valid contour found
        if best_contour is not None:
            # Scale contour points back to original image size
            points = best_contour.reshape(4, 2) / scale
            ordered_points = self._order_points(points)

            # Compute destination points (rectangle)
            (tl, tr, br, bl) = ordered_points
            width_a = np.linalg.norm(br - bl)
            width_b = np.linalg.norm(tr - tl)
            max_width = max(int(width_a), int(width_b))

            height_a = np.linalg.norm(tr - br)
            height_b = np.linalg.norm(tl - bl)
            max_height = max(int(height_a), int(height_b))

            dst_points = np.array(
                [
                    [0, 0],
                    [max_width - 1, 0],
                    [max_width - 1, max_height - 1],
                    [0, max_height - 1],
                ],
                dtype="float32",
            )

            # Compute perspective transform matrix
            matrix = cv2.getPerspectiveTransform(ordered_points, dst_points)

            # Apply transform
            warped = cv2.warpPerspective(image, matrix, (max_width, max_height))
            logger.info("Applied perspective correction")
            return warped
        else:
            logger.debug("No valid document contour found, skipping perspective correction")
            return image

    def _order_points(self, points: np.ndarray) -> np.ndarray:
        """Order points in clockwise order: TL, TR, BR, BL"""
        rect = np.zeros((4, 2), dtype="float32")

        # Top-left has smallest sum, bottom-right has largest sum
        s = points.sum(axis=1)
        rect[0] = points[np.argmin(s)]
        rect[2] = points[np.argmax(s)]

        # Top-right has smallest difference, bottom-left has largest difference
        diff = np.diff(points, axis=1)
        rect[1] = points[np.argmin(diff)]
        rect[3] = points[np.argmax(diff)]

        return rect

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)

        Particularly effective for images with poor lighting
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        # Split channels
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        # Merge channels
        enhanced = cv2.merge([l, a, b])

        # Convert back to BGR
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

        logger.debug("Applied contrast enhancement (CLAHE)")
        return enhanced

    def _sharpen_image(self, image: np.ndarray) -> np.ndarray:
        """
        Sharpen image to reduce blur from hand movement

        Uses unsharp masking technique
        """
        # Create Gaussian blur
        blurred = cv2.GaussianBlur(image, (0, 0), 3)

        # Unsharp mask: original + (original - blurred) * amount
        sharpened = cv2.addWeighted(image, 1.5, blurred, -0.5, 0)

        logger.debug("Applied sharpening (unsharp mask)")
        return sharpened

    def _adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """
        Convert to black/white using adaptive thresholding

        Better than simple thresholding for images with varying lighting
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive threshold
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2,
        )

        logger.debug("Applied adaptive thresholding")
        return binary

    def detect_blur(self, image_path: str) -> Tuple[float, bool]:
        """
        Detect blur level using Laplacian variance

        Args:
            image_path: Path to image

        Returns:
            Tuple of (blur_score, is_blurry)
            - blur_score: Higher = sharper, Lower = blurrier
            - is_blurry: True if blur_score < threshold (100)
        """
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Compute Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Threshold: < 100 is considered blurry
        is_blurry = laplacian_var < 100

        logger.info(f"Blur detection: score={laplacian_var:.2f}, blurry={is_blurry}")
        return laplacian_var, is_blurry


class MobilePhotoOptimizer(ImagePreprocessor):
    """
    Specialized preprocessor optimized for mobile phone photos

    Preset configurations for common mobile photo issues:
    - Hand-held blur
    - Poor lighting
    - Angled shots
    - Camera noise
    """

    def __init__(self):
        """Initialize with mobile-optimized settings"""
        super().__init__(
            target_dpi=300,  # Optimal for OCR
            auto_rotate=True,  # Handle portrait/landscape
            denoise=True,  # Remove camera noise
            enhance_contrast=True,  # Handle poor lighting
            sharpen=True,  # Reduce hand-held blur
            correct_perspective=True,  # Handle angled shots
        )

    def quick_preprocess(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        Quick preprocessing for time-sensitive applications

        Skips perspective correction (slow) and uses lighter denoising
        """
        # Temporarily disable slow operations
        original_perspective = self.correct_perspective
        self.correct_perspective = False

        # Preprocess
        result = self.preprocess(image_path, output_path)

        # Restore settings
        self.correct_perspective = original_perspective

        return result
