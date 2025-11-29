"""Unit tests for PaddleOCR health report parser.

Tests regex patterns and extraction logic for:
- Patient information (age, gender, height, weight, BMI, ID)
- Vital signs (cholesterol, blood pressure, glucose, BMI)
- Lifestyle factors (smoking, exercise, alcohol)
- Test date extraction
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from src.parsers.paddle_ocr_parser import (
    PaddleOCRHealthReportParser,
    HealthMetric,
    ParsedHealthReport,
)

# Real image file provided by user
REAL_IMAGE_PATH = "S_91693062_0.jpg"

class TestPaddleOCRParser:
    """PaddleOCR解析器單元測試"""

    @pytest.fixture
    def parser(self):
        """建立Parser實例"""
        # Mock PaddleOCR class to prevent model loading
        with patch("src.parsers.paddle_ocr_parser.PaddleOCR"):
            return PaddleOCRHealthReportParser()

    # ====== 患者信息提取測試 ======

    def test_extract_age_chinese_format(self, parser):
        """測試中文年齡格式提取"""
        text_blocks = [{"text": "年齡：45", "confidence": 0.95}]
        patient_info = parser._extract_patient_info(text_blocks)
        assert patient_info["age"] == 45

    def test_extract_age_english_format(self, parser):
        """測試英文年齡格式提取"""
        text_blocks = [{"text": "Age: 45", "confidence": 0.95}]
        patient_info = parser._extract_patient_info(text_blocks)
        assert patient_info["age"] == 45

    def test_extract_age_year_format(self, parser):
        """測試歲數格式提取"""
        text_blocks = [{"text": "45歲", "confidence": 0.95}]
        patient_info = parser._extract_patient_info(text_blocks)
        assert patient_info["age"] == 45

    def test_extract_gender_male_chinese(self, parser):
        """測試中文男性性別提取"""
        text_blocks = [{"text": "性別：男", "confidence": 0.95}]
        patient_info = parser._extract_patient_info(text_blocks)
        assert patient_info["gender"] == "M"

    def test_extract_gender_female_chinese(self, parser):
        """測試中文女性性別提取"""
        text_blocks = [{"text": "性別：女", "confidence": 0.95}]
        patient_info = parser._extract_patient_info(text_blocks)
        assert patient_info["gender"] == "F"

    def test_extract_gender_english(self, parser):
        """測試英文性別提取"""
        text_blocks = [{"text": "Gender: Male", "confidence": 0.95}]
        patient_info = parser._extract_patient_info(text_blocks)
        assert patient_info["gender"] == "M"

    def test_extract_height(self, parser):
        """測試身高提取"""
        text_blocks = [{"text": "身高：170cm", "confidence": 0.95}]
        patient_info = parser._extract_patient_info(text_blocks)
        assert patient_info["height_cm"] == 170.0

    def test_extract_weight(self, parser):
        """測試體重提取"""
        text_blocks = [{"text": "體重：70kg", "confidence": 0.95}]
        patient_info = parser._extract_patient_info(text_blocks)
        assert patient_info["weight_kg"] == 70.0

    def test_calculate_bmi_from_height_weight(self, parser):
        """測試BMI計算（由身高和體重計算）"""
        text_blocks = [
            {"text": "身高：170cm", "confidence": 0.95},
            {"text": "體重：70kg", "confidence": 0.95},
        ]
        patient_info = parser._extract_patient_info(text_blocks)
        assert "bmi" in patient_info
        assert abs(patient_info["bmi"] - 24.2) < 0.1  # 70 / (1.7^2) ≈ 24.2

    def test_extract_bmi_direct(self, parser):
        """測試直接BMI提取"""
        text_blocks = [{"text": "BMI：24.2", "confidence": 0.95}]
        patient_info = parser._extract_patient_info(text_blocks)
        assert patient_info["bmi"] == 24.2

    def test_extract_taiwan_id(self, parser):
        """測試台灣身份證號提取"""
        text_blocks = [{"text": "身份證：A123456789", "confidence": 0.95}]
        patient_info = parser._extract_patient_info(text_blocks)
        assert patient_info["id_number"] == "A123456789"

    # ====== 血脂面板提取測試 ======

    def test_extract_total_cholesterol(self, parser):
        """測試總膽固醇提取"""
        text_blocks = [{"text": "總膽固醇：200", "confidence": 0.95}]
        vitals = parser._extract_vital_signs(text_blocks)
        assert "total_cholesterol" in vitals
        assert vitals["total_cholesterol"].value == 200.0

    def test_extract_ldl(self, parser):
        """測試LDL提取"""
        text_blocks = [{"text": "LDL-C：130", "confidence": 0.95}]
        vitals = parser._extract_vital_signs(text_blocks)
        assert "ldl_cholesterol" in vitals
        assert vitals["ldl_cholesterol"].value == 130.0

    def test_extract_hdl(self, parser):
        """測試HDL提取"""
        text_blocks = [{"text": "HDL-C：45", "confidence": 0.95}]
        vitals = parser._extract_vital_signs(text_blocks)
        assert "hdl_cholesterol" in vitals
        assert vitals["hdl_cholesterol"].value == 45.0

    def test_extract_triglycerides(self, parser):
        """測試三酸甘油酯提取"""
        text_blocks = [{"text": "三酸甘油酯：150", "confidence": 0.95}]
        vitals = parser._extract_vital_signs(text_blocks)
        assert "triglycerides" in vitals
        assert vitals["triglycerides"].value == 150.0

    # ====== 真實圖片模擬測試 ======

    @pytest.mark.asyncio
    async def test_parse_real_image_mocked(self, parser):
        """使用真實圖片路徑但Mock OCR結果進行測試"""
        # 模擬 OCR 結果，對應 S_91693062_0.jpg 可能的內容
        # 這裡我們手動構造一個符合該圖片內容的 OCR 輸出
        mock_ocr_result = [
            [
                [[[10, 10], [100, 10], [100, 30], [10, 30]], ("姓名：陳大文", 0.99)],
                [[[10, 40], [100, 40], [100, 60], [10, 60]], ("性別：男", 0.98)],
                [[[10, 70], [100, 70], [100, 90], [10, 90]], ("年齡：45歲", 0.97)],
                [[[10, 100], [200, 100], [200, 120], [10, 120]], ("檢查日期：2023/10/25", 0.96)],
                [[[10, 130], [150, 130], [150, 150], [10, 150]], ("總膽固醇 210 mg/dL", 0.95)],
                [[[10, 160], [150, 160], [150, 180], [10, 180]], ("三酸甘油酯 160 mg/dL", 0.94)],
                [[[10, 190], [150, 190], [150, 210], [10, 210]], ("空腹血糖 95 mg/dL", 0.93)],
            ]
        ]
        
        # Mock predict method
        parser.ocr.predict = MagicMock(return_value=mock_ocr_result)
        
        # Mock Image.open to avoid actual file I/O if file doesn't exist, 
        # but since user said file exists, we can let it try or mock it for speed.
        # Let's mock it to be safe and fast.
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (1000, 1000) # Valid size
            mock_open.return_value = mock_img
            
            # Mock os.path.exists to return True for our fake file
            with patch("pathlib.Path.exists", return_value=True):
                result = await parser.parse(REAL_IMAGE_PATH)
                
                assert result.confidence_score > 0.9
                assert result.patient_info["name"] == "陳大文"
                assert result.patient_info["gender"] == "M"
                assert result.patient_info["age"] == 45
                assert result.test_date == "2023-10-25"
                
                # Check vitals
                assert "total_cholesterol" in result.vital_signs
                assert result.vital_signs["total_cholesterol"].value == 210.0
                assert "triglycerides" in result.vital_signs
                assert result.vital_signs["triglycerides"].value == 160.0
                assert "fasting_glucose" in result.vital_signs
                assert result.vital_signs["fasting_glucose"].value == 95.0


    def test_extract_total_cholesterol(self, parser):
        """測試總膽固醇提取"""
        text_blocks = [{"text": "總膽固醇：180", "confidence": 0.95}]
        vital_signs = parser._extract_vital_signs(text_blocks)
        assert "total_cholesterol" in vital_signs
        assert vital_signs["total_cholesterol"].value == 180.0
        assert vital_signs["total_cholesterol"].unit == "mg/dL"

    def test_extract_ldl_cholesterol(self, parser):
        """測試LDL膽固醇提取"""
        text_blocks = [{"text": "LDL膽固醇：120", "confidence": 0.95}]
        vital_signs = parser._extract_vital_signs(text_blocks)
        assert "ldl_cholesterol" in vital_signs
        assert vital_signs["ldl_cholesterol"].value == 120.0

    def test_extract_hdl_cholesterol(self, parser):
        """測試HDL膽固醇提取"""
        text_blocks = [{"text": "HDL膽固醇：50", "confidence": 0.95}]
        vital_signs = parser._extract_vital_signs(text_blocks)
        assert "hdl_cholesterol" in vital_signs
        assert vital_signs["hdl_cholesterol"].value == 50.0

    def test_extract_triglycerides(self, parser):
        """測試三酸甘油酯提取"""
        text_blocks = [{"text": "三酸甘油酯：150", "confidence": 0.95}]
        vital_signs = parser._extract_vital_signs(text_blocks)
        assert "triglycerides" in vital_signs
        assert vital_signs["triglycerides"].value == 150.0

    # ====== 血壓提取測試 ======

    def test_extract_blood_pressure(self, parser):
        """測試血壓提取"""
        text_blocks = [{"text": "血壓：130/85", "confidence": 0.95}]
        vital_signs = parser._extract_vital_signs(text_blocks)
        assert "systolic_bp" in vital_signs
        assert vital_signs["systolic_bp"].value == 130.0
        assert "diastolic_bp" in vital_signs
        assert vital_signs["diastolic_bp"].value == 85.0

    def test_extract_blood_pressure_slash_format(self, parser):
        """測試血壓斜線格式提取"""
        text_blocks = [{"text": "BP: 120/80", "confidence": 0.95}]
        vital_signs = parser._extract_vital_signs(text_blocks)
        assert vital_signs["systolic_bp"].value == 120.0
        assert vital_signs["diastolic_bp"].value == 80.0

    # ====== 血糖代謝提取測試 ======

    def test_extract_fasting_glucose(self, parser):
        """測試空腹血糖提取"""
        text_blocks = [{"text": "空腹血糖：100", "confidence": 0.95}]
        vital_signs = parser._extract_vital_signs(text_blocks)
        assert "fasting_glucose" in vital_signs
        assert vital_signs["fasting_glucose"].value == 100.0

    def test_extract_hba1c(self, parser):
        """測試HbA1c提取"""
        text_blocks = [{"text": "HbA1c：6.5", "confidence": 0.95}]
        vital_signs = parser._extract_vital_signs(text_blocks)
        assert "hba1c" in vital_signs
        assert vital_signs["hba1c"].value == 6.5

    # ====== 腰圍提取測試 ======

    def test_extract_waist_circumference(self, parser):
        """測試腰圍提取"""
        text_blocks = [{"text": "腰圍：90", "confidence": 0.95}]
        vital_signs = parser._extract_vital_signs(text_blocks)
        assert "waist_circumference" in vital_signs
        assert vital_signs["waist_circumference"].value == 90.0

    # ====== 生活方式因素提取測試 ======

    def test_extract_smoking_current(self, parser):
        """測試當前吸菸狀態提取"""
        text_blocks = [{"text": "吸菸：是", "confidence": 0.95}]
        lifestyle = parser._extract_lifestyle_factors(text_blocks)
        assert lifestyle["smoking_status"] == "current"

    def test_extract_smoking_never(self, parser):
        """測試從不吸菸狀態提取"""
        text_blocks = [{"text": "吸菸：否", "confidence": 0.95}]
        lifestyle = parser._extract_lifestyle_factors(text_blocks)
        assert lifestyle["smoking_status"] == "never"

    def test_extract_smoking_english(self, parser):
        """測試英文吸菸狀態提取"""
        text_blocks = [{"text": "Current smoker", "confidence": 0.95}]
        lifestyle = parser._extract_lifestyle_factors(text_blocks)
        assert lifestyle["smoking_status"] == "current"

    def test_extract_exercise_frequency(self, parser):
        """測試運動頻率提取"""
        text_blocks = [{"text": "運動：每週3次", "confidence": 0.95}]
        lifestyle = parser._extract_lifestyle_factors(text_blocks)
        assert lifestyle["exercise_frequency"] == 3
        assert lifestyle["exercise_period"] == "weekly"

    def test_extract_alcohol_consumption(self, parser):
        """測試酒精消費提取"""
        text_blocks = [{"text": "飲酒量：2杯", "confidence": 0.95}]
        lifestyle = parser._extract_lifestyle_factors(text_blocks)
        assert lifestyle["drinks_per_week"] == 2.0

    # ====== 日期提取測試 ======

    def test_extract_date_chinese_format(self, parser):
        """測試中文日期格式提取"""
        text_blocks = [{"text": "檢查日期：2024年11月15日", "confidence": 0.95}]
        date = parser._extract_test_date(text_blocks)
        assert date == "2024-11-15"

    def test_extract_date_slash_format(self, parser):
        """測試斜線日期格式提取"""
        text_blocks = [{"text": "Date: 2024/11/15", "confidence": 0.95}]
        date = parser._extract_test_date(text_blocks)
        assert date == "2024-11-15"

    def test_extract_date_minguo_format(self, parser):
        """測試民國日期格式提取並轉換"""
        text_blocks = [{"text": "檢查日期：113年11月15日", "confidence": 0.95}]
        date = parser._extract_test_date(text_blocks)
        # 民國113年 = 西曆2024年
        assert date == "2024-11-15"

    # ====== 風險評估測試 ======

    def test_assess_cholesterol_normal(self, parser):
        """測試膽固醇正常風險評估"""
        risk = parser._assess_cholesterol_risk(180)
        assert risk == "normal"

    def test_assess_cholesterol_borderline(self, parser):
        """測試膽固醇邊界風險評估"""
        risk = parser._assess_cholesterol_risk(220)
        assert risk == "borderline"

    def test_assess_cholesterol_high(self, parser):
        """測試膽固醇高風險評估"""
        risk = parser._assess_cholesterol_risk(250)
        assert risk == "high"

    def test_assess_ldl_normal(self, parser):
        """測試LDL正常風險評估"""
        risk = parser._assess_ldl_risk(80)
        assert risk == "normal"

    def test_assess_ldl_high(self, parser):
        """測試LDL高風險評估"""
        risk = parser._assess_ldl_risk(180)
        assert risk == "high"

    def test_assess_systolic_bp_normal(self, parser):
        """測試收縮壓正常風險評估"""
        risk = parser._assess_systolic_bp_risk(110)
        assert risk == "normal"

    def test_assess_systolic_bp_stage1(self, parser):
        """測試收縮壓第一階段風險評估"""
        risk = parser._assess_systolic_bp_risk(135)
        assert risk == "stage1"

    def test_assess_systolic_bp_high(self, parser):
        """測試收縮壓高風險評估"""
        risk = parser._assess_systolic_bp_risk(145)
        assert risk == "high"

    def test_assess_fasting_glucose_normal(self, parser):
        """測試空腹血糖正常風險評估"""
        risk = parser._assess_fasting_glucose_risk(90)
        assert risk == "normal"

    def test_assess_fasting_glucose_borderline(self, parser):
        """測試空腹血糖邊界風險評估"""
        risk = parser._assess_fasting_glucose_risk(110)
        assert risk == "borderline"

    def test_assess_fasting_glucose_high(self, parser):
        """測試空腹血糖高風險評估"""
        risk = parser._assess_fasting_glucose_risk(130)
        assert risk == "high"

    # ====== 文字正規化測試 ======

    def test_normalize_fullwidth_numbers(self, parser):
        """測試全形數字轉換"""
        text = "年齡：４５"
        normalized = parser._normalize_text(text)
        assert "45" in normalized

    def test_normalize_fullwidth_colon(self, parser):
        """測試全形冒號轉換"""
        text = "年齡：45"
        normalized = parser._normalize_text(text)
        assert "年齡:45" in normalized

    def test_normalize_whitespace(self, parser):
        """測試空白正規化"""
        text = "年齡  :  45"
        normalized = parser._normalize_text(text)
        # 應該消除多餘空白
        assert normalized.count(" ") < text.count(" ")

    # ====== 資料結構測試 ======

    def test_health_metric_creation(self):
        """測試HealthMetric建立"""
        metric = HealthMetric(
            name="Total Cholesterol",
            value=180.0,
            unit="mg/dL",
            reference_range="<200",
            risk_level="normal",
        )
        assert metric.name == "Total Cholesterol"
        assert metric.value == 180.0
        assert metric.risk_level == "normal"

    def test_parsed_health_report_to_dict(self):
        """測試ParsedHealthReport轉字典"""
        metric = HealthMetric(
            name="Total Cholesterol",
            value=180.0,
            unit="mg/dL",
        )
        report = ParsedHealthReport(
            patient_info={"age": 45},
            vital_signs={"total_cholesterol": metric},
            test_date="2024-11-15",
        )

        report_dict = report.to_dict()
        assert report_dict["patient_info"]["age"] == 45
        assert report_dict["test_date"] == "2024-11-15"
        assert "total_cholesterol" in report_dict["vital_signs"]

    # ====== 整合測試 ======

    def test_extract_complex_report(self, parser):
        """測試複雜報告提取"""
        text_blocks = [
            {"text": "年齡：45", "confidence": 0.95},
            {"text": "性別：男", "confidence": 0.95},
            {"text": "身高：170cm", "confidence": 0.95},
            {"text": "體重：70kg", "confidence": 0.95},
            {"text": "總膽固醇：200", "confidence": 0.95},
            {"text": "血壓：130/85", "confidence": 0.95},
            {"text": "空腹血糖：100", "confidence": 0.95},
            {"text": "吸菸：否", "confidence": 0.95},
            {"text": "檢查日期：2024年11月15日", "confidence": 0.95},
        ]

        patient_info = parser._extract_patient_info(text_blocks)
        vital_signs = parser._extract_vital_signs(text_blocks)
        lifestyle = parser._extract_lifestyle_factors(text_blocks)
        date = parser._extract_test_date(text_blocks)

        assert patient_info["age"] == 45
        assert patient_info["gender"] == "M"
        assert vital_signs["total_cholesterol"].value == 200.0
        assert vital_signs["systolic_bp"].value == 130.0
        assert lifestyle["smoking_status"] == "never"
        assert date == "2024-11-15"
