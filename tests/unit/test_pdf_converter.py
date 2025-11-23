"""Unit tests for PDF converter module.

Tests PDF to image conversion, image enhancement, and batch processing.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from PIL import Image
import numpy as np

from src.parsers.pdf_converter import PDFConverter


class TestPDFConverter:
    """PDF轉換器單元測試"""

    @pytest.fixture
    def converter(self):
        """建立PDFConverter實例"""
        return PDFConverter(dpi=300)

    @pytest.fixture
    def temp_dir(self):
        """建立臨時目錄"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def sample_pdf(self, temp_dir):
        """建立樣本PDF檔案路徑"""
        pdf_path = Path(temp_dir) / "sample.pdf"
        # 建立空文件作為測試用
        pdf_path.touch()
        return str(pdf_path)

    # ====== 初始化測試 ======

    def test_converter_initialization(self):
        """測試轉換器初始化"""
        converter = PDFConverter(dpi=300)
        assert converter.dpi == 300
        assert converter.logger is not None

    def test_converter_custom_dpi(self):
        """測試自定義DPI設置"""
        converter = PDFConverter(dpi=600)
        assert converter.dpi == 600

    # ====== 同步轉換測試 ======

    def test_sync_conversion_file_not_found(self, converter):
        """測試檔案不存在時的錯誤處理"""
        with pytest.raises(FileNotFoundError):
            converter.convert_pdf_to_images_sync("/nonexistent/path.pdf")

    @patch("src.parsers.pdf_converter.convert_from_path")
    def test_sync_conversion_success(self, mock_convert, converter, sample_pdf, temp_dir):
        """測試同步轉換成功"""
        # 建立模擬的PIL圖片
        mock_image = MagicMock(spec=Image.Image)
        mock_image.save = MagicMock()
        mock_convert.return_value = [mock_image]

        result = converter.convert_pdf_to_images_sync(sample_pdf, temp_dir)

        assert isinstance(result, list)
        assert len(result) > 0
        mock_convert.assert_called_once()

    @patch("src.parsers.pdf_converter.convert_from_path")
    def test_sync_conversion_multiple_pages(self, mock_convert, converter, sample_pdf, temp_dir):
        """測試多頁PDF轉換"""
        # 建立多個模擬圖片
        mock_images = [MagicMock(spec=Image.Image) for _ in range(3)]
        for img in mock_images:
            img.save = MagicMock()

        mock_convert.return_value = mock_images

        result = converter.convert_pdf_to_images_sync(sample_pdf, temp_dir)

        assert len(result) == 3
        # 驗證保存次數
        assert sum(img.save.call_count for img in mock_images) == 3

    # ====== 異步轉換測試 ======

    @pytest.mark.asyncio
    async def test_async_conversion_not_found(self, converter):
        """測試異步轉換檔案不存在"""
        with pytest.raises(FileNotFoundError):
            await converter.convert_pdf_to_images("/nonexistent/path.pdf")

    @pytest.mark.asyncio
    @patch("src.parsers.pdf_converter.convert_from_path")
    async def test_async_conversion_success(self, mock_convert, converter, sample_pdf, temp_dir):
        """測試異步轉換成功"""
        mock_image = MagicMock(spec=Image.Image)
        mock_image.save = MagicMock()
        mock_convert.return_value = [mock_image]

        result = await converter.convert_pdf_to_images(sample_pdf, temp_dir)

        assert isinstance(result, list)
        assert len(result) > 0

    # ====== 字節轉換測試 ======

    @pytest.mark.asyncio
    @patch("src.parsers.pdf_converter.convert_from_bytes")
    async def test_bytes_conversion_success(self, mock_convert, converter, temp_dir):
        """測試從字節轉換成功"""
        mock_image = MagicMock(spec=Image.Image)
        mock_image.save = MagicMock()
        mock_convert.return_value = [mock_image]

        pdf_bytes = b"fake pdf content"
        result = await converter.convert_pdf_bytes(pdf_bytes, temp_dir)

        assert isinstance(result, list)
        assert len(result) > 0

    # ====== 圖片增強測試 ======

    @patch("PIL.Image.open")
    @patch("PIL.ImageEnhance.Contrast")
    @patch("PIL.ImageEnhance.Sharpness")
    def test_enhance_image_quality(self, mock_sharpness, mock_contrast, mock_open, converter, temp_dir):
        """測試圖片品質增強"""
        # 建立模擬圖片
        mock_img = MagicMock(spec=Image.Image)
        mock_img.mode = "RGB"
        mock_img.save = MagicMock()
        mock_open.return_value = mock_img

        # 建立模擬的增強器
        mock_contrast_enhancer = MagicMock()
        mock_contrast_enhancer.enhance.return_value = mock_img
        mock_contrast.return_value = mock_contrast_enhancer

        mock_sharpness_enhancer = MagicMock()
        mock_sharpness_enhancer.enhance.return_value = mock_img
        mock_sharpness.return_value = mock_sharpness_enhancer

        image_path = Path(temp_dir) / "test.png"
        image_path.touch()

        result = converter.enhance_image_quality(str(image_path))

        # 應該返回增強後的圖片路徑
        assert "enhanced_" in result

    @patch("PIL.Image.open")
    def test_enhance_image_rgba_conversion(self, mock_open, converter, temp_dir):
        """測試RGBA圖片轉RGB"""
        # 建立RGBA模擬圖片
        mock_img = MagicMock(spec=Image.Image)
        mock_img.mode = "RGBA"
        mock_img.split.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_img.save = MagicMock()

        # 模擬轉換為RGB的圖片
        rgb_img = MagicMock(spec=Image.Image)
        rgb_img.mode = "RGB"
        rgb_img.filter.return_value = rgb_img
        rgb_img.save = MagicMock()

        mock_open.return_value = mock_img

        with patch.object(Image, "new", return_value=rgb_img):
            with patch("PIL.Image.Image.convert", return_value=rgb_img):
                image_path = Path(temp_dir) / "test.png"
                image_path.touch()

                result = converter.enhance_image_quality(str(image_path))
                assert result is not None

    # ====== 圖片裁剪測試 ======

    @patch("PIL.Image.open")
    @patch("PIL.ImageOps.invert")
    def test_crop_to_content(self, mock_invert, mock_open, converter, temp_dir):
        """測試圖片裁剪"""
        mock_img = MagicMock(spec=Image.Image)
        mock_img.mode = "RGB"
        mock_img.crop.return_value = mock_img
        mock_img.save = MagicMock()
        mock_open.return_value = mock_img

        mock_inverted = MagicMock()
        mock_inverted.getbbox.return_value = (10, 20, 790, 980)
        mock_invert.return_value = mock_inverted

        image_path = Path(temp_dir) / "test.png"
        image_path.touch()

        result = converter.crop_to_content(str(image_path))

        assert "cropped_" in result

    # ====== 頁數獲取測試 ======

    @patch("src.parsers.pdf_converter.convert_from_path")
    def test_get_pdf_page_count_fallback(self, mock_convert, converter, sample_pdf):
        """測試使用pdf2image的頁數獲取"""
        mock_images = [MagicMock(), MagicMock(), MagicMock()]
        mock_convert.return_value = mock_images

        page_count = converter.get_pdf_page_count(sample_pdf)

        assert page_count == 3

    @patch("src.parsers.pdf_converter.PdfReader")
    def test_get_pdf_page_count_pypdf2(self, mock_reader_class, converter, sample_pdf):
        """測試使用PyPDF2的頁數獲取"""
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock() for _ in range(5)]
        mock_reader_class.return_value = mock_reader

        page_count = converter.get_pdf_page_count(sample_pdf)

        assert page_count == 5

    # ====== 批量轉換測試 ======

    @pytest.mark.asyncio
    @patch("src.parsers.pdf_converter.convert_from_path")
    async def test_batch_conversion_success(self, mock_convert, converter, temp_dir):
        """測試批量PDF轉換成功"""
        # 建立多個測試PDF
        pdf_paths = []
        for i in range(3):
            pdf_path = Path(temp_dir) / f"test_{i}.pdf"
            pdf_path.touch()
            pdf_paths.append(str(pdf_path))

        # 模擬轉換結果
        mock_image = MagicMock(spec=Image.Image)
        mock_image.save = MagicMock()
        mock_convert.return_value = [mock_image]

        result = await converter.convert_multiple_pdfs(pdf_paths, temp_dir)

        assert isinstance(result, dict)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_batch_conversion_with_errors(self, converter, temp_dir):
        """測試批量轉換時的錯誤處理"""
        pdf_paths = [
            "/nonexistent/test1.pdf",
            "/nonexistent/test2.pdf",
        ]

        result = await converter.convert_multiple_pdfs(pdf_paths, temp_dir)

        # 應該返回字典，但轉換會失敗
        assert isinstance(result, dict)
        # 所有項目應該是空列表（轉換失敗）
        assert all(v == [] for v in result.values())

    # ====== 輸出目錄處理測試 ======

    @patch("src.parsers.pdf_converter.convert_from_path")
    def test_default_output_directory(self, mock_convert, converter, sample_pdf):
        """測試使用預設輸出目錄"""
        mock_image = MagicMock(spec=Image.Image)
        mock_image.save = MagicMock()
        mock_convert.return_value = [mock_image]

        # 不指定輸出目錄
        result = converter.convert_pdf_to_images_sync(sample_pdf)

        assert isinstance(result, list)
        # 圖片應該在臨時目錄中
        assert len(result) > 0

    @patch("src.parsers.pdf_converter.convert_from_path")
    def test_custom_output_directory(self, mock_convert, converter, sample_pdf, temp_dir):
        """測試自定義輸出目錄"""
        mock_image = MagicMock(spec=Image.Image)
        mock_image.save = MagicMock()
        mock_convert.return_value = [mock_image]

        result = converter.convert_pdf_to_images_sync(sample_pdf, temp_dir)

        assert isinstance(result, list)
        # 驗證圖片在指定目錄
        if result:
            assert temp_dir in result[0]

    # ====== 圖片命名測試 ======

    @patch("src.parsers.pdf_converter.convert_from_path")
    def test_image_naming_convention(self, mock_convert, converter, sample_pdf, temp_dir):
        """測試圖片檔案命名約定"""
        mock_images = [MagicMock(), MagicMock()]
        for img in mock_images:
            img.save = MagicMock()

        mock_convert.return_value = mock_images

        result = converter.convert_pdf_to_images_sync(sample_pdf, temp_dir)

        # 驗證命名格式: {pdf_name}_page_{number}.png
        for i, image_path in enumerate(result):
            assert f"_page_{i + 1}.png" in image_path

    # ====== 錯誤處理測試 ======

    @patch("src.parsers.pdf_converter.convert_from_path")
    def test_ocr_error_handling(self, mock_convert, converter, sample_pdf):
        """測試轉換錯誤處理"""
        mock_convert.side_effect = Exception("Conversion failed")

        with pytest.raises(Exception):
            converter.convert_pdf_to_images_sync(sample_pdf)

    @patch("PIL.Image.open")
    def test_enhancement_error_fallback(self, mock_open, converter, temp_dir):
        """測試增強失敗時的回退"""
        mock_open.side_effect = Exception("Image opening failed")

        image_path = Path(temp_dir) / "test.png"
        image_path.touch()

        # 應該返回原始路徑而不是失敗
        result = converter.enhance_image_quality(str(image_path))
        assert result == str(image_path)

    @patch("PIL.Image.open")
    def test_crop_error_fallback(self, mock_open, converter, temp_dir):
        """測試裁剪失敗時的回退"""
        mock_open.side_effect = Exception("Image opening failed")

        image_path = Path(temp_dir) / "test.png"
        image_path.touch()

        # 應該返回原始路徑而不是失敗
        result = converter.crop_to_content(str(image_path))
        assert result == str(image_path)
