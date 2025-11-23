# PaddleOCR Parser - Quick Start Guide

## Installation

All dependencies are already in `requirements.txt`. No additional setup needed:

```bash
# Dependencies automatically installed with project
pip install -r requirements.txt
```

## Basic Usage (5 minutes)

### 1. Parse a Single Image

```python
import asyncio
from src.parsers import PaddleOCRHealthReportParser

async def parse_report():
    # Initialize parser
    parser = PaddleOCRHealthReportParser(language="ch_tra", device="cpu")

    # Parse image
    report = await parser.parse("health_report.png")

    # Access results
    print(f"Age: {report.patient_info.get('age')}")
    print(f"Total Cholesterol: {report.vital_signs['total_cholesterol'].value}")
    print(f"Confidence: {report.confidence_score:.1%}")

    return report.to_dict()

# Run
result = asyncio.run(parse_report())
```

### 2. Convert PDF to Images First

```python
import asyncio
from src.parsers import PDFConverter, PaddleOCRHealthReportParser

async def parse_pdf_report():
    # Convert PDF to images
    converter = PDFConverter(dpi=300)
    images = await converter.convert_pdf_to_images("health_report.pdf", "output/images")

    print(f"Generated {len(images)} images")

    # Parse each image
    parser = PaddleOCRHealthReportParser()
    for image_path in images:
        report = await parser.parse(image_path)
        print(f"Page {images.index(image_path) + 1}: {len(report.vital_signs)} metrics extracted")

asyncio.run(parse_pdf_report())
```

### 3. Batch Process Multiple Images

```python
import asyncio
from src.parsers import PaddleOCRHealthReportParser

async def batch_parse():
    parser = PaddleOCRHealthReportParser()

    images = ["report1.png", "report2.png", "report3.png"]
    reports = await parser.parse_batch(images)

    for report in reports:
        print(f"Patient age: {report.patient_info.get('age')}")
        print(f"Extracted metrics: {len(report.vital_signs)}")

asyncio.run(batch_parse())
```

## Common Operations

### Get Patient Information

```python
patient = report.patient_info

age = patient.get("age")              # int
gender = patient.get("gender")        # "M" or "F"
height = patient.get("height_cm")     # float
weight = patient.get("weight_kg")     # float
bmi = patient.get("bmi")              # float
```

### Get Vital Signs with Risk Level

```python
for metric_name, metric in report.vital_signs.items():
    print(f"{metric.name}: {metric.value} {metric.unit}")
    print(f"  Reference: {metric.reference_range}")
    print(f"  Risk Level: {metric.risk_level}")  # normal, borderline, high

    if metric.risk_level != "normal":
        print(f"  ⚠️ Needs attention!")
```

### Get Lifestyle Information

```python
lifestyle = report.lifestyle_factors

smoking = lifestyle.get("smoking_status")      # current, former, never
exercise = lifestyle.get("exercise_frequency") # int (times per week)
alcohol = lifestyle.get("drinks_per_week")     # float
```

### Get Test Date

```python
test_date = report.test_date  # "2024-11-15" format
```

## Data Structure Overview

### HealthMetric Object

```python
class HealthMetric:
    name: str                       # "Total Cholesterol"
    value: float                    # 180.0
    unit: str                       # "mg/dL"
    reference_range: str            # "<200"
    risk_level: str                 # "normal", "borderline", "high"
```

### ParsedHealthReport Object

```python
class ParsedHealthReport:
    patient_info: Dict[str, Any]           # Age, gender, BMI, etc.
    vital_signs: Dict[str, HealthMetric]   # All health metrics
    lifestyle_factors: Dict[str, Any]      # Smoking, exercise, alcohol
    test_date: Optional[str]               # "YYYY-MM-DD"
    confidence_score: float                # 0-1
    raw_text: str                          # Full OCR text
    parsing_errors: List[str]              # Any extraction errors
```

## Supported Metrics

### Vital Signs (Automatically Extracted)

- **Cholesterol Panel**
  - Total Cholesterol (TC)
  - LDL Cholesterol (Low-Density)
  - HDL Cholesterol (High-Density)
  - Triglycerides (TG)

- **Blood Pressure**
  - Systolic BP (收縮壓)
  - Diastolic BP (舒張壓)

- **Glucose Metabolism**
  - Fasting Glucose (空腹血糖)
  - HbA1c (糖化血色素)

- **Anthropometry**
  - BMI (Body Mass Index)
  - Waist Circumference (腰圍)

### Lifestyle Factors

- Smoking Status (吸菸狀況)
- Exercise Frequency (運動頻率)
- Alcohol Consumption (飲酒量)

## Text Format Examples

The parser recognizes these formats:

```
年齡：45              (Age in Chinese)
Age: 45              (Age in English)
45歲                 (Age with year character)

性別：男             (Gender in Chinese)
Gender: Male         (Gender in English)

身高：170cm          (Height)
Height: 170 cm      (Height English)

體重：70kg           (Weight)
Weight: 70 kg       (Weight English)

總膽固醇：200        (Total Cholesterol)
Total Cholesterol: 200

血壓：130/85        (Blood Pressure)
BP: 130/85

空腹血糖：100       (Fasting Glucose)
Fasting Glucose: 100

HbA1c：6.5          (HbA1c)

吸菸：否             (Smoking: No)
運動：每週3次       (Exercise: 3 times per week)

檢查日期：2024年11月15日  (Test Date)
```

## Error Handling

```python
try:
    report = await parser.parse("health_report.png")
except FileNotFoundError:
    print("Image file not found")
except ValueError as e:
    print(f"OCR processing failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

# Check for extraction errors
if report.parsing_errors:
    print(f"Some fields could not be extracted: {report.parsing_errors}")

# Check confidence
if report.confidence_score < 0.7:
    print("⚠️ Low OCR confidence - results may be inaccurate")
```

## Configuration Options

### Parser Initialization

```python
# Default (CPU, Traditional Chinese)
parser = PaddleOCRHealthReportParser()

# With GPU acceleration (faster)
parser = PaddleOCRHealthReportParser(device="gpu")

# Custom language (English only)
parser = PaddleOCRHealthReportParser(language="en")
```

### PDF Converter Initialization

```python
# Default (300 DPI - standard medical documents)
converter = PDFConverter()

# Lower DPI for speed (200 DPI)
converter = PDFConverter(dpi=200)

# Higher DPI for precision (600 DPI)
converter = PDFConverter(dpi=600)
```

## Performance Tips

1. **Use GPU if available** (~5x faster)
   ```python
   parser = PaddleOCRHealthReportParser(device="gpu")
   ```

2. **Batch process multiple files** (parallelized)
   ```python
   reports = await parser.parse_batch(image_list)
   ```

3. **Enhance image quality for difficult documents**
   ```python
   enhanced_image = converter.enhance_image_quality("report.png")
   report = await parser.parse(enhanced_image)
   ```

4. **Reduce PDF DPI for faster conversion**
   ```python
   converter = PDFConverter(dpi=200)  # Instead of 300
   ```

## Logging & Debugging

The module uses structured logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now you'll see detailed logs during parsing
report = await parser.parse("health_report.png")

# Logs show:
# - OCR progress
# - Extracted fields
# - Confidence scores
# - Any errors or warnings
```

## Next Steps

1. **See detailed API**: Read [PARSER_MODULE_GUIDE.md](docs/PARSER_MODULE_GUIDE.md)
2. **Check examples**: View test files in `tests/unit/test_paddle_ocr_parser.py`
3. **Integrate with workflow**: Use with ADK agents in `src/workflow/`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Low confidence (<0.7) | Enhance image: `converter.enhance_image_quality()` |
| Missing metrics | Check raw_text in report; format might differ |
| PDF conversion fails | Try lower DPI: `PDFConverter(dpi=200)` |
| Out of memory | Process PDFs page-by-page instead of batch |

## API Quick Reference

```python
# Main classes
from src.parsers import PaddleOCRHealthReportParser, PDFConverter

# Parse single image
report = await parser.parse(image_path: str) -> ParsedHealthReport

# Parse multiple images in parallel
reports = await parser.parse_batch(image_paths: List[str]) -> List[ParsedHealthReport]

# Convert PDF to images
images = await converter.convert_pdf_to_images(pdf_path: str) -> List[str]

# Convert PDF synchronously
images = converter.convert_pdf_to_images_sync(pdf_path: str) -> List[str]

# Enhance image quality
enhanced = converter.enhance_image_quality(image_path: str) -> str

# Crop whitespace
cropped = converter.crop_to_content(image_path: str) -> str
```

---

**For detailed information**, see [PARSER_MODULE_GUIDE.md](docs/PARSER_MODULE_GUIDE.md)
