"""API package for Health Action Squad REST server.

This package provides FastAPI REST endpoints for the Health Action Squad
multi-agent workflow system.
"""

from .server import app

__all__ = ["app"]
