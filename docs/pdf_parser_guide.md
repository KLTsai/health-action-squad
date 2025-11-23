# PDF Parser Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-23
**Status:** Implementation Guide

## Overview

This guide provides detailed information about the PDF parser system in Health Action Squad, including supported hospital formats, how to add new templates, regex pattern examples, troubleshooting, and understanding the LLM fallback mechanism.

## Supported Hospital Formats

### Current Templates

#### 1. National Taiwan University Hospital (NTUH)

**Format Name**: `ntuh_template.py`

**Supported Report Types**:
- Annual health screening reports
- Lab panel reports (lipid, glucose, liver/kidney function)
- Clinical assessment forms
- Multi-page comprehensive physicals

**Example Header Detection**:
```
National Taiwan University Hospital
或
NTUH
或
臺灣大學醫院
```

**Typical Fields Extracted**:
- Total Cholesterol
- HDL, LDL, Triglycerides
- Blood Pressure (Systolic/Diastolic)
- Fasting Glucose, HbA1c
- Liver Function Tests (AST, ALT, GGT)
- Kidney Function (Creatinine, eGFR)
- BMI, Height, Weight

#### 2. Taipei Veterans General Hospital (TVGH)

**Format Name**: `tvgh_template.py`

**Supported Report Types**:
- Health screening programs
- Occupational health reports
- Employee wellness assessments

**Example Header Detection**:
```
Taipei Veterans General Hospital
或
TVGH
或
台北榮民總醫院
```

#### 3. Generic Hospital Report

**Format Name**: `generic_template.py`

**Supported Report Types**:
- Standard health screening from other hospitals
- Generic lab reports
- Fallback for unrecognized formats with confidence penalty

**Characteristics**:
- Detects common health metrics regardless of hospital
- Lower confidence threshold (0.70 vs 0.85)
- Best-effort extraction

## How to Add New Hospital Templates

### Step-by-Step Guide

#### Prerequisites

- Understanding of regex patterns (see [Regex Pattern Examples](#regex-pattern-examples) below)
- Sample PDF from the hospital you want to support
- Basic Python knowledge

#### Step 1: Extract Sample Text

Convert a sample PDF from the hospital to text:

```bash
# Using PDFProcessor to extract text from PDF
python -c "
from src.parsers.pdf_processor import PDFProcessor
text = PDFProcessor.extract_text_from_pdf('path/to/sample_report.pdf')
print(text)
"
```

Or manually convert:

```bash
# Using pdftotext (part of poppler)
pdftotext path/to/sample_report.pdf -
```

#### Step 2: Identify Key Patterns

Extract the patterns that identify this hospital's format and the health metrics:

```
Example text:
---
Memorial Hospital Group
Health Screening Report
Patient: John Doe  DOB: 01/01/1990

Total Cholesterol: 240 mg/dL
HDL Cholesterol:  35 mg/dL
LDL Cholesterol: 180 mg/dL
Blood Pressure: 140/90 mmHg
Fasting Glucose: 110 mg/dL
---

Key patterns to extract:
- Hospital name: "Memorial Hospital Group"
- Total Cholesterol: "240"
- Blood Pressure: "140" and "90"
```

#### Step 3: Create Template File

Create `src/parsers/templates/memorial_hospital_template.py`:

```python
"""
Memorial Hospital Group health report template.

Supports: Annual physicals, Health screenings
Source: Memorial Hospital Group
"""

from typing import Tuple, Dict, Any
import re


class MemorialHospitalTemplate:
    """Memorial Hospital Group report format."""

    # Header pattern to detect this hospital's format
    HEADER_PATTERN = r"Memorial Hospital Group|MHG"

    # Confidence threshold - set higher (0.85+) for distinctive formats
    CONFIDENCE_THRESHOLD = 0.85

    # Field extraction patterns (regex with capture groups)
    PATTERNS = {
        # Lipid panel
        "total_cholesterol": r"Total Cholesterol[:\s]+(\d+)",
        "hdl": r"HDL[:\s]+(\d+)",
        "ldl": r"LDL[:\s]+(\d+)",
        "triglycerides": r"Triglycerides[:\s]+(\d+)",

        # Cardiovascular
        "blood_pressure": r"Blood Pressure[:\s]+(\d+)/(\d+)",
        "heart_rate": r"Heart Rate[:\s]+(\d+)",

        # Metabolic
        "fasting_glucose": r"Fasting Glucose[:\s]+(\d+)",
        "hba1c": r"HbA1c[:\s]+([\d.]+)",

        # Anthropometric
        "bmi": r"BMI[:\s]+([\d.]+)",
        "weight": r"Weight[:\s]+(\d+)\s*kg",
        "height": r"Height[:\s]+(\d+)\s*cm",
    }

    @classmethod
    def match(cls, text: str) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Try to match this template to extracted text.

        Args:
            text: Raw OCR or extracted text from PDF

        Returns:
            (is_match, confidence_score, extracted_data)

        Examples:
            >>> text = "Memorial Hospital Group\nTotal Cholesterol: 240"
            >>> is_match, conf, data = MemorialHospitalTemplate.match(text)
            >>> is_match
            True
            >>> conf >= 0.85
            True
            >>> data['total_cholesterol']
            '240'
        """

        # Step 1: Check if this is likely the right hospital
        if not re.search(cls.HEADER_PATTERN, text, re.IGNORECASE):
            return False, 0.0, {}

        # Step 2: Extract all fields using patterns
        extracted = {}
        matches_found = 0

        for field_name, pattern in cls.PATTERNS.items():
            match_obj = re.search(pattern, text, re.IGNORECASE)
            if match_obj:
                # Handle multi-group patterns like blood pressure
                if len(match_obj.groups()) > 1:
                    extracted[field_name] = {
                        "systolic": match_obj.group(1),
                        "diastolic": match_obj.group(2),
                    }
                else:
                    extracted[field_name] = match_obj.group(1)
                matches_found += 1

        # Step 3: Calculate confidence based on fields found
        confidence = matches_found / len(cls.PATTERNS)

        # Step 4: Determine if match is good enough
        is_match = confidence >= cls.CONFIDENCE_THRESHOLD

        return is_match, confidence, extracted
```

#### Step 4: Register Template

Edit `src/parsers/data_extractor.py`:

```python
from parsers.templates import (
    NTUHTemplate,
    TVGHTemplate,
    GenericTemplate,
    MemorialHospitalTemplate,  # Add this import
)

class DataExtractor:
    """Extract structured health data from various hospital report formats."""

    # Register all known templates in order of specificity (most specific first)
    TEMPLATES = [
        NTUHTemplate,           # Most specific (Taiwan)
        TVGHTemplate,           # Taiwan
        MemorialHospitalTemplate,  # Your new template
        GenericTemplate,        # Fallback (least specific)
    ]
```

#### Step 5: Create Unit Test

Create `tests/unit/parsers/test_memorial_hospital_template.py`:

```python
"""Unit tests for Memorial Hospital template."""

import pytest
from src.parsers.templates import MemorialHospitalTemplate


class TestMemorialHospitalTemplate:
    """Test Memorial Hospital report format detection."""

    def test_header_detection(self):
        """Test that template correctly identifies hospital reports."""
        text = """
        Memorial Hospital Group
        Health Screening Report

        Total Cholesterol: 240 mg/dL
        """
        is_match, confidence, _ = MemorialHospitalTemplate.match(text)
        assert is_match
        assert confidence >= 0.85

    def test_cholesterol_extraction(self):
        """Test cholesterol field extraction."""
        text = "Total Cholesterol: 240"
        _, _, data = MemorialHospitalTemplate.match(text)
        assert data["total_cholesterol"] == "240"

    def test_blood_pressure_extraction(self):
        """Test multi-field extraction (BP systolic/diastolic)."""
        text = "Blood Pressure: 140/90"
        _, _, data = MemorialHospitalTemplate.match(text)
        assert data["blood_pressure"]["systolic"] == "140"
        assert data["blood_pressure"]["diastolic"] == "90"

    def test_no_false_positives(self):
        """Test that template doesn't match unrelated text."""
        text = "Some random hospital report"
        is_match, confidence, _ = MemorialHospitalTemplate.match(text)
        assert not is_match
        assert confidence < 0.85

    def test_partial_match_confidence(self):
        """Test confidence calculation with partial fields."""
        text = """
        Memorial Hospital Group
        Total Cholesterol: 240
        """
        # Only 1 of 11 fields found, so confidence = 1/11 ≈ 0.09
        _, confidence, _ = MemorialHospitalTemplate.match(text)
        assert confidence < cls.CONFIDENCE_THRESHOLD
```

Run tests:

```bash
pytest tests/unit/parsers/test_memorial_hospital_template.py -v
```

#### Step 6: Test with Real PDF

```bash
# Test the parser with your sample PDF
python -c "
from src.parsers.data_extractor import DataExtractor
from src.parsers.pdf_processor import PDFProcessor

pdf_path = 'path/to/real_hospital_report.pdf'
text = PDFProcessor.extract_text_from_pdf(pdf_path)

template_name, confidence, data = DataExtractor.match_templates(text)
print(f'Template: {template_name}')
print(f'Confidence: {confidence:.2%}')
print(f'Extracted: {data}')
"
```

## Regex Pattern Examples

### Common Health Metrics

#### Lipid Panel

```python
# Total Cholesterol (various formats)
r"Total Cholesterol[:\s]+(\d+)"           # "Total Cholesterol: 240"
r"TC[:\s]+(\d+)"                          # "TC: 240"
r"Cholesterol[:\s]+(\d+)"                 # "Cholesterol: 240"

# HDL (with optional units)
r"HDL[:\s]+(\d+)"                         # "HDL: 35"
r"HDL Cholesterol[:\s]+(\d+)\s*mg"        # "HDL Cholesterol: 35 mg"
r"好的膽固醇[:\s]+(\d+)"                   # Chinese: "好的膽固醇: 35"

# LDL
r"LDL[:\s]+(\d+)"                         # "LDL: 180"
r"壞的膽固醇[:\s]+(\d+)"                   # Chinese

# Triglycerides
r"Triglycerides?[:\s]+(\d+)"               # Handles plural and singular
r"三酸甘油脂[:\s]+(\d+)"                   # Chinese
```

#### Blood Pressure

```python
# Single capture (returns string)
r"BP[:\s]+(\d+)/(\d+)"                    # "BP: 140/90"
r"Blood Pressure[:\s]+(\d+)/(\d+)"        # "Blood Pressure: 140/90"

# With units
r"BP[:\s]+(\d+)/(\d+)\s*mmHg"             # "BP: 140/90 mmHg"

# Chinese
r"血壓[:\s]+(\d+)/(\d+)"                  # "血壓: 140/90"
```

#### Glucose & Diabetes

```python
# Fasting glucose
r"Fasting Glucose[:\s]+(\d+)"             # "Fasting Glucose: 110"
r"空腹血糖[:\s]+(\d+)"                     # Chinese

# HbA1c (floating point)
r"HbA1c[:\s]+([\d.]+)"                    # "HbA1c: 6.5"
r"醣化血紅蛋白[:\s]+([\d.]+)"              # Chinese

# Random glucose
r"Random Glucose[:\s]+(\d+)"               # Non-fasting
```

#### Body Measurements

```python
# BMI (floating point)
r"BMI[:\s]+([\d.]+)"                      # "BMI: 24.5"
r"Body Mass Index[:\s]+([\d.]+)"          # Full name

# Weight (in kg)
r"Weight[:\s]+(\d+)\s*kg"                 # "Weight: 70 kg"
r"體重[:\s]+(\d+)"                         # Chinese

# Height (in cm)
r"Height[:\s]+(\d+)\s*cm"                 # "Height: 175 cm"
r"身高[:\s]+(\d+)"                         # Chinese
```

### Pattern Tips

1. **Use `[:\s]+`** to match colons and variable whitespace
   - Matches: `"Cholesterol: 240"`, `"Cholesterol:240"`, `"Cholesterol :240"`

2. **Use `[\d.]+`** for decimals
   - Matches: `"HbA1c: 6.5"`, `"HbA1c: 6"`, `"HbA1c: 6.52"`

3. **Use `?` for optional parts**
   - `r"Triglycerides?[:\s]+(\d+)"` matches both "Triglyceride" and "Triglycerides"

4. **Use `re.IGNORECASE` flag**
   - Makes patterns case-insensitive: `re.search(pattern, text, re.IGNORECASE)`

5. **Test patterns in Python**
   ```python
   import re
   pattern = r"Total Cholesterol[:\s]+(\d+)"
   text = "Total Cholesterol: 240"
   match = re.search(pattern, text, re.IGNORECASE)
   print(match.group(1))  # Output: "240"
   ```

## Troubleshooting Guide

### Issue: Template Not Matching

**Symptom**: Parser falls back to OCR for hospital reports you added template for

**Diagnosis**:
1. Extract text from sample PDF:
   ```python
   from src.parsers.pdf_processor import PDFProcessor
   text = PDFProcessor.extract_text_from_pdf('sample.pdf')
   print(text[:500])  # Print first 500 chars
   ```

2. Check if HEADER_PATTERN matches:
   ```python
   import re
   from src.parsers.templates.your_template import YourTemplate

   if re.search(YourTemplate.HEADER_PATTERN, text, re.IGNORECASE):
       print("Header matches!")
   else:
       print("Header pattern NOT found")
   ```

3. Fix HEADER_PATTERN:
   ```python
   # If hospital name is "XYZ Medical Center"
   HEADER_PATTERN = r"XYZ Medical Center|XYZ|Medical Center"
   ```

**Solution**: Update HEADER_PATTERN to match actual text in PDF

### Issue: Low Confidence Score

**Symptom**: Template matches but confidence < 0.85, falls back to OCR

**Diagnosis**:
```python
from src.parsers.templates.your_template import YourTemplate

template_name, confidence, data = YourTemplate.match(text)
print(f"Confidence: {confidence:.2%}")
print(f"Fields found: {len(data)} / {len(YourTemplate.PATTERNS)}")
print(f"Missing fields: {set(YourTemplate.PATTERNS) - set(data)}")
```

**Solution**:
- If OCR is working fine and you want to allow this template: Lower CONFIDENCE_THRESHOLD to 0.70
- If some fields are truly optional: Remove them from PATTERNS dict
- If patterns aren't matching: Debug regex patterns (see [Regex Pattern Examples](#regex-pattern-examples))

### Issue: Extracted Values Incorrect

**Symptom**: Parser extracts "240x" instead of "240", or other formatting issues

**Diagnosis**:
```python
import re
pattern = r"Cholesterol[:\s]+(\d+)"
text = "Total Cholesterol: 240 mg/dL"
match = re.search(pattern, text)
print(match.group(1))  # What was actually captured?
```

**Solutions**:

1. **Add units to pattern** (if they interfere):
   ```python
   r"Cholesterol[:\s]+(\d+)\s*mg"  # Explicitly consume "mg"
   ```

2. **Use `\b` word boundaries**:
   ```python
   r"\bCholesterol[:\s]+(\d+)\b"  # Prevents partial matches
   ```

3. **Handle multiple units**:
   ```python
   r"Cholesterol[:\s]+(\d+)\s*(?:mg/dL|mg)?"  # Optional units
   ```

### Issue: PDF Won't Convert to Images

**Symptom**: `PDFProcessor.convert_to_images()` fails with error about Poppler

**Solution**:

**Windows**:
```bash
# Download poppler
# From: https://github.com/oschwartz10612/poppler-windows/releases

# Extract and add to system PATH
$env:Path += ";C:\Program Files\poppler\bin"

# Verify
pdftoppm -v
```

**macOS**:
```bash
brew install poppler
```

**Linux**:
```bash
sudo apt-get install poppler-utils
```

### Issue: OCR Not Working (PaddleOCR)

**Symptom**: OCREngine fails with model download error

**Diagnosis**:
```bash
# Check if models are cached
ls ~/.paddleocr/
```

**Solution**:

```bash
# Force redownload
python -c "
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True)  # Downloads ~500MB
"

# Or specify offline if models already cached
from src.parsers.ocr_engine import OCREngine
engine = OCREngine(use_online=False)
```

## LLM Fallback Explanation

### When Fallback is Used

1. **No template matches** with confidence ≥ 0.85
2. **Template matches** but confidence < 0.85
3. **Manual format** - User selected "hospital not in list"

### How It Works

```
Unmatched PDF
    ↓
OCREngine.extract_text()  (PaddleOCR)
    ↓
LLMParser.parse_structured()  (Gemini LLM)
    ↓ (with prompt below)
JSON with extracted metrics + confidence score
    ↓ (if confidence ≥ 0.85)
Use extracted data
    ↓ (if 0.70 ≤ confidence < 0.85)
Ask user to verify
    ↓ (if confidence < 0.70)
Reject, ask user to manually enter
```

### LLM Parser Prompt

Located in: `resources/prompts/llm_parser_prompt.txt`

```
You are a medical data extraction specialist.
Extract structured health metrics from OCR text.

REQUIREMENTS:
1. Return ONLY valid JSON (no markdown, no explanation)
2. Fields: total_cholesterol, hdl, ldl, triglycerides,
           blood_pressure, fasting_glucose, hba1c, bmi, weight, height
3. All values MUST be numbers (no units)
4. If not found, use null
5. blood_pressure format: {"systolic": number, "diastolic": number}
6. Include "confidence" (0-1) for entire extraction
7. List uncertain fields in "uncertain_fields" array

OCR TEXT:
{ocr_text}

RESPONSE (JSON ONLY):
```

### Confidence Scoring

LLM calculates confidence as:

```python
confidence = (fields_found / total_fields) * accuracy_factor

where:
- fields_found: Number of non-null extracted fields
- total_fields: 10 (standard health metrics)
- accuracy_factor: 0.9-1.0 (penalizes uncertain extractions)
```

**Example**:
- Found 8 fields, all confident → confidence = 0.8 × 1.0 = 0.80 (requires verification)
- Found 9 fields, 1 uncertain → confidence = 0.9 × 0.9 = 0.81 (requires verification)
- Found 7 fields, 1 uncertain → confidence = 0.7 × 0.9 = 0.63 (rejected, manual input)

### Why LLM Fallback?

1. **Handles unknown formats** - No need to maintain templates for every hospital
2. **Graceful degradation** - Works with low-quality OCR
3. **User transparency** - Confidence score indicates reliability
4. **Manual override** - Users can reject and re-enter if low confidence

### Limitations

- OCR quality directly impacts extraction accuracy
- Structured/tabular formats work better than free-form text
- Handwritten annotations often misread
- Confidence score is approximate (not ground truth)

## Integration with API

### Upload Endpoint

```python
# POST /api/v1/upload_report
# Returns:
{
  "parsing_method": "template_match",  # or "ocr_fallback"
  "parsing_confidence": 0.95,
  "extracted_data": {...},
  "health_report": {...}  # Formatted for analyst agent
}
```

### ReportAnalystAgent Integration

The analyst agent receives:

```python
{
  "data_source": "pdf_upload",
  "parsing_method": "template_match",
  "extraction_confidence": 0.95,
  "health_report": {
    "total_cholesterol": 240,
    "hdl": 35,
    "blood_pressure": {"systolic": 140, "diastolic": 90},
    ...
  }
}
```

This allows the analyst to:
- Assess extraction reliability (via confidence)
- Adjust risk assessment based on source quality
- Flag low-confidence data in analysis
- Request manual verification if needed

---

**Questions?** Open an issue on GitHub or check CLAUDE.md for system architecture details.
