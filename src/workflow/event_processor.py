"""Event stream processing module for ADK workflows.

Extracts agent outputs from ADK event streams using configurable mappings.
Enables configuration-driven agent output extraction without code changes.
"""

from typing import Dict, Any, AsyncIterator, Optional
import logging

logger = logging.getLogger(__name__)


class EventStreamProcessor:
    """Processes ADK event streams and extracts agent outputs.

    Key Innovation: Configuration-driven agent-to-output-key mapping.
    Adding new agents only requires updating the mapping configuration,
    not modifying code logic.

    Example:
        >>> processor = EventStreamProcessor({
        ...     "ReportAnalyst": "health_analysis",
        ...     "LifestylePlanner": "current_plan",
        ...     "SafetyGuard": "validation_result"
        ... })
        >>> outputs = await processor.process_events(workflow.run_async(ctx))
        >>> assert "health_analysis" in outputs
    """

    def __init__(self, agent_output_mapping: Dict[str, str]):
        """Initialize with agent-to-output-key mapping.

        Args:
            agent_output_mapping: Maps agent names to output keys.
                Example: {"ReportAnalyst": "health_analysis"}

        Raises:
            ValueError: If mapping is empty or None
        """
        if not agent_output_mapping:
            raise ValueError("agent_output_mapping cannot be empty or None")

        self.mapping = agent_output_mapping
        logger.debug(
            "EventStreamProcessor initialized",
            extra={"agent_mapping": list(agent_output_mapping.keys())}
        )

    async def process_events(
        self,
        event_stream: AsyncIterator,
        logger_instance: Optional[logging.Logger] = None
    ) -> Dict[str, Any]:
        """Process event stream and return agent outputs.

        Robustly handles malformed events by:
        - Skipping events without author/content attributes
        - Skipping events from unknown agents (with warning)
        - Skipping events with empty/None text
        - Gracefully handling missing attributes

        Args:
            event_stream: Async iterator of ADK events
            logger_instance: Optional logger for debug output

        Returns:
            Dictionary mapping output keys to agent outputs.
            Empty dict if no valid events found.

        Example:
            >>> processor = EventStreamProcessor({"Agent1": "output1"})
            >>> outputs = await processor.process_events(workflow.run_async(ctx))
            >>> print(outputs["output1"])
            "Agent1's response text"

        Note:
            If the same agent emits multiple events, the last output wins.
            This is intentional to allow agents to refine their output.
        """
        agent_outputs = {}
        effective_logger = logger_instance or logger

        async for event in event_stream:
            try:
                # Skip events without author attribute
                if not hasattr(event, 'author'):
                    effective_logger.debug(
                        "Skipping event without author attribute",
                        extra={"event_type": type(event).__name__}
                    )
                    continue

                author = event.author

                # Skip events with empty author
                if not author:
                    effective_logger.debug("Skipping event with empty author")
                    continue

                # Check if this agent is in our mapping
                if author not in self.mapping:
                    effective_logger.warning(
                        f"Unknown agent in event stream: {author}",
                        extra={
                            "unknown_agent": author,
                            "known_agents": list(self.mapping.keys())
                        }
                    )
                    continue

                output_key = self.mapping[author]

                # Skip events without content attribute
                if not hasattr(event, 'content'):
                    effective_logger.debug(
                        f"Skipping event from {author} without content attribute"
                    )
                    continue

                content = event.content

                # Skip events with None content
                if content is None:
                    effective_logger.debug(
                        f"Skipping event from {author} with None content"
                    )
                    continue

                # Extract text from content parts
                if hasattr(content, 'parts') and content.parts:
                    for part in content.parts:
                        # Check if part has text attribute
                        if not hasattr(part, 'text'):
                            continue

                        text = part.text

                        # Skip None or empty text
                        if text is None or (isinstance(text, str) and not text):
                            continue

                        # Valid text found - extract it
                        agent_outputs[output_key] = text

                        effective_logger.debug(
                            f"Extracted agent output",
                            extra={
                                "agent": author,
                                "output_key": output_key,
                                "text_length": len(text)
                            }
                        )

                        # Break after first valid text part
                        # (agents typically emit one text part per event)
                        break
                else:
                    effective_logger.debug(
                        f"Skipping event from {author} with empty or missing parts"
                    )

            except Exception as e:
                # Log but don't crash on malformed events
                effective_logger.error(
                    f"Error processing event: {e}",
                    extra={
                        "error_type": type(e).__name__,
                        "event_type": type(event).__name__ if event else "None"
                    }
                )
                continue

        effective_logger.info(
            "Event stream processing completed",
            extra={
                "extracted_outputs": list(agent_outputs.keys()),
                "output_count": len(agent_outputs)
            }
        )

        return agent_outputs
