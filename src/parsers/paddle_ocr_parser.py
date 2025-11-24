"""PaddleOCR-based health report parser.

本模組提供基於PaddleOCR的健康檢查報告解析功能，支持傳統中文和英文。
提取生理指標、患者信息和生活方式因素。

Supports:
- Vital signs extraction (cholesterol, blood pressure, glucose, BMI, etc.)
- Patient information (age, gender, report date)
- Lifestyle factors (smoking, physical activity, alcohol consumption)
- Traditional Chinese and English text
"""

import asyncio
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from paddleocr import PaddleOCR
from PIL import Image
import numpy as np

from ..utils.logger import AgentLogger


@dataclass
class HealthMetric:
    """單一健康指標的結構化表示

    Represents a single health metric with value and unit.
    """
    name: str
    value: float
    unit: str
    reference_range: Optional[str] = None
    risk_level: str = "unknown"  # normal, borderline, high, critical


@dataclass
class ParsedHealthReport:
    """解析後的完整健康檢查報告

    Complete parsed health report with all extracted information.
    """
    patient_info: Dict[str, Any] = field(default_factory=dict)
    vital_signs: Dict[str, HealthMetric] = field(default_factory=dict)
    lifestyle_factors: Dict[str, Any] = field(default_factory=dict)
    test_date: Optional[str] = None
    raw_text: str = ""
    confidence_score: float = 0.0
    parsing_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式供後續處理

        Convert to dictionary for downstream processing.
        """
        return {
            "patient_info": self.patient_info,
            "vital_signs": {
                k: {
                    "name": v.name,
                    "value": v.value,
                    "unit": v.unit,
                    "reference_range": v.reference_range,
                    "risk_level": v.risk_level,
                }
                for k, v in self.vital_signs.items()
            },
            "lifestyle_factors": self.lifestyle_factors,
            "test_date": self.test_date,
            "confidence_score": self.confidence_score,
            "parsing_errors": self.parsing_errors,
        }


class PaddleOCRHealthReportParser:
    """基於PaddleOCR的健康檢查報告解析器

    Parses health reports from images using PaddleOCR.
    Supports Traditional Chinese and English text extraction.

    Attributes:
        ocr: PaddleOCR instance configured for Traditional Chinese
        logger: Structured logger for tracing
    """

    # ========================================================================
    # 初始化與配置 (Initialization & Configuration)
    # ========================================================================

    def __init__(self, language: str = "chinese_cht", device: str = "cpu"):
        """初始化PaddleOCR解析器

        Initialize PaddleOCR parser with Traditional Chinese & English support.

        Args:
            language: OCR語言設置 ('chinese_cht' for Traditional Chinese + English,
                                  'ch' for Simplified Chinese, 'en' for English only)
            device: 運算設備 ('cpu' or 'gpu')

        Note:
            'chinese_cht' model can recognize Traditional Chinese, English, and numbers.
            This is ideal for Taiwan health reports which mix Chinese and English.
        """
        self.language = language
        self.device = device
        self.logger = AgentLogger("PaddleOCRParser")

        # 初始化PaddleOCR (Traditional Chinese + English)
        try:
            self.ocr = PaddleOCR(
                use_textline_orientation=True,  # Updated from deprecated use_angle_cls
                lang=language,
                # Note: PaddleOCR 3.x+ uses CPU by default, no use_gpu parameter needed
            )
            self.logger.info("PaddleOCR initialized", language=language, device=device)
        except Exception as e:
            self.logger.error("Failed to initialize PaddleOCR", error=str(e))
            raise

    # ========================================================================
    # 主要解析方法 (Main Parsing Methods)
    # ========================================================================

    async def parse(self, image_path: str) -> ParsedHealthReport:
        """異步解析單張圖片的健康檢查報告

        Asynchronously parse a health report image.

        Args:
            image_path: 圖片檔案路徑 (Image file path)

        Returns:
            ParsedHealthReport 包含所有提取的信息

        Raises:
            FileNotFoundError: 如果圖片不存在
            ValueError: 如果圖片無法被解析
        """
        # 驗證圖片存在
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        try:
            # 在執行緒池中運行OCR以避免阻斷
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._perform_ocr, image_path
            )

            if result is None:
                raise ValueError(f"OCR failed to process: {image_path}")

            # 提取文字和信心度
            text_blocks, confidence = self._extract_text_and_confidence(result)

            # 組合提取的信息
            report = ParsedHealthReport(
                raw_text="\n".join([block["text"] for block in text_blocks]),
                confidence_score=confidence,
            )

            # 解析各部分資訊
            report.patient_info = self._extract_patient_info(text_blocks)
            report.vital_signs = self._extract_vital_signs(text_blocks)
            report.lifestyle_factors = self._extract_lifestyle_factors(text_blocks)
            report.test_date = self._extract_test_date(text_blocks)

            self.logger.info(
                "Successfully parsed health report",
                metrics_count=len(report.vital_signs),
                confidence=confidence,
            )

            return report

        except Exception as e:
            self.logger.error("Error parsing health report", error=str(e))
            raise

    async def parse_batch(self, image_paths: List[str]) -> List[ParsedHealthReport]:
        """批量異步解析多張圖片

        Batch parse multiple health report images.

        Args:
            image_paths: 圖片檔案路徑列表 (List of image file paths)

        Returns:
            ParsedHealthReport 列表 (List of parsed reports)
        """
        tasks = [self.parse(image_path) for image_path in image_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理異常
        parsed_reports = []
        for image_path, result in zip(image_paths, results):
            if isinstance(result, Exception):
                self.logger.error(
                    "Failed to parse image in batch",
                    image_path=image_path,
                    error=str(result),
                )
            else:
                parsed_reports.append(result)

        return parsed_reports

    # ========================================================================
    # OCR執行 (OCR Execution)
    # ========================================================================

    def _perform_ocr(self, image_path: str) -> Optional[List]:
        """執行實際的OCR識別

        Perform actual OCR recognition on image.

        Args:
            image_path: 圖片檔案路徑 (Image file path)

        Returns:
            OCR 結果 (PaddleOCR result or None if failed)
        """
        try:
            # 檢查圖片格式並驗證
            img = Image.open(image_path)

            # 如果圖片太小，可能無法識別
            if img.size[0] < 100 or img.size[1] < 100:
                self.logger.warning(
                    "Image too small for reliable OCR",
                    width=img.size[0],
                    height=img.size[1],
                )

            # 執行OCR (新版 PaddleOCR 使用 predict() 方法)
            result = self.ocr.predict(image_path)
            return result

        except Exception as e:
            self.logger.error("OCR execution failed", error=str(e))
            return None

    def _extract_text_and_confidence(self, ocr_result: List) -> Tuple[List[Dict], float]:
        """從OCR結果中提取文字和平均信心度

        Extract text blocks and confidence score from OCR result.

        Args:
            ocr_result: PaddleOCR 原始結果 (Raw PaddleOCR result)

        Returns:
            Tuple of (text_blocks, average_confidence)
        """
        text_blocks = []
        confidences = []

        if not ocr_result or len(ocr_result) == 0:
            return text_blocks, 0.0

        # 提取所有頁面的文字
        for page in ocr_result:
            if page is None:
                continue

            for line in page:
                if len(line) < 2:
                    continue

                # line[0] 是邊界框座標，line[1] 是 (文字, 信心度)
                text = line[1][0]
                confidence = line[1][1]

                text_blocks.append({
                    "text": text,
                    "confidence": confidence,
                })
                confidences.append(confidence)

        # 計算平均信心度
        avg_confidence = np.mean(confidences) if confidences else 0.0

        return text_blocks, float(avg_confidence)

    # ========================================================================
    # 患者信息提取 (Patient Information Extraction)
    # ========================================================================

    def _extract_patient_info(self, text_blocks: List[Dict]) -> Dict[str, Any]:
        """提取患者個人資訊

        Extract patient information like age, gender, name, ID.

        Args:
            text_blocks: 文字區塊列表 (List of text blocks from OCR)

        Returns:
            患者信息字典 (Patient information dictionary)
        """
        text = self._normalize_text("\n".join([b["text"] for b in text_blocks]))
        patient_info = {}

        # ====== 年齡 (Age) ======
        # 台灣醫院常見格式: "年齡:45" 或 "Age: 45" 或 "45歲"
        age_patterns = [
            r"年齡\s*[:：]\s*(\d+)",  # 年齡: 45
            r"age\s*[:：]\s*(\d+)",   # Age: 45 (case-insensitive)
            r"(\d+)\s*歲",             # 45歲
        ]

        for pattern in age_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                patient_info["age"] = int(match.group(1))
                break

        # ====== 性別 (Gender) ======
        # 格式: "性別:男" 或 "Gender: Female" 或 "M/F"
        if re.search(r"性別\s*[:：]\s*[男M]", text, re.IGNORECASE):
            patient_info["gender"] = "M"
        elif re.search(r"性別\s*[:：]\s*[女F]", text, re.IGNORECASE):
            patient_info["gender"] = "F"
        elif re.search(r"Male|男性|男", text, re.IGNORECASE):
            patient_info["gender"] = "M"
        elif re.search(r"Female|女性|女", text, re.IGNORECASE):
            patient_info["gender"] = "F"

        # ====== 身高 (Height) ======
        # 格式: "身高: 170cm" 或 "Height: 170 cm"
        height_patterns = [
            r"身高\s*[:：]\s*(\d+(?:\.\d+)?)\s*cm",
            r"height\s*[:：]\s*(\d+(?:\.\d+)?)\s*cm",
        ]

        for pattern in height_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                patient_info["height_cm"] = float(match.group(1))
                break

        # ====== 體重 (Weight) ======
        # 格式: "體重: 70kg" 或 "Weight: 70 kg"
        weight_patterns = [
            r"體重\s*[:：]\s*(\d+(?:\.\d+)?)\s*kg",
            r"weight\s*[:：]\s*(\d+(?:\.\d+)?)\s*kg",
        ]

        for pattern in weight_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                patient_info["weight_kg"] = float(match.group(1))
                break

        # ====== BMI ======
        # 格式: "BMI: 24.2" 或 "BMI: 24.2 kg/m²"
        bmi_patterns = [
            r"BMI\s*[:：]\s*(\d+(?:\.\d+)?)",
        ]

        for pattern in bmi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                patient_info["bmi"] = float(match.group(1))
                break

        # 計算BMI如果有身高和體重但沒有BMI
        if "height_cm" in patient_info and "weight_kg" in patient_info and "bmi" not in patient_info:
            height_m = patient_info["height_cm"] / 100
            bmi = patient_info["weight_kg"] / (height_m ** 2)
            patient_info["bmi"] = round(bmi, 1)

        # ====== 患者姓名 (Patient Name) ======
        # 格式: "姓名:王小明" 或 "Name: John Doe"
        name_patterns = [
            r"姓名\s*[:：]\s*([^\n]+)",
            r"name\s*[:：]\s*([^\n]+)",
        ]

        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 0 and len(name) < 50:  # 合理的名字長度
                    patient_info["name"] = name
                break

        # ====== 身份證號 (ID Number) ======
        # 台灣身份證號格式: 1個大寫字母 + 9個數字
        id_pattern = r"([A-Z]\d{9})"
        match = re.search(id_pattern, text)
        if match:
            patient_info["id_number"] = match.group(1)

        return patient_info

    # ========================================================================
    # 生理指標提取 (Vital Signs Extraction)
    # ========================================================================

    def _extract_vital_signs(self, text_blocks: List[Dict]) -> Dict[str, HealthMetric]:
        """提取生理指標 (血脂、血壓、血糖、BMI等)

        Extract vital signs including:
        - Cholesterol (total, LDL, HDL, triglycerides)
        - Blood pressure (systolic, diastolic)
        - Glucose metrics (fasting glucose, HbA1c)
        - Anthropometry (BMI, waist circumference)

        Args:
            text_blocks: 文字區塊列表 (List of text blocks from OCR)

        Returns:
            健康指標字典 (Dictionary of HealthMetric objects)
        """
        text = self._normalize_text("\n".join([b["text"] for b in text_blocks]))
        vital_signs = {}

        # ====== 血脂面板 (Lipid Panel) ======

        # 總膽固醇 (Total Cholesterol)
        tc_patterns = [
            r"總膽固醇\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"total\s+cholesterol\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"TC\s*[:：]\s*(\d+(?:\.\d+)?)",
        ]
        for pattern in tc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                vital_signs["total_cholesterol"] = HealthMetric(
                    name="Total Cholesterol",
                    value=value,
                    unit="mg/dL",
                    reference_range="<200",
                    risk_level=self._assess_cholesterol_risk(value),
                )
                break

        # LDL膽固醇 (Low-Density Lipoprotein)
        ldl_patterns = [
            r"LDL\s*[-:：]\s*(?:膽固醇)?\s*(\d+(?:\.\d+)?)",
            r"ldl\s+cholesterol\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"低密度脂蛋白\s*[:：]\s*(\d+(?:\.\d+)?)",
        ]
        for pattern in ldl_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                vital_signs["ldl_cholesterol"] = HealthMetric(
                    name="LDL Cholesterol",
                    value=value,
                    unit="mg/dL",
                    reference_range="<100",
                    risk_level=self._assess_ldl_risk(value),
                )
                break

        # HDL膽固醇 (High-Density Lipoprotein)
        hdl_patterns = [
            r"HDL\s*[-:：]\s*(?:膽固醇)?\s*(\d+(?:\.\d+)?)",
            r"hdl\s+cholesterol\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"高密度脂蛋白\s*[:：]\s*(\d+(?:\.\d+)?)",
        ]
        for pattern in hdl_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                vital_signs["hdl_cholesterol"] = HealthMetric(
                    name="HDL Cholesterol",
                    value=value,
                    unit="mg/dL",
                    reference_range=">40 (men), >50 (women)",
                    risk_level=self._assess_hdl_risk(value),
                )
                break

        # 三酸甘油酯 (Triglycerides)
        triglyceride_patterns = [
            r"三酸甘油酯\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"triglycerides?\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"TG\s*[:：]\s*(\d+(?:\.\d+)?)",
        ]
        for pattern in triglyceride_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                vital_signs["triglycerides"] = HealthMetric(
                    name="Triglycerides",
                    value=value,
                    unit="mg/dL",
                    reference_range="<150",
                    risk_level=self._assess_triglyceride_risk(value),
                )
                break

        # ====== 血壓 (Blood Pressure) ======

        # 收縮壓和舒張壓 (Systolic and Diastolic)
        bp_patterns = [
            r"血壓\s*[:：]\s*(\d+)\s*[/\\]\s*(\d+)",
            r"blood\s+pressure\s*[:：]\s*(\d+)\s*[/\\]\s*(\d+)",
            r"BP\s*[:：]\s*(\d+)\s*[/\\]\s*(\d+)",
        ]
        for pattern in bp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                systolic = float(match.group(1))
                diastolic = float(match.group(2))

                vital_signs["systolic_bp"] = HealthMetric(
                    name="Systolic Blood Pressure",
                    value=systolic,
                    unit="mmHg",
                    reference_range="<120",
                    risk_level=self._assess_systolic_bp_risk(systolic),
                )

                vital_signs["diastolic_bp"] = HealthMetric(
                    name="Diastolic Blood Pressure",
                    value=diastolic,
                    unit="mmHg",
                    reference_range="<80",
                    risk_level=self._assess_diastolic_bp_risk(diastolic),
                )
                break

        # ====== 血糖代謝 (Glucose Metabolism) ======

        # 空腹血糖 (Fasting Glucose)
        fasting_glucose_patterns = [
            r"空腹血糖\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"fasting\s+glucose\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"AC\s*[:：]\s*(\d+(?:\.\d+)?)",
        ]
        for pattern in fasting_glucose_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                vital_signs["fasting_glucose"] = HealthMetric(
                    name="Fasting Glucose",
                    value=value,
                    unit="mg/dL",
                    reference_range="<100",
                    risk_level=self._assess_fasting_glucose_risk(value),
                )
                break

        # HbA1c (糖化血紅蛋白)
        hba1c_patterns = [
            r"HbA1c\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"glycated\s+hemoglobin\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"糖化血紅蛋白\s*[:：]\s*(\d+(?:\.\d+)?)",
        ]
        for pattern in hba1c_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                vital_signs["hba1c"] = HealthMetric(
                    name="HbA1c",
                    value=value,
                    unit="%",
                    reference_range="<5.7",
                    risk_level=self._assess_hba1c_risk(value),
                )
                break

        # ====== 人體測量 (Anthropometry) ======

        # 腰圍 (Waist Circumference)
        waist_patterns = [
            r"腰圍\s*[:：]\s*(\d+(?:\.\d+)?)",
            r"waist\s+circumference\s*[:：]\s*(\d+(?:\.\d+)?)",
        ]
        for pattern in waist_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                vital_signs["waist_circumference"] = HealthMetric(
                    name="Waist Circumference",
                    value=value,
                    unit="cm",
                    reference_range="<90 (men), <80 (women)",
                    risk_level=self._assess_waist_risk(value),
                )
                break

        return vital_signs

    # ========================================================================
    # 生活型態因素提取 (Lifestyle Factors Extraction)
    # ========================================================================

    def _extract_lifestyle_factors(self, text_blocks: List[Dict]) -> Dict[str, Any]:
        """提取生活方式相關信息

        Extract lifestyle factors including smoking, physical activity, alcohol consumption.

        Args:
            text_blocks: 文字區塊列表 (List of text blocks from OCR)

        Returns:
            生活型態字典 (Lifestyle factors dictionary)
        """
        text = self._normalize_text("\n".join([b["text"] for b in text_blocks]))
        lifestyle_factors = {}

        # ====== 吸菸狀況 (Smoking Status) ======
        # 可能的格式: "吸菸:是" 或 "Smoking: Yes" 或 "Current smoker"
        if re.search(r"吸菸|抽菸|smoking", text, re.IGNORECASE):
            if re.search(r"吸菸\s*[:：]\s*是|current\s+smoker|正在吸菸", text, re.IGNORECASE):
                lifestyle_factors["smoking_status"] = "current"
            elif re.search(r"吸菸\s*[:：]\s*否|never\s+smoked|從不吸菸", text, re.IGNORECASE):
                lifestyle_factors["smoking_status"] = "never"
            elif re.search(r"former\s+smoker|曾經吸菸|戒菸", text, re.IGNORECASE):
                lifestyle_factors["smoking_status"] = "former"

        # ====== 身體活動 (Physical Activity) ======
        # 可能的格式: "運動:每週3次" 或 "Exercise: 3 times per week"
        activity_patterns = [
            r"運動\s*[:：]\s*(.+?)(?=\n|$)",
            r"exercise\s*[:：]\s*(.+?)(?=\n|$)",
            r"physical\s+activity\s*[:：]\s*(.+?)(?=\n|$)",
        ]

        for pattern in activity_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                activity_text = match.group(1).strip()

                # 嘗試提取頻率 (每週/每月的次數)
                freq_match = re.search(r"(\d+)\s*次", activity_text)
                if freq_match:
                    lifestyle_factors["exercise_frequency"] = int(freq_match.group(1))

                # 嘗試提取時間單位
                if re.search(r"週|week", activity_text, re.IGNORECASE):
                    lifestyle_factors["exercise_period"] = "weekly"
                elif re.search(r"月|month", activity_text, re.IGNORECASE):
                    lifestyle_factors["exercise_period"] = "monthly"
                elif re.search(r"天|day", activity_text, re.IGNORECASE):
                    lifestyle_factors["exercise_period"] = "daily"

                lifestyle_factors["exercise_description"] = activity_text
                break

        # ====== 酒精消費 (Alcohol Consumption) ======
        # 可能的格式: "飲酒:否" 或 "Alcohol: No" 或 "Drinks per week: 0"
        alcohol_patterns = [
            r"飲酒|飲酒量|alcohol",
        ]

        for pattern in alcohol_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # 查找飲酒頻率/量
                quantity_match = re.search(
                    r"飲酒[量：:]\s*(\d+(?:\.\d+)?)\s*(?:杯|盞|次|drinks?)?|"
                    r"alcohol\s*[:：]\s*(\d+(?:\.\d+)?)\s*(?:drinks?)?",
                    text,
                    re.IGNORECASE
                )

                if quantity_match:
                    quantity = float(quantity_match.group(1) or quantity_match.group(2))
                    lifestyle_factors["drinks_per_week"] = quantity

                # 查找是否飲酒
                if re.search(r"飲酒\s*[:：]\s*是|drinks?\s*[:：]\s*yes|regular\s+drinker", text, re.IGNORECASE):
                    lifestyle_factors["alcohol_consumption"] = "yes"
                elif re.search(r"飲酒\s*[:：]\s*否|drinks?\s*[:：]\s*no|non.?drinker", text, re.IGNORECASE):
                    lifestyle_factors["alcohol_consumption"] = "no"
                break

        return lifestyle_factors

    # ========================================================================
    # 檢查日期提取 (Test Date Extraction)
    # ========================================================================

    def _extract_test_date(self, text_blocks: List[Dict]) -> Optional[str]:
        """提取健康檢查報告的日期

        Extract the test date from health report.

        Args:
            text_blocks: 文字區塊列表 (List of text blocks from OCR)

        Returns:
            日期字符串 (Date string in YYYY-MM-DD format or None)
        """
        text = self._normalize_text("\n".join([b["text"] for b in text_blocks]))

        # 台灣常見日期格式
        date_patterns = [
            # 民國格式: 113年11月15日
            r"(\d{2,3})年(\d{1,2})月(\d{1,2})日",
            # 西曆格式: 2024年11月15日 或 2024/11/15
            r"(202\d)年(\d{1,2})月(\d{1,2})日",
            r"(202\d)[/\-](\d{1,2})[/\-](\d{1,2})",
            # 英文格式: Nov 15, 2024 或 15 November 2024
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(202\d)",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()

                # 處理民國格式
                if len(groups[0]) <= 3 and int(groups[0]) < 200:
                    # 民國轉西曆 (add 1911)
                    year = int(groups[0]) + 1911
                    month = int(groups[1])
                    day = int(groups[2])
                else:
                    year = int(groups[0])
                    month = int(groups[1])
                    day = int(groups[2])

                try:
                    date_obj = datetime(year, month, day)
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    # 無效的日期，繼續嘗試下一個模式
                    continue

        return None

    # ========================================================================
    # 風險評估方法 (Risk Assessment Methods)
    # ========================================================================

    def _assess_cholesterol_risk(self, value: float) -> str:
        """評估總膽固醇風險等級"""
        if value < 200:
            return "normal"
        elif value < 240:
            return "borderline"
        else:
            return "high"

    def _assess_ldl_risk(self, value: float) -> str:
        """評估LDL膽固醇風險等級"""
        if value < 100:
            return "normal"
        elif value < 130:
            return "borderline"
        elif value < 160:
            return "borderline_high"
        else:
            return "high"

    def _assess_hdl_risk(self, value: float) -> str:
        """評估HDL膽固醇風險等級 (higher is better)"""
        if value >= 60:
            return "normal"
        elif value >= 40:
            return "borderline"
        else:
            return "high"

    def _assess_triglyceride_risk(self, value: float) -> str:
        """評估三酸甘油酯風險等級"""
        if value < 150:
            return "normal"
        elif value < 200:
            return "borderline"
        else:
            return "high"

    def _assess_systolic_bp_risk(self, value: float) -> str:
        """評估收縮壓風險等級"""
        if value < 120:
            return "normal"
        elif value < 130:
            return "elevated"
        elif value < 140:
            return "stage1"
        else:
            return "high"

    def _assess_diastolic_bp_risk(self, value: float) -> str:
        """評估舒張壓風險等級"""
        if value < 80:
            return "normal"
        elif value < 90:
            return "stage1"
        else:
            return "high"

    def _assess_fasting_glucose_risk(self, value: float) -> str:
        """評估空腹血糖風險等級"""
        if value < 100:
            return "normal"
        elif value < 126:
            return "borderline"
        else:
            return "high"

    def _assess_hba1c_risk(self, value: float) -> str:
        """評估HbA1c風險等級"""
        if value < 5.7:
            return "normal"
        elif value < 6.5:
            return "borderline"
        else:
            return "high"

    def _assess_waist_risk(self, value: float) -> str:
        """評估腰圍風險等級 (需要性別信息，這裡使用通用閾值)"""
        # 使用亞洲標準
        if value < 80:
            return "normal"
        elif value < 90:
            return "borderline"
        else:
            return "high"

    # ========================================================================
    # 文字正規化 (Text Normalization)
    # ========================================================================

    def _normalize_text(self, text: str) -> str:
        """正規化OCR提取的文字

        Normalize text extracted from OCR:
        - Convert full-width characters to half-width
        - Remove extra whitespace
        - Standardize punctuation

        Args:
            text: 原始文字 (Raw text)

        Returns:
            正規化文字 (Normalized text)
        """
        # 轉換全形字符為半形 (Full-width to half-width)
        text = text.translate(
            str.maketrans(
                "０１２３４５６７８９：；，。！？（）【】「」",
                "0123456789:;,.!?()[]「」",
            )
        )

        # 移除多餘空白和換行
        text = re.sub(r"\s+", " ", text)

        # 標準化冒號
        text = text.replace("：", ":")
        text = text.replace("。", "")

        return text
