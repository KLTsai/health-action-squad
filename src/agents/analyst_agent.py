"""ReportAnalystAgent - Health report parsing agent.

Parses health reports into structured metrics and risk tags.
MUST inherit from google.adk.agents.Agent.
"""

from typing import Dict, List
from google.generativeai import GenerativeModel

# from google.adk.agents import Agent  # Uncomment when ADK is installed

from ..domain.state import SessionState, WorkflowStatus
from ..utils.logger import AgentLogger
from ..ai import AIClientFactory, load_prompt


class ReportAnalystAgent:  # TODO: Inherit from Agent when ADK is installed
    """ReportAnalystAgent parses health reports.

    Responsibilities:
    - Parse raw health report data
    - Extract health metrics (cholesterol, blood pressure, etc.)
    - Identify risk tags based on report findings
    - NO external queries allowed
    - Output MUST conform to SessionState schema

    System prompt loaded from: resources/prompts/analyst_prompt.txt
    """

    def __init__(self, model: GenerativeModel = None):
        """Initialize ReportAnalystAgent.

        Args:
            model: Optional GenerativeModel instance. If None, creates default client.
        """
        self.logger = AgentLogger("ReportAnalystAgent")

        # Use centralized AI client
        self.model = model or AIClientFactory.create_default_client()

        # Load system prompt from file (NOT hardcoded)
        self.system_prompt = self._load_prompt()

        self.logger.info("ReportAnalystAgent initialized with Gemini model")

    def _load_prompt(self) -> str:
        """Load system prompt from resources/prompts/analyst_prompt.txt.

        Returns:
            System prompt text
        """
        return load_prompt("analyst_prompt")

    def execute(self, state: SessionState, health_report: Dict) -> SessionState:
        """Parse health report and update state.

        Args:
            state: Current session state
            health_report: Raw health report data

        Returns:
            Updated SessionState with health_metrics and risk_tags

        Raises:
            ValueError: If health report is invalid
        """
        self.logger.set_session(state.session_id)
        self.logger.info("Starting health report analysis")

        # Validate input
        if not health_report:
            raise ValueError("Health report cannot be empty")

        # TODO: Implement ADK agent execution
        # 1. Use ADK ModelClient to call Gemini
        # 2. Pass system_prompt and health_report
        # 3. Parse response into health_metrics and risk_tags

        # Placeholder implementation
        health_metrics, risk_tags = self._parse_report_placeholder(health_report)

        # Update state
        updated_state = state.update(
            health_metrics=health_metrics,
            risk_tags=risk_tags,
            status=WorkflowStatus.PLANNING,
        )

        self.logger.trace_state_transition(
            from_state=state.status.value,
            to_state=updated_state.status.value,
            health_metrics_count=len(health_metrics),
            risk_tags_count=len(risk_tags),
        )

        self.logger.info(
            "Health report analysis completed",
            health_metrics=health_metrics,
            risk_tags=risk_tags,
        )

        return updated_state

    def _parse_report_placeholder(self, health_report: Dict) -> tuple[Dict, List[str]]:
        """Placeholder for report parsing.

        TODO: Replace with actual ADK agent implementation.

        Args:
            health_report: Raw health report

        Returns:
            Tuple of (health_metrics, risk_tags)
        """
        # Extract basic metrics from report
        health_metrics = {
            "cholesterol_total": health_report.get("cholesterol_total", 0),
            "cholesterol_ldl": health_report.get("cholesterol_ldl", 0),
            "cholesterol_hdl": health_report.get("cholesterol_hdl", 0),
            "blood_pressure_systolic": health_report.get("blood_pressure_systolic", 0),
            "blood_pressure_diastolic": health_report.get(
                "blood_pressure_diastolic", 0
            ),
            "glucose": health_report.get("glucose", 0),
            "bmi": health_report.get("bmi", 0),
        }

        # Identify risk tags based on metrics
        risk_tags = []

        # Cholesterol
        if health_metrics["cholesterol_total"] > 200:
            risk_tags.append("high_cholesterol")
        if health_metrics["cholesterol_ldl"] > 130:
            risk_tags.append("high_ldl")

        # Blood pressure
        if (
            health_metrics["blood_pressure_systolic"] > 130
            or health_metrics["blood_pressure_diastolic"] > 80
        ):
            risk_tags.append("high_blood_pressure")

        # Glucose
        if health_metrics["glucose"] > 100:
            risk_tags.append("elevated_glucose")

        # BMI
        if health_metrics["bmi"] > 25:
            risk_tags.append("overweight")
        elif health_metrics["bmi"] > 30:
            risk_tags.append("obese")

        return health_metrics, risk_tags
