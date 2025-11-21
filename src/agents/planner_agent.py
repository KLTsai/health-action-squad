"""LifestylePlannerAgent - Lifestyle plan generation agent.

Generates personalized lifestyle plans based on health metrics and user profile.
MUST inherit from google.adk.agents.Agent.
"""

from typing import Dict

# from google.adk.agents import Agent  # Uncomment when ADK is installed

from ..domain.state import SessionState, WorkflowStatus
from ..common.config import Config
from ..utils.logger import AgentLogger


class LifestylePlannerAgent:  # TODO: Inherit from Agent when ADK is installed
    """LifestylePlannerAgent generates personalized lifestyle plans.

    Responsibilities:
    - Combine health_metrics, risk_tags, and user_profile
    - Generate Markdown lifestyle plan (max 1500 words)
    - Use ADK Tool for knowledge search (GoogleSearchTool)
    - Medical recommendations MUST cite sources
    - Incorporate Guard feedback in retry loop

    System prompt loaded from: resources/prompts/planner_prompt.txt
    """

    def __init__(self):
        """Initialize LifestylePlannerAgent."""
        self.config = Config()
        self.logger = AgentLogger("LifestylePlannerAgent")

        # Load system prompt from file (NOT hardcoded)
        self.system_prompt = self._load_prompt()

        # TODO: Initialize ADK tools
        # self.search_tool = GoogleSearchTool()

        self.logger.info("LifestylePlannerAgent initialized")

    def _load_prompt(self) -> str:
        """Load system prompt from resources/prompts/planner_prompt.txt.

        Returns:
            System prompt text
        """
        return Config.get_prompt(Config.PLANNER_PROMPT_PATH)

    def execute(self, state: SessionState) -> SessionState:
        """Generate lifestyle plan.

        Args:
            state: Current session state with health_metrics, risk_tags, user_profile

        Returns:
            Updated SessionState with current_plan

        Raises:
            ValueError: If required state data is missing
        """
        self.logger.set_session(state.session_id)
        self.logger.set_iteration(state.retry_count + 1)

        self.logger.info(
            "Starting lifestyle plan generation",
            retry_count=state.retry_count,
            risk_tags=state.risk_tags,
        )

        # Validate state
        if not state.health_metrics:
            raise ValueError("Health metrics required for plan generation")

        # Build planning context
        context = self._build_planning_context(state)

        # TODO: Implement ADK agent execution
        # 1. Use ADK ModelClient to call Gemini
        # 2. Pass system_prompt, context, and previous feedback (if retry)
        # 3. Use search_tool for medical knowledge lookup
        # 4. Generate Markdown plan (max 1500 words)

        # Placeholder implementation
        plan = self._generate_plan_placeholder(context)

        # Update state
        updated_state = state.update(current_plan=plan, status=WorkflowStatus.REVIEWING)

        self.logger.trace_state_transition(
            from_state=state.status.value,
            to_state=updated_state.status.value,
            plan_length=len(plan),
        )

        self.logger.info(
            "Lifestyle plan generated",
            plan_length=len(plan),
            iteration=state.retry_count + 1,
        )

        return updated_state

    def _build_planning_context(self, state: SessionState) -> Dict:
        """Build context for plan generation.

        Args:
            state: Current session state

        Returns:
            Context dictionary for planner
        """
        context = {
            "health_metrics": state.health_metrics,
            "risk_tags": state.risk_tags,
            "user_profile": state.user_profile,
            "retry_count": state.retry_count,
        }

        # Include previous feedback if this is a retry
        if state.feedback_history:
            context["previous_feedback"] = state.feedback_history

        return context

    def _generate_plan_placeholder(self, context: Dict) -> str:
        """Placeholder for plan generation.

        TODO: Replace with actual ADK agent implementation.

        Args:
            context: Planning context

        Returns:
            Generated plan in Markdown
        """
        risk_tags = context.get("risk_tags", [])
        user_profile = context.get("user_profile", {})

        plan = f"""# Personalized Lifestyle Plan

## Overview
This plan is tailored based on your health report and identified risk factors.

**Identified Risk Factors:** {', '.join(risk_tags) if risk_tags else 'None'}

## Nutrition Recommendations

### Dietary Guidelines
- Focus on heart-healthy foods rich in omega-3 fatty acids
- Increase fiber intake through whole grains, fruits, and vegetables
- Limit saturated fats and trans fats
- Reduce sodium intake to less than 2,300mg per day

### Meal Planning
- Start your day with a balanced breakfast including whole grains and protein
- Include at least 5 servings of fruits and vegetables daily
- Choose lean proteins (fish, poultry, legumes)
- Stay hydrated with 8-10 glasses of water daily

## Physical Activity Plan

### Weekly Exercise Schedule
- **Aerobic Exercise**: 150 minutes of moderate-intensity activity per week
  - Example: 30 minutes of brisk walking, 5 days a week
- **Strength Training**: 2 sessions per week
  - Focus on major muscle groups
- **Flexibility**: Daily stretching routine (10-15 minutes)

### Getting Started
1. Start with low-intensity activities
2. Gradually increase duration and intensity
3. Listen to your body and rest when needed

## Sleep Hygiene

- Aim for 7-9 hours of quality sleep per night
- Maintain consistent sleep schedule
- Create a relaxing bedtime routine
- Limit screen time before bed

## Stress Management

- Practice mindfulness or meditation (10-15 minutes daily)
- Engage in hobbies and activities you enjoy
- Maintain social connections
- Consider professional support if needed

## Medical Follow-up

⚠️ **Important**: Schedule a follow-up with your healthcare provider to:
- Review these recommendations
- Monitor progress
- Adjust treatment plan as needed

## Progress Tracking

Track the following metrics weekly:
- Weight and BMI
- Blood pressure (if applicable)
- Physical activity minutes
- Sleep quality

---

**Disclaimer**: This plan is for informational purposes only. Always consult with your healthcare provider before making significant lifestyle changes.

**Sources**:
- American Heart Association Guidelines
- CDC Physical Activity Guidelines
- National Institutes of Health Nutrition Recommendations
"""

        return plan
