# Health Report Parser Guide

## Overview

The health report parser module provides a unified interface for parsing and extracting health metrics from medical documents in multiple formats (PDF, JPG, PNG). It features automatic file type detection, OCR-based text extraction, and LLM-based fallback for incomplete data.

## Architecture

### Core Components

1. **HealthReportParser** (`src/parsers/health_report_parser.py`)
   - Main unified interface for health report parsing
   - Auto-detects file types (PDF, JPG, PNG)
   - Handles multi-page PDFs
   - Implements completeness scoring (0.0-1.0)
   - Intelligently merges data from multiple sources
   - Orchestrates OCR and LLM extraction pipelines

2. **GeminiStructuredExtractor** (`src/parsers/llm_fallback.py`)
   - Gemini API-based structured data extraction
   - Handles image and text content
   - JSON response parsing with markdown code block handling
   - Automatic retry logic with exponential backoff
   - Integrates with existing `AIClientFactory` from `src/ai/client.py`

### Module Integration

```
HealthReportParser
├── File Detection
│   └── Identifies PDF/JPG/PNG
├── PDF Conversion
│   └── pdf2image → List[PIL.Image]
├── OCR Extraction (placeholder)
│   └── PaddleOCR (when integrated)
├── Completeness Check
│   └── Scores data presence (0.0-1.0)
└── LLM Fallback Pipeline
    └── GeminiStructuredExtractor
        ├── Gemini Vision API (for images)
        ├── Gemini Text API (for content)
        └── Structured JSON extraction
```

## Usage Examples

### Basic Parsing

```python
from src.parsers import HealthReportParser
import asyncio

async def parse_report():
    parser = HealthReportParser(session_id="patient_123")

    # Parse a health report file
    result = await parser.parse("health_report.pdf")

    print(f"Completeness: {result['completeness']:.1%}")
    print(f"Source: {result['source']}")  # 'ocr', 'llm', or 'hybrid'
    print(f"Data: {result['data']}")

asyncio.run(parse_report())
```

### With Custom Threshold

```python
# Disable LLM fallback if OCR extracts >50% of data
parser = HealthReportParser(
    min_completeness_threshold=0.5,
    use_llm_fallback=True
)

result = await parser.parse("report.jpg")
```

### Batch Processing

```python
# Parse multiple pages and merge results
parser = HealthReportParser()
batch_result = await parser.parse_batch(
    file_paths=[
        "page1.pdf",
        "page2.jpg",
        "page3.jpg"
    ],
    merge_results=True
)

print(f"Overall completeness: {batch_result['overall_completeness']:.1%}")
print(f"Merged data: {batch_result['merged_data']}")
```

### Override LLM Fallback Per-Call

```python
parser = HealthReportParser(use_llm_fallback=True)

# Parse without LLM fallback for this call
result = await parser.parse(
    "report.pdf",
    use_llm_fallback=False  # Override instance setting
)
```

### Direct LLM Extraction

```python
from src.parsers import GeminiStructuredExtractor

extractor = GeminiStructuredExtractor(session_id="session_123")

# Extract from image
result = await extractor.extract("medical_report.jpg")

# Extract from text with retry
result = await extractor.extract_with_retry(
    "Total Cholesterol: 200 mg/dL\nHDL: 50 mg/dL",
    is_text=True,
    max_retries=3
)
```

## Data Structure

### Returned Data Format

```python
{
    "data": {
        "blood_pressure": "120/80",
        "systolic": 120,
        "diastolic": 80,
        "cholesterol": 200,
        "hdl_cholesterol": 50,
        "ldl_cholesterol": 130,
        "triglycerides": 150,
        "glucose": 100,
        "bmi": 22.5,
        "weight": 70,
        "height": 177,
        "heart_rate": 72,
        # ... more fields as extracted
    },
    "completeness": 0.71,  # 0.0-1.0 score
    "source": "hybrid",     # 'ocr', 'llm', or 'hybrid'
    "file_path": "/path/to/report.pdf",
    "file_type": "pdf"
}
```

### Required Fields for Completeness

The completeness score is calculated based on these 7 required health metrics:

1. `blood_pressure` - Format: "120/80" (systolic/diastolic)
2. `cholesterol` - Total cholesterol in mg/dL
3. `glucose` - Fasting glucose in mg/dL
4. `bmi` - Body mass index (numeric)
5. `heart_rate` - Beats per minute
6. `temperature` - In Celsius
7. `oxygen_saturation` - SpO2 in %

**Completeness Formula**:
```
completeness = (number of present required fields) / 7
```

Additional fields beyond these 7 are extracted but don't affect the completeness score.

## Supported File Types

### Directly Supported
- **PDF** (`.pdf`) - Multi-page support via pdf2image
- **JPG/JPEG** (`.jpg`, `.jpeg`) - Direct image processing
- **PNG** (`.png`) - Direct image processing

### Format Detection
- Automatic via file extension
- Case-insensitive (`.JPG`, `.Pdf` both work)
- Returns `FileType.UNKNOWN` for unsupported formats

## Extraction Pipeline

### OCR Extraction Flow

```
File Input
    ↓
Detect Type
    ↓
Convert to Images (PDF → Images)
    ↓
OCR Extraction (PaddleOCR)
    ↓
Completeness Check
    ↓
[Below Threshold?] → LLM Fallback
    ↓
Merge Results
    ↓
Return Structured Data
```

### LLM Fallback Conditions

The LLM fallback activates when:
1. `use_llm_fallback=True` (instance setting)
2. **AND** `completeness < min_completeness_threshold` (default: 0.7)

Example scenarios:
- OCR extracts 3 of 7 fields (43%) → Fallback activated
- OCR extracts 5 of 7 fields (71%) → No fallback (meets 70% threshold)

### Data Merging Strategy

When combining OCR and LLM results:
1. OCR data takes priority
2. For empty/missing fields in OCR, use LLM data
3. Non-empty OCR values are preserved even if LLM has alternatives

```python
# Example merge
ocr_data = {"blood_pressure": "120/80", "cholesterol": ""}
llm_data = {"cholesterol": "200", "glucose": "100"}

merged = parser._merge_data(ocr_data, llm_data)
# Result: {
#     "blood_pressure": "120/80",  # From OCR (takes priority)
#     "cholesterol": "200",         # From LLM (OCR was empty)
#     "glucose": "100"              # From LLM (OCR didn't have it)
# }
```

## Configuration

### Environment Variables

Configure via `.env` file or environment:

```bash
# LLM Model Configuration
MODEL_NAME=gemini-2.5-flash          # Gemini model name
TEMPERATURE=0.1                      # Sampling temperature (0-1)
MAX_TOKENS=2048                      # Max output tokens
GEMINI_API_KEY=your_api_key_here    # Gemini API key

# Logging
LOG_LEVEL=INFO                       # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json                      # json or console
```

### Programmatic Configuration

```python
from src.parsers import HealthReportParser

# Custom LLM settings via GeminiStructuredExtractor
parser = HealthReportParser()
parser.llm_extractor = GeminiStructuredExtractor(
    model_name="gemini-pro",
    temperature=0.1,
    max_output_tokens=1024
)

# Or set completeness threshold
parser.min_completeness_threshold = 0.5
```

## Error Handling

### Graceful Degradation

The parser implements graceful error handling:

```python
result = await parser.parse("invalid_file.pdf")

if result["source"] == "error":
    print(f"Parsing failed: {result['error']}")
    # Handle error case
else:
    # Use partial or complete data
    if result["completeness"] < 0.3:
        print("Warning: Data is very incomplete")
```

### Common Errors

| Scenario | Result | Recovery |
|----------|--------|----------|
| File doesn't exist | `source: "error"` | Check file path |
| Unsupported type | `source: "error"` | Convert file to supported format |
| OCR fails | Falls back to LLM | Automatic if enabled |
| LLM fails | Returns OCR data | No further fallback available |
| Both fail | Empty data | Manual input required |

## Performance Considerations

### File Size Limits

- **Image base64 encoding**: Max 100 MB per image
- **PDF page limit**: No enforced limit (but recommend <50 pages)
- **API payload**: Max ~4 MB for Gemini API (enforced by Google)

### Optimization Tips

1. **Compress images** before parsing (reduces API payload)
2. **Use PDF for multi-page documents** (more efficient than multiple JPGs)
3. **Batch processing**: Parse multiple pages concurrently
4. **Session IDs**: Reuse parser instance for same patient (reduces overhead)

### Async Usage

All extraction methods are async for non-blocking I/O:

```python
# Concurrent batch processing (recommended)
tasks = [parser.parse(f) for f in file_list]
results = await asyncio.gather(*tasks)

# Sequential processing (less efficient)
results = []
for f in file_list:
    results.append(await parser.parse(f))
```

## Logging

### Structured Logging

All operations are logged with structured context:

```python
# Logs include:
# - Session ID
# - Agent name (HealthReportParser)
# - Operation type (parse_start, extract_from_ocr, etc.)
# - Completeness scores
# - Error details

parser = HealthReportParser(session_id="patient_456")
result = await parser.parse("report.pdf")

# Log output (JSON format):
# {
#   "event": "Parsing started",
#   "session_id": "patient_456",
#   "agent": "HealthReportParser",
#   "file": "report.pdf",
#   "action": "parse_start"
# }
```

### Debug Logging

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python main.py
```

This outputs detailed traces:
- File detection results
- Image conversion progress
- OCR extraction details
- LLM API calls
- Data merging operations

## Testing

### Unit Tests

Run parser unit tests:

```bash
pytest tests/unit/test_health_report_parser.py -v
pytest tests/unit/test_llm_fallback.py -v
```

### Integration Tests

Run parser integration tests:

```bash
pytest tests/integration/test_parser_integration.py -v
```

### Test Coverage

Generate coverage report:

```bash
pytest tests/unit/test_health_report_parser.py \
        tests/unit/test_llm_fallback.py \
        --cov=src.parsers --cov-report=html
```

## Future Enhancements

### Planned Features

1. **PaddleOCR Integration**
   - Actual text extraction from images
   - Multi-language support (English, Traditional Chinese)
   - Table detection for structured data

2. **Advanced Data Validation**
   - Threshold checking against medical guidelines
   - Outlier detection and flagging
   - Unit conversion and normalization

3. **Optical Verification**
   - Return extracted regions from OCR
   - Confidence scores per field
   - Visual feedback for uncertain extractions

4. **API Scaling**
   - Batch API endpoint
   - Async task queue for large jobs
   - Progress tracking for long-running extractions

5. **RAG-based Extraction**
   - Medical knowledge base integration
   - Context-aware field extraction
   - Rare condition handling

## Troubleshooting

### Issue: Low Completeness Score

**Symptoms**: `completeness < 0.3`

**Solutions**:
1. Check image quality (ensure readable text)
2. Try manual entry for critical fields
3. Verify field format matches expected structure
4. Check API responses for parsing errors

### Issue: LLM Fallback Not Activating

**Symptoms**: LLM not called despite low OCR completeness

**Solutions**:
1. Verify `use_llm_fallback=True`
2. Check `min_completeness_threshold` setting
3. Verify Gemini API key in `.env`
4. Check logs for API errors

### Issue: Slow Parsing

**Symptoms**: Takes >10 seconds per page

**Solutions**:
1. Compress images (reduce file size)
2. Use concurrent processing for batch jobs
3. Check network latency to Gemini API
4. Consider PDF vs. image format

## API Reference

See docstrings in:
- `src/parsers/health_report_parser.py` - HealthReportParser class
- `src/parsers/llm_fallback.py` - GeminiStructuredExtractor class

For detailed method signatures and parameters.
