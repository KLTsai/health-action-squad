"""PDF to image converter for health reports.

將健康檢查報告PDF轉換為圖片，支援多頁PDF處理。
Converts PDF health reports to images for OCR processing with support for multi-page PDFs.
"""

import asyncio
from pathlib import Path
from typing import List, Optional
import tempfile

from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image
import numpy as np

from ..utils.logger import AgentLogger


class PDFConverter:
    """PDF轉圖片轉換器

    Converts PDF files to images for OCR processing.
    Supports multi-page PDFs and handles various DPI/quality settings.

    Attributes:
        logger: Structured logger for tracing
        dpi: DPI setting for conversion (higher = better quality, slower)
    """

    # ========================================================================
    # 初始化 (Initialization)
    # ========================================================================

    def __init__(self, dpi: int = 300):
        """初始化PDF轉換器

        Initialize PDF converter with configurable DPI.

        Args:
            dpi: 轉換DPI設置 (Default: 300 for medical documents)
                300 DPI: 標準醫療文件品質 (standard medical document quality)
                200 DPI: 快速轉換 (faster conversion)
                600 DPI: 高精度 (high precision, slower)
        """
        self.dpi = dpi
        self.logger = AgentLogger("PDFConverter")
        self.logger.info("PDFConverter initialized", dpi=dpi)

    # ========================================================================
    # 主要轉換方法 (Main Conversion Methods)
    # ========================================================================

    async def convert_pdf_to_images(
        self, pdf_path: str, output_dir: Optional[str] = None
    ) -> List[str]:
        """異步將PDF轉換為圖片

        Asynchronously convert PDF to images.

        Args:
            pdf_path: PDF檔案路徑 (Path to PDF file)
            output_dir: 輸出目錄 (Output directory. If None, uses temp directory)

        Returns:
            圖片檔案路徑列表 (List of image file paths)

        Raises:
            FileNotFoundError: 如果PDF不存在
            ValueError: 如果PDF無法被轉換
        """
        # 驗證PDF檔案存在
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            # 在執行緒池中運行PDF轉換以避免阻斷
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._perform_conversion,
                str(pdf_file),
                output_dir,
            )

            self.logger.info(
                "Successfully converted PDF to images",
                pdf_path=str(pdf_file),
                image_count=len(result),
            )

            return result

        except Exception as e:
            self.logger.error("Error converting PDF", error=str(e), pdf_path=str(pdf_file))
            raise

    async def convert_pdf_bytes(
        self, pdf_bytes: bytes, output_dir: Optional[str] = None
    ) -> List[str]:
        """異步將PDF字節轉換為圖片

        Convert PDF from bytes to images (useful for API requests).

        Args:
            pdf_bytes: PDF檔案的字節內容 (PDF file bytes)
            output_dir: 輸出目錄 (Output directory. If None, uses temp directory)

        Returns:
            圖片檔案路徑列表 (List of image file paths)
        """
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._perform_conversion_from_bytes,
                pdf_bytes,
                output_dir,
            )

            self.logger.info(
                "Successfully converted PDF bytes to images",
                image_count=len(result),
            )

            return result

        except Exception as e:
            self.logger.error("Error converting PDF bytes", error=str(e))
            raise

    def convert_pdf_to_images_sync(
        self, pdf_path: str, output_dir: Optional[str] = None
    ) -> List[str]:
        """同步將PDF轉換為圖片 (用於不需要異步的場景)

        Synchronously convert PDF to images (for non-async contexts).

        Args:
            pdf_path: PDF檔案路徑 (Path to PDF file)
            output_dir: 輸出目錄 (Output directory. If None, uses temp directory)

        Returns:
            圖片檔案路徑列表 (List of image file paths)
        """
        return self._perform_conversion(pdf_path, output_dir)

    # ========================================================================
    # 內部轉換邏輯 (Internal Conversion Logic)
    # ========================================================================

    def _perform_conversion(
        self, pdf_path: str, output_dir: Optional[str] = None
    ) -> List[str]:
        """執行實際的PDF轉換

        Perform the actual PDF to image conversion.

        Args:
            pdf_path: PDF檔案路徑 (Path to PDF file)
            output_dir: 輸出目錄 (Output directory)

        Returns:
            圖片檔案路徑列表 (List of image file paths)
        """
        # 決定輸出目錄
        if output_dir is None:
            output_dir = tempfile.gettempdir()
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        output_dir = Path(output_dir)

        try:
            # 使用pdf2image轉換PDF
            images = convert_from_path(pdf_path, dpi=self.dpi)

            if not images:
                raise ValueError(f"No images extracted from PDF: {pdf_path}")

            # 保存圖片
            image_paths = []
            pdf_name = Path(pdf_path).stem  # 獲取PDF檔案名稱 (不含副檔名)

            for i, image in enumerate(images):
                # 生成圖片檔案名稱: report_page_1.png, report_page_2.png, 等
                image_filename = f"{pdf_name}_page_{i + 1}.png"
                image_path = output_dir / image_filename

                # 保存為PNG
                image.save(str(image_path), "PNG")
                image_paths.append(str(image_path))

                self.logger.debug(
                    "Saved page image",
                    page=i + 1,
                    output_path=str(image_path),
                )

            return image_paths

        except Exception as e:
            self.logger.error(
                "PDF conversion failed",
                pdf_path=pdf_path,
                error=str(e),
            )
            raise

    def _perform_conversion_from_bytes(
        self, pdf_bytes: bytes, output_dir: Optional[str] = None
    ) -> List[str]:
        """從PDF字節執行轉換

        Perform conversion from PDF bytes.

        Args:
            pdf_bytes: PDF檔案字節 (PDF file bytes)
            output_dir: 輸出目錄 (Output directory)

        Returns:
            圖片檔案路徑列表 (List of image file paths)
        """
        # 決定輸出目錄
        if output_dir is None:
            output_dir = tempfile.gettempdir()
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        output_dir = Path(output_dir)

        try:
            # 使用pdf2image從字節轉換
            images = convert_from_bytes(pdf_bytes, dpi=self.dpi)

            if not images:
                raise ValueError("No images extracted from PDF bytes")

            # 保存圖片
            image_paths = []

            for i, image in enumerate(images):
                # 生成圖片檔案名稱
                image_filename = f"health_report_page_{i + 1}.png"
                image_path = output_dir / image_filename

                # 保存為PNG
                image.save(str(image_path), "PNG")
                image_paths.append(str(image_path))

                self.logger.debug(
                    "Saved page image from bytes",
                    page=i + 1,
                    output_path=str(image_path),
                )

            return image_paths

        except Exception as e:
            self.logger.error(
                "PDF bytes conversion failed",
                error=str(e),
            )
            raise

    # ========================================================================
    # 圖片處理工具方法 (Image Processing Utilities)
    # ========================================================================

    def enhance_image_quality(self, image_path: str) -> str:
        """增強圖片品質以改善OCR結果

        Enhance image quality for better OCR results.
        - Increase contrast
        - Reduce noise
        - Sharpen text

        Args:
            image_path: 圖片檔案路徑 (Path to image file)

        Returns:
            處理後圖片的路徑 (Path to enhanced image)
        """
        try:
            from PIL import ImageEnhance, ImageFilter

            # 開啟圖片
            img = Image.open(image_path)

            # 轉換為RGB (如果是RGBA則移除alpha通道)
            if img.mode == "RGBA":
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # 1. 增加對比度 (Increase contrast)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)

            # 2. 提高銳度 (Increase sharpness)
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)

            # 3. 應用雙邊濾波以減少噪音同時保留邊界
            # (Apply bilateral filter to reduce noise while preserving edges)
            img_array = np.array(img)
            # 簡單的中值濾波 (Simple median filter)
            img = Image.fromarray(img_array)
            img = img.filter(ImageFilter.MedianFilter(size=3))

            # 保存增強後的圖片
            output_path = str(Path(image_path).parent / f"enhanced_{Path(image_path).name}")
            img.save(output_path, "PNG")

            self.logger.debug(
                "Enhanced image quality",
                input_path=image_path,
                output_path=output_path,
            )

            return output_path

        except Exception as e:
            self.logger.error(
                "Image enhancement failed",
                image_path=image_path,
                error=str(e),
            )
            # 返回原始路徑，如果增強失敗
            return image_path

    def crop_to_content(self, image_path: str) -> str:
        """裁剪圖片以移除空白邊界

        Crop image to remove whitespace borders.

        Args:
            image_path: 圖片檔案路徑 (Path to image file)

        Returns:
            裁剪後圖片的路徑 (Path to cropped image)
        """
        try:
            from PIL import ImageOps

            img = Image.open(image_path)

            # 自動裁剪白色邊界 (Auto-crop white borders)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 使用ImageOps.invert和getbbox來找內容邊界
            # (Use ImageOps to find content boundaries)
            inverted = ImageOps.invert(img.convert("L"))
            bbox = inverted.getbbox()

            if bbox:
                img_cropped = img.crop(bbox)
            else:
                img_cropped = img

            # 保存裁剪後的圖片
            output_path = str(Path(image_path).parent / f"cropped_{Path(image_path).name}")
            img_cropped.save(output_path, "PNG")

            self.logger.debug(
                "Cropped image to content",
                input_path=image_path,
                output_path=output_path,
                bbox=bbox,
            )

            return output_path

        except Exception as e:
            self.logger.error(
                "Image cropping failed",
                image_path=image_path,
                error=str(e),
            )
            return image_path

    def get_pdf_page_count(self, pdf_path: str) -> int:
        """獲取PDF檔案的頁數

        Get the number of pages in a PDF file.

        Args:
            pdf_path: PDF檔案路徑 (Path to PDF file)

        Returns:
            頁數 (Number of pages)
        """
        try:
            # 讀取PDF的第一頁以確定頁數
            # (This is a simple approach - pdf2image doesn't directly expose page count)
            images = convert_from_path(pdf_path, first_page=1, last_page=1)
            # 如果成功，我們知道至少有1頁

            # 對於更精確的頁數，可以使用PyPDF2
            try:
                from PyPDF2 import PdfReader

                reader = PdfReader(pdf_path)
                return len(reader.pages)
            except ImportError:
                # 如果PyPDF2不可用，只返回轉換的頁數
                images = convert_from_path(pdf_path)
                return len(images)

        except Exception as e:
            self.logger.error(
                "Failed to get PDF page count",
                pdf_path=pdf_path,
                error=str(e),
            )
            return 0

    # ========================================================================
    # 批量處理方法 (Batch Processing Methods)
    # ========================================================================

    async def convert_multiple_pdfs(
        self, pdf_paths: List[str], output_dir: Optional[str] = None
    ) -> dict:
        """批量異步轉換多個PDF檔案

        Batch convert multiple PDF files asynchronously.

        Args:
            pdf_paths: PDF檔案路徑列表 (List of PDF file paths)
            output_dir: 輸出目錄 (Output directory)

        Returns:
            字典，key為PDF路徑，value為圖片路徑列表
            (Dictionary mapping PDF paths to image path lists)
        """
        tasks = [self.convert_pdf_to_images(pdf_path, output_dir) for pdf_path in pdf_paths]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for pdf_path, result in zip(pdf_paths, results):
            if isinstance(result, Exception):
                self.logger.error(
                    "Failed to convert PDF in batch",
                    pdf_path=pdf_path,
                    error=str(result),
                )
                output[pdf_path] = []
            else:
                output[pdf_path] = result

        return output
