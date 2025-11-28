"""SafetyGuardAgent - Plan validation and safety checking agent.

Validates lifestyle plans against safety policies using Google ADK.

Safety Rules:
- Safety policies from resources/policies/safety_rules.yaml are injected via InstructionProvider
- Validates against all rules before approving plan
- Provides structured feedback for rejection cases

Logging:
- Execution tracing with approval/rejection decisions handled by orchestrator

ADK InstructionProvider Pattern:
- Uses InstructionProvider to dynamically inject state at runtime
- Uses inject_session_state utility to replace {safety_rules_yaml}, {current_plan}, {health_analysis}
- This pattern is required for LoopAgent to access session state reliably
- Reference: https://google.github.io/adk-docs/sessions/state/
"""

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.exit_loop_tool import exit_loop
from google.adk.tools import FunctionTool
from google.adk.models import Gemini
from google.genai.types import GenerateContentConfig
from google.adk.utils.instructions_utils import inject_session_state

from ..ai import load_prompt
from ..common.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SafetyGuardAgent:
    """Factory for creating SafetyGuard ADK agent.

    Responsibilities:
    - Validate current_plan against safety_rules.yaml
    - Check for medical claims without sources
    - Detect potentially harmful recommendations
    - Return: decision (APPROVE/REJECT), feedback, violations
    - On REJECT: provide specific feedback for Planner retry
    - On APPROVE: call exit_loop tool to terminate loop

    System prompt loaded from: resources/prompts/guard_prompt.txt
    Safety rules injected via InstructionProvider from: resources/policies/safety_rules.yaml
    """

    @staticmethod
    async def _build_guard_instruction(readonly_context: ReadonlyContext) -> str:
        """InstructionProvider: Dynamically build Guard instruction with session state injection.

        This function is called by ADK at runtime and receives the current session context.
        It uses inject_session_state to replace placeholders with actual values from session.state.

        Args:
            readonly_context: ADK readonly context with session state access

        Returns:
            Fully populated instruction string with all placeholders replaced
        """
        # Load the prompt template (contains {placeholders})
        prompt_template = load_prompt("guard_prompt")

        # Use ADK's inject_session_state utility to replace {safety_rules_yaml},
        # {current_plan}, {health_analysis} with actual values from session.state
        populated_instruction = await inject_session_state(
            prompt_template,
            readonly_context
        )

        return populated_instruction

    @staticmethod
    def create_agent(model_name: str = "gemini-2.5-flash") -> LlmAgent:
        """Create ADK LlmAgent for safety validation with InstructionProvider.

        Args:
            model_name: Gemini model name (default: gemini-2.5-flash)

        Returns:
            Configured LlmAgent instance with InstructionProvider and termination tool
        """
        # Create ADK Gemini model instance
        gemini_model = Gemini(model=model_name)

        # Create generation config with temperature and max_tokens from Config
        gen_config = GenerateContentConfig(
            temperature=Config.TEMPERATURE,
            max_output_tokens=Config.MAX_TOKENS
        )

        logger.info(
            "SafetyGuard agent created with InstructionProvider",
            model=model_name,
            temperature=Config.TEMPERATURE,
            max_output_tokens=Config.MAX_TOKENS,
            output_key="validation_result",
            description="Validates plans against safety policies and terminates loop on approval",
            tools=["exit_loop"],
            instruction_provider="SafetyGuardAgent._build_guard_instruction"
        )

        # ADK LlmAgent with InstructionProvider
        # The instruction parameter accepts a callable (function) that receives ReadonlyContext
        # and returns the populated instruction string
        return LlmAgent(
            name="SafetyGuard",
            model=gemini_model,
            instruction=SafetyGuardAgent._build_guard_instruction,  # InstructionProvider function
            generate_content_config=gen_config,
            output_key="validation_result",
            tools=[FunctionTool(exit_loop)],  # Use ADK's built-in exit_loop tool
            description="Validates plans against safety policies and terminates loop on approval"
        )
