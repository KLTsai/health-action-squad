"""Workflow module for Health Action Squad.

Contains orchestration logic and workflow patterns.
"""

from .event_processor import EventStreamProcessor
from .response_formatter import ResponseFormatter

# Lazy import to avoid requiring google.adk at import time
def _get_orchestrator():
    from .orchestrator import Orchestrator
    return Orchestrator

__all__ = ["EventStreamProcessor", "ResponseFormatter", "_get_orchestrator"]
