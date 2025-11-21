"""Structured logging for Health Action Squad.

Provides structured JSON logging with agent-to-agent (A2A) tracing.
MUST be used instead of print() statements.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import structlog
from datetime import datetime

from ..common.config import Config


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structured logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "console")
    """
    # Ensure logs directory exists
    Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend(
            [
                structlog.dev.ConsoleRenderer(colors=True),
            ]
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger

    Example:
        logger = get_logger(__name__)
        logger.info("Agent started", extra={"agent": "planner", "session_id": "123"})
    """
    return structlog.get_logger(name)


class AgentLogger:
    """Specialized logger for agent tracing.

    Provides structured logging with automatic agent and session context.
    """

    def __init__(self, agent_name: str, session_id: Optional[str] = None):
        """Initialize agent logger.

        Args:
            agent_name: Name of the agent
            session_id: Optional session ID
        """
        self.logger = get_logger(agent_name)
        self.agent_name = agent_name
        self.session_id = session_id
        self._iteration = 0

    def _build_context(self, **kwargs) -> Dict[str, Any]:
        """Build logging context with agent metadata.

        Args:
            **kwargs: Additional context fields

        Returns:
            Context dictionary
        """
        context = {
            "agent": self.agent_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self.session_id:
            context["session_id"] = self.session_id

        if self._iteration > 0:
            context["iteration"] = self._iteration

        context.update(kwargs)
        return context

    def set_session(self, session_id: str) -> None:
        """Set session ID for this logger.

        Args:
            session_id: Session identifier
        """
        self.session_id = session_id

    def set_iteration(self, iteration: int) -> None:
        """Set iteration counter for retry loops.

        Args:
            iteration: Iteration number
        """
        self._iteration = iteration

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        self.logger.debug(message, **self._build_context(**kwargs))

    def info(self, message: str, **kwargs) -> None:
        """Log info message.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        self.logger.info(message, **self._build_context(**kwargs))

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        self.logger.warning(message, **self._build_context(**kwargs))

    def error(self, message: str, **kwargs) -> None:
        """Log error message.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        self.logger.error(message, **self._build_context(**kwargs))

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message.

        Args:
            message: Log message
            **kwargs: Additional context
        """
        self.logger.critical(message, **self._build_context(**kwargs))

    def trace_state_transition(self, from_state: str, to_state: str, **kwargs) -> None:
        """Log state transition for workflow tracing.

        Args:
            from_state: Previous state
            to_state: New state
            **kwargs: Additional context
        """
        self.info(
            "State transition", from_state=from_state, to_state=to_state, **kwargs
        )

    def trace_agent_call(self, target_agent: str, action: str, **kwargs) -> None:
        """Log agent-to-agent (A2A) call.

        Args:
            target_agent: Target agent name
            action: Action being performed
            **kwargs: Additional context
        """
        self.info("Agent call", target_agent=target_agent, action=action, **kwargs)


# Initialize logging on module import
setup_logging(log_level=Config.LOG_LEVEL, log_format=Config.LOG_FORMAT)
