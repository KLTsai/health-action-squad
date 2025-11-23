"""Health report parsing module for Health Action Squad.

Provides unified interface for parsing health reports in multiple formats
(PDF, JPG, PNG) with automatic detection and LLM-based fallback for
incomplete extraction.
"""

# Core parser modules
from .paddle_ocr_parser import PaddleOCRHealthReportParser, ParsedHealthReport
from .pdf_converter import PDFConverter

# Legacy modules (optional imports to avoid dependency issues)
try:
    from .health_report_parser import HealthReportParser
except ImportError:
    HealthReportParser = None

try:
    from .llm_fallback import GeminiStructuredExtractor
except ImportError:
    GeminiStructuredExtractor = None

__all__ = [
    "PaddleOCRHealthReportParser",
    "ParsedHealthReport",
    "PDFConverter",
    "HealthReportParser",
    "GeminiStructuredExtractor",
]
