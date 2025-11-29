"""Factory for creating ADK agents and workflows.

Centralizes all agent creation logic in one place for high cohesion.
"""

from typing import Tuple
from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent

from ...agents.analyst_agent import ReportAnalystAgent
from ...agents.planner_agent import LifestylePlannerAgent
from ...agents.guard_agent import SafetyGuardAgent
from ...domain.state import MAX_RETRIES
from ...utils.logger import get_logger

logger = get_logger(__name__)


class AgentFactory:
    """Factory for creating ADK agents and workflows.

    High Cohesion:
    - All agent creation logic centralized in one place
    - Encapsulates agent configuration details
    - Single responsibility: create agents

    Low Coupling:
    - No dependencies on Orchestrator or Executors
    - Can be used independently
    - Easy to test and mock

    Design Pattern: Factory Method
    Benefits:
    - Centralized creation makes configuration changes easy
    - Easy to add new agent types
    - Testable without running full workflow
    """

    @staticmethod
    def create_workflow(model_name: str = "gemini-2.5-flash") -> SequentialAgent:
        """Create complete workflow with all agents.

        This is the ONLY place where the workflow structure is defined.
        Changing workflow composition only requires modifying this method.

        Args:
            model_name: Gemini model name for all agents

        Returns:
            Configured SequentialAgent workflow with structure:
            SequentialAgent[
                ReportAnalyst,
                LoopAgent[
                    LifestylePlanner,
                    SafetyGuard
                ]
            ]

        Note:
            Workflow structure:
            1. ReportAnalyst analyzes health report once
            2. LoopAgent manages Planner-Guard retry loop
            3. Guard validates plan and provides feedback for retries
        """
        # Create individual agents
        analyst = ReportAnalystAgent.create_agent(model_name)
        planner = LifestylePlannerAgent.create_agent(model_name)
        guard = SafetyGuardAgent.create_agent(model_name)

        logger.info(
            "ADK agents created via AgentFactory",
            agents=["ReportAnalyst", "LifestylePlanner", "SafetyGuard"],
            model=model_name
        )

        # Create Planner-Guard retry loop
        planning_loop = LoopAgent(
            name="PlanningLoop",
            sub_agents=[planner, guard],
            max_iterations=MAX_RETRIES,
            description=f"Planner-Guard retry loop with max {MAX_RETRIES} iterations"
        )

        # Create main sequential workflow
        workflow = SequentialAgent(
            name="HealthActionSquad",
            sub_agents=[analyst, planning_loop],
            description="Health report analysis → lifestyle plan generation with safety validation"
        )

        logger.info(
            "Workflow created via AgentFactory",
            structure="SequentialAgent[Analyst, LoopAgent[Planner, Guard]]",
            max_loop_iterations=MAX_RETRIES
        )

        return workflow

    @staticmethod
    def create_agents(
        model_name: str = "gemini-2.5-flash"
    ) -> Tuple[LlmAgent, LlmAgent, LlmAgent]:
        """Create individual agents without workflow composition.

        Useful for testing, debugging, or custom workflow assembly.

        Args:
            model_name: Gemini model name

        Returns:
            Tuple of (analyst, planner, guard) agents
        """
        return (
            ReportAnalystAgent.create_agent(model_name),
            LifestylePlannerAgent.create_agent(model_name),
            SafetyGuardAgent.create_agent(model_name)
        )
