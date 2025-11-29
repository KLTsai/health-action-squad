"""Abstract base class for workflow executors.

Defines the interface for workflow execution strategies, enabling
dependency inversion and strategy pattern.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class WorkflowExecutor(ABC):
    """Abstract interface for workflow execution strategies.

    This enables dependency inversion - Orchestrator depends on abstraction,
    not concrete implementations.

    Implementations:
    - RunnerBasedExecutor: Uses ADK Runner (recommended)
    - EventStreamExecutor: Uses manual event processing (deprecated)

    Design Pattern: Strategy Pattern
    Benefits:
    - High cohesion: Each executor encapsulates ONE execution strategy
    - Low coupling: Orchestrator depends on interface, not implementation
    - Testability: Easy to mock for unit tests
    - Extensibility: Add new strategies without modifying orchestrator
    """

    @abstractmethod
    async def execute(
        self,
        workflow: Any,
        initial_state: Dict[str, Any],
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Execute workflow and return final state.

        Args:
            workflow: ADK workflow agent (SequentialAgent)
            initial_state: Initial session state dictionary
            session_id: Unique session identifier
            user_id: User identifier

        Returns:
            Final session state after workflow execution

        Raises:
            Exception: If workflow execution fails

        Note:
            This method encapsulates ALL execution logic, keeping it
            highly cohesive within the executor implementation.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources (if any).

        Called when orchestrator is done using the executor.
        Implementations should release any held resources.
        """
        pass
