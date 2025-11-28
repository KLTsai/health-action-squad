"""Comprehensive tests for EventStreamProcessor.

Tests cover:
1. Agent mapping (known agents, unknown agents, empty authors)
2. Content extraction (valid text, multiple parts, empty/None text)
3. Multiple agents (simultaneous, same agent multiple times, mixed order)
4. Error handling (malformed events, missing attributes, exceptions)
5. Configuration-driven extensibility
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
import logging
from src.workflow.event_processor import EventStreamProcessor


class TestEventStreamProcessor:
    """Comprehensive tests for EventStreamProcessor."""

    @pytest.fixture
    def processor(self):
        """Create processor with standard 3-agent mapping."""
        return EventStreamProcessor({
            "Agent1": "output1",
            "Agent2": "output2",
            "Agent3": "output3"
        })

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger for testing logging behavior."""
        return MagicMock(spec=logging.Logger)

    def create_mock_event(self, author: str, text: str):
        """Helper to create mock ADK event with standard structure.

        Args:
            author: Agent name (e.g., "Agent1")
            text: Text content to return

        Returns:
            MagicMock event object matching ADK event structure
        """
        event = MagicMock()
        event.author = author

        part = MagicMock()
        part.text = text

        event.content = MagicMock()
        event.content.parts = [part]

        return event

    # ========================================================================
    # Test 1: Agent Mapping
    # ========================================================================

    @pytest.mark.asyncio
    async def test_extract_single_agent_output(self, processor):
        """Test extracting output from single agent."""
        events = [
            self.create_mock_event("Agent1", "output text from agent1")
        ]

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream())

        assert "output1" in outputs
        assert outputs["output1"] == "output text from agent1"

    @pytest.mark.asyncio
    async def test_extract_multiple_agents(self, processor):
        """Test extracting outputs from multiple agents."""
        events = [
            self.create_mock_event("Agent1", "text1"),
            self.create_mock_event("Agent2", "text2"),
            self.create_mock_event("Agent3", "text3"),
        ]

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 3
        assert outputs["output1"] == "text1"
        assert outputs["output2"] == "text2"
        assert outputs["output3"] == "text3"

    @pytest.mark.asyncio
    async def test_unknown_agent_skipped(self, processor, mock_logger):
        """Test that unknown agents are skipped with warning."""
        events = [
            self.create_mock_event("UnknownAgent", "should be skipped"),
            self.create_mock_event("Agent1", "should be extracted"),
        ]

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream(), mock_logger)

        assert len(outputs) == 1
        assert "output1" in outputs
        assert "UnknownAgent" not in outputs

        # Verify warning was logged
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_event_without_author(self, processor):
        """Test handling events without author attribute."""
        event = MagicMock()
        del event.author  # Remove author attribute

        async def mock_stream():
            yield event

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0  # Should skip gracefully

    @pytest.mark.asyncio
    async def test_event_with_empty_author(self, processor):
        """Test handling events with empty author string."""
        event = MagicMock()
        event.author = ""  # Empty author
        event.content = MagicMock()
        event.content.parts = [MagicMock(text="some text")]

        async def mock_stream():
            yield event

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0  # Should skip empty authors

    # ========================================================================
    # Test 2: Content Extraction
    # ========================================================================

    @pytest.mark.asyncio
    async def test_event_without_content(self, processor):
        """Test handling events without content attribute."""
        event = MagicMock()
        event.author = "Agent1"
        del event.content  # Remove content attribute

        async def mock_stream():
            yield event

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0

    @pytest.mark.asyncio
    async def test_event_with_none_content(self, processor):
        """Test handling events with None content."""
        event = MagicMock()
        event.author = "Agent1"
        event.content = None

        async def mock_stream():
            yield event

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0

    @pytest.mark.asyncio
    async def test_event_with_empty_parts(self, processor):
        """Test handling events with empty parts list."""
        event = MagicMock()
        event.author = "Agent1"
        event.content = MagicMock()
        event.content.parts = []

        async def mock_stream():
            yield event

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0

    @pytest.mark.asyncio
    async def test_event_with_none_parts(self, processor):
        """Test handling events with None parts."""
        event = MagicMock()
        event.author = "Agent1"
        event.content = MagicMock()
        event.content.parts = None

        async def mock_stream():
            yield event

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0

    @pytest.mark.asyncio
    async def test_event_with_none_text(self, processor):
        """Test handling parts with None text."""
        event = MagicMock()
        event.author = "Agent1"

        part = MagicMock()
        part.text = None

        event.content = MagicMock()
        event.content.parts = [part]

        async def mock_stream():
            yield event

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0

    @pytest.mark.asyncio
    async def test_event_with_empty_text(self, processor):
        """Test handling parts with empty text string."""
        event = MagicMock()
        event.author = "Agent1"

        part = MagicMock()
        part.text = ""  # Empty string

        event.content = MagicMock()
        event.content.parts = [part]

        async def mock_stream():
            yield event

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0

    @pytest.mark.asyncio
    async def test_event_part_without_text_attribute(self, processor):
        """Test handling parts without text attribute."""
        event = MagicMock()
        event.author = "Agent1"

        part = MagicMock()
        del part.text  # Remove text attribute

        event.content = MagicMock()
        event.content.parts = [part]

        async def mock_stream():
            yield event

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0

    @pytest.mark.asyncio
    async def test_event_with_multiple_parts_extracts_first(self, processor):
        """Test that only first valid text part is extracted."""
        event = MagicMock()
        event.author = "Agent1"

        part1 = MagicMock()
        part1.text = "first text"

        part2 = MagicMock()
        part2.text = "second text"

        event.content = MagicMock()
        event.content.parts = [part1, part2]

        async def mock_stream():
            yield event

        outputs = await processor.process_events(mock_stream())

        assert outputs["output1"] == "first text"

    # ========================================================================
    # Test 3: Multiple Agents
    # ========================================================================

    @pytest.mark.asyncio
    async def test_same_agent_multiple_times_last_wins(self, processor):
        """Test that last output wins when same agent emits multiple times."""
        events = [
            self.create_mock_event("Agent1", "first output"),
            self.create_mock_event("Agent1", "second output"),
            self.create_mock_event("Agent1", "third output"),
        ]

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream())

        assert outputs["output1"] == "third output"

    @pytest.mark.asyncio
    async def test_mixed_order_agents(self, processor):
        """Test that agent event order doesn't matter."""
        events = [
            self.create_mock_event("Agent3", "text3"),
            self.create_mock_event("Agent1", "text1"),
            self.create_mock_event("Agent2", "text2"),
        ]

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 3
        assert outputs["output1"] == "text1"
        assert outputs["output2"] == "text2"
        assert outputs["output3"] == "text3"

    @pytest.mark.asyncio
    async def test_interleaved_agent_events(self, processor):
        """Test interleaved events from multiple agents."""
        events = [
            self.create_mock_event("Agent1", "a1_v1"),
            self.create_mock_event("Agent2", "a2_v1"),
            self.create_mock_event("Agent1", "a1_v2"),  # Agent1 updates
            self.create_mock_event("Agent3", "a3_v1"),
            self.create_mock_event("Agent2", "a2_v2"),  # Agent2 updates
        ]

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 3
        assert outputs["output1"] == "a1_v2"  # Last Agent1 output
        assert outputs["output2"] == "a2_v2"  # Last Agent2 output
        assert outputs["output3"] == "a3_v1"

    # ========================================================================
    # Test 4: Error Handling
    # ========================================================================

    @pytest.mark.asyncio
    async def test_malformed_event_skipped_gracefully(self, processor, mock_logger):
        """Test that malformed events are skipped without crashing."""
        # Create event that raises exception when accessing author
        # This simulates corrupted event objects
        class MalformedEvent:
            @property
            def author(self):
                raise Exception("Malformed event")

        malformed_event = MalformedEvent()

        valid_event = self.create_mock_event("Agent1", "valid text")

        async def mock_stream():
            yield malformed_event
            yield valid_event

        outputs = await processor.process_events(mock_stream(), mock_logger)

        # Should still extract valid event
        assert "output1" in outputs
        assert outputs["output1"] == "valid text"

        # Error should be logged
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_empty_event_stream(self, processor):
        """Test handling empty event stream."""
        async def mock_stream():
            return
            yield  # Make it a generator

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0
        assert outputs == {}

    @pytest.mark.asyncio
    async def test_event_stream_with_only_invalid_events(self, processor):
        """Test stream with only invalid events returns empty dict."""
        events = [
            MagicMock(author="Unknown1"),  # Unknown agent
            MagicMock(author="Unknown2"),  # Unknown agent
        ]

        # Add content to make them valid structure, just unknown
        for event in events:
            event.content = MagicMock()
            event.content.parts = [MagicMock(text="some text")]

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream())

        assert len(outputs) == 0

    # ========================================================================
    # Test 5: Configuration-Driven Extensibility
    # ========================================================================

    @pytest.mark.asyncio
    async def test_configuration_driven_extension(self):
        """Test that adding new agents only requires config change.

        This demonstrates the key innovation: no code changes needed
        to support new agents, just add mapping entry.
        """
        # Simulate adding a 4th agent to the system
        processor = EventStreamProcessor({
            "Agent1": "output1",
            "Agent2": "output2",
            "Agent3": "output3",
            "NewAgent": "new_output"  # <- Just add this line
        })

        events = [
            self.create_mock_event("NewAgent", "new agent text"),
            self.create_mock_event("Agent1", "agent1 text"),
        ]

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream())

        assert "new_output" in outputs
        assert outputs["new_output"] == "new agent text"
        assert "output1" in outputs

    @pytest.mark.asyncio
    async def test_custom_output_keys(self):
        """Test that output keys can be any string, not just 'outputN'."""
        processor = EventStreamProcessor({
            "ReportAnalyst": "health_analysis",
            "LifestylePlanner": "current_plan",
            "SafetyGuard": "validation_result"
        })

        events = [
            self.create_mock_event("ReportAnalyst", "health data"),
            self.create_mock_event("LifestylePlanner", "plan data"),
            self.create_mock_event("SafetyGuard", "validation data"),
        ]

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream())

        assert outputs["health_analysis"] == "health data"
        assert outputs["current_plan"] == "plan data"
        assert outputs["validation_result"] == "validation data"

    def test_initialization_with_empty_mapping(self):
        """Test that empty mapping raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty or None"):
            EventStreamProcessor({})

    def test_initialization_with_none_mapping(self):
        """Test that None mapping raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty or None"):
            EventStreamProcessor(None)

    # ========================================================================
    # Test 6: Logging Behavior
    # ========================================================================

    @pytest.mark.asyncio
    async def test_logging_with_custom_logger(self, processor, mock_logger):
        """Test that custom logger is used when provided."""
        events = [
            self.create_mock_event("Agent1", "test output")
        ]

        async def mock_stream():
            for e in events:
                yield e

        await processor.process_events(mock_stream(), mock_logger)

        # Verify logger was called
        assert mock_logger.debug.called or mock_logger.info.called

    @pytest.mark.asyncio
    async def test_logging_without_custom_logger(self, processor):
        """Test that processor works without custom logger."""
        events = [
            self.create_mock_event("Agent1", "test output")
        ]

        async def mock_stream():
            for e in events:
                yield e

        # Should not crash without logger
        outputs = await processor.process_events(mock_stream())

        assert "output1" in outputs

    # ========================================================================
    # Test 7: Real-World Scenarios
    # ========================================================================

    @pytest.mark.asyncio
    async def test_realistic_adk_workflow_simulation(self):
        """Test realistic ADK workflow with Analyst -> Planner -> Guard loop."""
        processor = EventStreamProcessor({
            "ReportAnalyst": "health_analysis",
            "LifestylePlanner": "current_plan",
            "SafetyGuard": "validation_result"
        })

        # Simulate real workflow:
        # 1. Analyst runs once
        # 2. Planner-Guard loop runs 2 iterations (reject then approve)
        events = [
            self.create_mock_event("ReportAnalyst", "Health metrics: cholesterol=250"),
            self.create_mock_event("LifestylePlanner", "Plan v1: reduce fat"),
            self.create_mock_event("SafetyGuard", "REJECT: too vague"),
            self.create_mock_event("LifestylePlanner", "Plan v2: reduce saturated fat to <7% calories"),
            self.create_mock_event("SafetyGuard", "APPROVE: plan is safe"),
        ]

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream())

        # Should have latest outputs from each agent
        assert outputs["health_analysis"] == "Health metrics: cholesterol=250"
        assert outputs["current_plan"] == "Plan v2: reduce saturated fat to <7% calories"
        assert outputs["validation_result"] == "APPROVE: plan is safe"

    @pytest.mark.asyncio
    async def test_large_event_stream_performance(self, processor):
        """Test handling large number of events efficiently."""
        # Create 1000 events from 3 agents
        # i=0 -> Agent1, i=1 -> Agent2, i=2 -> Agent3, i=3 -> Agent1, ...
        # i=999 -> 999 % 3 = 0 -> Agent1
        # Last Agent1: i=999, Last Agent2: i=998, Last Agent3: i=997
        events = []
        for i in range(1000):
            agent = f"Agent{(i % 3) + 1}"
            events.append(self.create_mock_event(agent, f"output_{i}"))

        async def mock_stream():
            for e in events:
                yield e

        outputs = await processor.process_events(mock_stream())

        # Should have 3 outputs (one per agent, last wins)
        assert len(outputs) == 3
        # Verify last outputs are correct (last wins principle)
        assert outputs["output1"] == "output_999"  # Last Agent1 event (i=999: 999%3=0, 0+1=1)
        assert outputs["output2"] == "output_997"  # Last Agent2 event (i=997: 997%3=1, 1+1=2)
        assert outputs["output3"] == "output_998"  # Last Agent3 event (i=998: 998%3=2, 2+1=3)
