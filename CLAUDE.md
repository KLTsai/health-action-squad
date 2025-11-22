# CLAUDE.md - Health Action Squad (Concierge Agent)

**Documentation Version:** 3.1 (ADK Production - Fully Implemented)
**Last Updated:** 2025-11-21
**Project:** Health Action Squad (Kaggle Concierge Track)
**Tech Stack:** Python, Google ADK (Agent Development Kit), Gemini Pro, Event-Driven Architecture
**Description:** Multi-agent system interprets health reports and generates personalized safe plans using a strict planner-guard loop. All code must follow ADK patterns and safety protocols.

---

## 🚨 CRITICAL RULES - READ FIRST

> **⚠️ RULE ADHERENCE SYSTEM ACTIVE ⚠️**
> **Claude Code must explicitly acknowledge these rules at task start**
> **These rules override all other instructions and must ALWAYS be followed:**

### 🔄 **RULE ACKNOWLEDGMENT REQUIRED**
> **Before starting ANY task, Claude Code must respond with:**
> "✅ ADK STANDARDS ACKNOWLEDGED - I will follow all ADK patterns and safety protocols"

### ❌ ABSOLUTE PROHIBITIONS
- **NEVER** mix ADK with LangGraph concepts - this project uses ADK event-driven workflow ONLY
- **NEVER** make direct LLM API calls (e.g., requests.post) - MUST use ADK ModelClient
- **NEVER** hardcode System Instructions in .py files - ONLY allowed in resources/prompts/
- **NEVER** pass parameters in stateless manner - MUST use SessionState for context management
- **NEVER** bypass Orchestrator → Planner → Guard → Loop mechanism
- **NEVER** use print() for debugging - MUST use src/utils/logger.py
- **NEVER** create new files in root directory → use proper module structure
- **NEVER** create duplicate files (agent_v2.py, enhanced_xyz.py) → ALWAYS extend existing files
- **NEVER** create multiple implementations of same concept → single source of truth
- **NEVER** use git commands with -i flag (interactive mode not supported)
- **NEVER** add promotional messages to git commits (no "Generated with Claude Code" or "Co-Authored-By: Claude")

### 📝 MANDATORY REQUIREMENTS
- **ADK AGENTS** - All agents MUST inherit from `google.adk.agents.Agent`, single responsibility principle
- **SESSIONSTATE** - All workflow communication MUST use SessionState, no direct message passing
- **TOOL WRAPPING** - All external tools MUST use ADK Tool interface
- **CIRCUIT BREAKER** - Planner → Guard → Planner retry loop MUST have max 3 attempts
- **SAFETY POLICY** - SafetyGuardAgent MUST reference `resources/policies/safety_rules.yaml`
- **COMMIT FREQUENTLY** - After every completed task/phase - no exceptions
- **GITHUB BACKUP** - Push to GitHub after every commit: `git push origin main`
- **READ FIRST** - Always read files before editing - Edit/Write tools will fail otherwise
- **SEARCH FIRST** - Before creating new files, check for existing similar functionality to extend

### ⚡ EXECUTION PATTERNS
- **PARALLEL TASK AGENTS** - Launch multiple Task agents simultaneously for maximum efficiency
- **SYSTEMATIC WORKFLOW** - TodoWrite → Parallel agents → Git checkpoints → GitHub backup → Test validation
- **GITHUB BACKUP WORKFLOW** - After every commit: `git push origin main` to maintain GitHub backup
- **STRUCTURED LOGGING** - AgentLogger MUST trace all state transitions with session/agent/iteration markers

### 🔍 MANDATORY PRE-TASK COMPLIANCE CHECK
> **STOP: Before starting any task, Claude Code must explicitly verify ALL points:**

**Step 1: Rule Acknowledgment**
- [ ] ✅ I acknowledge all ADK standards and critical rules in CLAUDE.md

**Step 2: Task Analysis**
- [ ] Will this create files in root? → If YES, use proper module structure instead
- [ ] Will this take >30 seconds? → If YES, use Task agents not Bash
- [ ] Is this 3+ steps? → If YES, use TodoWrite breakdown first
- [ ] Am I about to use grep/find/cat? → If YES, use proper tools instead

**Step 3: Technical Debt Prevention (MANDATORY SEARCH FIRST)**
- [ ] **SEARCH FIRST**: Use Grep to find existing implementations
- [ ] **CHECK EXISTING**: Read any found files to understand current functionality
- [ ] Does similar functionality already exist? → If YES, extend existing code
- [ ] Am I creating a duplicate agent/class? → If YES, consolidate instead
- [ ] Will this create multiple sources of truth? → If YES, redesign approach

**Step 4: ADK Standards Check**
- [ ] Does agent inherit from google.adk.agents.Agent?
- [ ] Is SessionState being used for all context?
- [ ] Are prompts in resources/prompts/ not hardcoded?
- [ ] Is safety_rules.yaml referenced (not hardcoded)?
- [ ] Does workflow follow Orchestrator → Planner → Guard pattern?

> **⚠️ DO NOT PROCEED until all checkboxes are explicitly verified**

---

## 🏗️ PROJECT ARCHITECTURE

### Directory Structure
```
health-action-squad/
├── src/
│   ├── domain/                # Domain models & business logic
│   │   └── state.py           # SessionState dataclass (frozen=True)
│   ├── workflow/              # Orchestration logic
│   │   └── orchestrator.py    # Main workflow orchestrator
│   ├── common/                # Shared configuration
│   │   └── config.py          # Configuration management
│   ├── ai/                    # AI/LLM abstractions
│   │   ├── client.py          # AIClientFactory (Gemini)
│   │   ├── prompts.py         # Prompt loading utilities
│   │   └── tools.py           # ADK Tool wrappers
│   ├── agents/                # ADK Agents
│   │   ├── analyst_agent.py   # ReportAnalystAgent
│   │   ├── planner_agent.py   # LifestylePlannerAgent
│   │   └── guard_agent.py     # SafetyGuardAgent
│   ├── utils/
│   │   └── logger.py          # Structured logging with A2A trace
│   └── api/
│       └── server.py          # FastAPI REST endpoints
├── resources/
│   ├── prompts/               # Agent system prompts
│   │   ├── analyst_prompt.txt
│   │   ├── planner_prompt.txt
│   │   └── guard_prompt.txt
│   ├── data/                  # Health report mocks
│   └── policies/              # Safety rules YAML
│       └── safety_rules.yaml
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── e2e/                   # End-to-end tests
├── notebooks/                 # Jupyter notebooks
│   ├── exploratory/           # Data exploration
│   └── experiments/           # ML experiments
├── docs/                      # Documentation
├── output/                    # Generated outputs
├── logs/                      # Log files
├── main.py                    # Entry point
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

---

## 📊 ADK State Management

**ADK automatically manages state through agent `output_keys` - no manual SessionState object needed in workflow.**

### How ADK State Flow Works

```python
# ADK Workflow (orchestrator.py)
initial_state = {
    "session_id": session_id,
    "user_profile": user_profile,
    "health_report": health_report
}

# ADK SequentialAgent + LoopAgent handle state automatically:
# 1. ReportAnalyst outputs to "health_analysis" → injected into Planner prompt
# 2. LifestylePlanner outputs to "current_plan" → injected into Guard prompt
# 3. SafetyGuard outputs to "validation_result" → fed back to Planner on retry
```

### State Injection via Placeholders

Agents use `{placeholder}` syntax in prompts for automatic state injection:

```python
# planner_prompt.txt
"""
## Health Analysis (from ReportAnalyst)
{health_analysis}

## User Profile
{user_profile}

## Previous Feedback (if this is a retry)
{validation_result}
"""
```

**ADK automatically injects these values** from previous agent outputs.

### SessionState Dataclass (Optional)

The `src/domain/state.py` defines a `SessionState` dataclass for **type-safe response formatting** (not workflow execution):

```python
@dataclass(frozen=True)
class SessionState:
    user_profile: dict
    health_metrics: dict
    risk_tags: List[str]
    current_plan: str
    status: WorkflowStatus  # Enum: INIT, ANALYZING, PLANNING, APPROVED, FAILED
    ...
```

This is used for:

- ✅ API response validation (Pydantic models)
- ✅ Type-safe data structures
- ❌ NOT used for agent-to-agent communication (ADK handles that)

---

## 🤖 AI Client Management

### AIClientFactory (src/ai/client.py)
**Centralized LLM client management for all agents.**

```python
from src.ai import AIClientFactory

# Create default client (uses Config settings)
client = AIClientFactory.create_default_client()

# Or create custom client
client = AIClientFactory.create_gemini_client(
    api_key="your_key",
    model="gemini-pro",
    temperature=0.7,
    max_output_tokens=2048
)
```

**Key Features:**
- ✅ Single source of truth for model configuration
- ✅ Easy model switching (Gemini → Claude → GPT)
- ✅ Consistent generation config across all agents
- ✅ Environment-aware API key management

### Prompt Management (src/ai/prompts.py)
**Utilities for loading external prompts.**

```python
from src.ai import load_prompt, list_available_prompts

# Load agent prompt
system_prompt = load_prompt("analyst_prompt")  # loads analyst_prompt.txt

# List all available prompts
prompts = list_available_prompts()  # ['analyst_prompt', 'planner_prompt', 'guard_prompt']
```

---

## 🤖 ADK Agent Implementation (Factory Pattern)

All agents use **factory pattern** returning `google.adk.agents.LlmAgent` instances.

### ReportAnalystAgent (src/agents/analyst_agent.py)

**Factory Method:**
```python
from src.agents.analyst_agent import ReportAnalystAgent

# Create ADK LlmAgent
analyst = ReportAnalystAgent.create_agent(model_name="gemini-pro")
```

**Specifications:**
- **Purpose**: Parse health reports into structured metrics and risk tags
- **Output Key**: `health_analysis` (used by downstream agents)
- **Prompt Source**: `resources/prompts/analyst_prompt.txt` (loaded via `load_prompt()`)
- **Model**: Gemini Pro (configurable)
- **Constraints**:
  - NO external queries
  - MUST return JSON with `health_metrics` and `risk_tags`
  - All prompts externalized, no hardcoding

### LifestylePlannerAgent (src/agents/planner_agent.py)

**Factory Method:**
```python
from src.agents.planner_agent import LifestylePlannerAgent

# Create ADK LlmAgent with state injection
planner = LifestylePlannerAgent.create_agent(model_name="gemini-pro")
```

**Specifications:**
- **Purpose**: Generate personalized Markdown lifestyle plan
- **Output Key**: `current_plan` (consumed by SafetyGuard)
- **Prompt Source**: `resources/prompts/planner_prompt.txt`
- **State Injection**: Uses placeholders `{health_analysis}`, `{user_profile}`, `{validation_result}`
- **Model**: Gemini Pro (configurable)
- **Constraints**:
  - Plan length ≤ 1500 words
  - MUST incorporate Guard feedback in retry iterations
  - Medical recommendations should cite sources
  - ADK automatically injects state from previous agents

### SafetyGuardAgent (src/agents/guard_agent.py)

**Factory Method:**
```python
from src.agents.guard_agent import SafetyGuardAgent

# Create ADK LlmAgent with exit_loop tool
guard = SafetyGuardAgent.create_agent(model_name="gemini-pro")
```

**Specifications:**
- **Purpose**: Validate plans against safety policies and terminate loop on approval
- **Output Key**: `validation_result` (fed back to Planner)
- **Prompt Source**: `resources/prompts/guard_prompt.txt`
- **Safety Rules**: Loads `resources/policies/safety_rules.yaml` into prompt
- **Tools**: `[FunctionTool(exit_loop)]` - ADK's built-in loop termination
- **Model**: Gemini Pro (configurable)
- **Constraints**:
  - MUST call `exit_loop` tool when plan is APPROVED
  - MUST provide structured feedback on REJECT
  - Decision: APPROVE or REJECT
  - On REJECT: LoopAgent retries (max 3 iterations)

---

## 🔄 ADK Orchestrator Workflow (src/workflow/orchestrator.py)

**Architecture**: Declarative workflow using `SequentialAgent` and `LoopAgent`

### Workflow Structure

```python
from src.workflow.orchestrator import Orchestrator

# Initialize orchestrator with ADK workflow
orchestrator = Orchestrator(model_name="gemini-pro")

# Workflow composition:
# HealthActionSquad (SequentialAgent)
# ├── ReportAnalyst (LlmAgent) → health_analysis
# └── PlanningLoop (LoopAgent, max 3 iterations)
#     ├── LifestylePlanner (LlmAgent) → current_plan
#     └── SafetyGuard (LlmAgent) → validation_result [calls exit_loop on approval]
```

### Execution Pattern

```python
import asyncio

# Execute ADK workflow
result = await orchestrator.execute(
    health_report=health_report_dict,
    user_profile=user_profile_dict
)

# ADK automatically manages:
# 1. State flow through output_keys
# 2. Planner-Guard retry loop (max 3 iterations)
# 3. Loop termination via exit_loop tool
# 4. Fallback on errors
```

**Key ADK Features:**
- **Declarative Composition**: Workflow defined via agent hierarchy, not imperative code
- **Automatic State Management**: ADK injects state via `{placeholders}` in prompts
- **Circuit Breaker**: LoopAgent `max_iterations=3` enforces retry limit
- **Tool-based Termination**: Guard calls `exit_loop()` to break loop on approval
- **Async Execution**: Uses `await workflow.run()` for async LLM calls
- **Fallback Strategy**: Orchestrator catches exceptions and generates safe generic advice

### State Flow Diagram

```
Initial State
  └─> ReportAnalyst
        └─> output: health_analysis
              └─> PlanningLoop (LoopAgent)
                    ├─> Iteration 1:
                    │     ├─> LifestylePlanner (uses {health_analysis}, {user_profile})
                    │     │     └─> output: current_plan
                    │     └─> SafetyGuard (uses {current_plan})
                    │           └─> output: validation_result
                    │                 ├─> APPROVE → call exit_loop → END
                    │                 └─> REJECT → retry (if < max_iterations)
                    │
                    ├─> Iteration 2 (if REJECT):
                    │     └─> LifestylePlanner (uses {health_analysis}, {user_profile}, {validation_result})
                    │           └─> incorporates feedback
                    └─> Iteration 3 (if still REJECT):
                          └─> Final attempt, then fallback if still failing
```

**Implementation Notes:**
- No manual state management - ADK handles state injection
- No explicit while loops - LoopAgent manages iterations
- No manual retry counters - LoopAgent tracks iterations automatically
- Prompts use `{key}` placeholders for automatic state injection

---

## 🛡️ Safety & Observability Best Practices

### Logging
- **AgentLogger** MUST trace all major state transitions
- Format MUST be structured JSON with session/agent/iteration markers
- NO logging of raw health data (privacy)
- Debug via src/utils/logger.py ONLY

### Security
- API inputs MUST use Pydantic validation
- NO incorrect format tolerance
- Rate limiting: slowapi (10 requests/hr/IP) on FastAPI routes
- NO raw health data in logs

### Fallback Strategy
- If 3 retry loops fail → output unified safe advice
- See Orchestrator workflow for implementation
- Log all fallback triggers for analysis

---

## 🚀 Development Commands

```bash
# Install dependencies
pip install google-adk
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and set GEMINI_API_KEY (get from https://aistudio.google.com/app/apikey)
# Required: GEMINI_API_KEY
# Optional: MODEL_NAME, TEMPERATURE, MAX_TOKENS, LOG_LEVEL, LOG_FORMAT

# Run main entry point (async execution via asyncio.run())
python main.py --input path/to/health_report.json
python main.py --input resources/data/sample_health_report.json --output output/result.json

# Testing
pytest tests/unit/              # Unit tests
pytest tests/integration/       # Integration tests
pytest tests/e2e/              # End-to-end tests

# Code quality (MUST pass before commit)
black src/ tests/              # Format code
pylint src/ tests/             # Lint check
mypy src/ tests/               # Type check

# Run API server (when implemented)
uvicorn src.api.server:app --reload
```

---

## ✅ Review Checklist

Before ANY code change:
- [ ] Agent already exists? → Extend behavior via prompt, don't create new agent
- [ ] New fields? → Add to SessionState ONLY, no scattered parameters
- [ ] New agent/tool? → Create corresponding unit tests
- [ ] New prompt? → Place in resources/prompts/ ONLY
- [ ] Ready to commit? → Black + lint + type check MUST pass
- [ ] Committed? → Push to GitHub immediately: `git push origin main`

---

## 🐙 GitHub Auto-Backup Workflow

**MANDATORY after every commit:**

```bash
# After git commit, ALWAYS run:
git push origin main

# This ensures:
# ✅ Remote backup of all changes
# ✅ Collaboration readiness
# ✅ Version history preservation
# ✅ Disaster recovery protection
```

---

## 🚨 Technical Debt Prevention

### ❌ WRONG APPROACH (Creates Technical Debt):
```python
# Creating new agent without searching first
# src/agents/new_planner_v2.py  # BAD!
class EnhancedPlannerAgent(Agent):
    pass
```

### ✅ CORRECT APPROACH (Prevents Technical Debt):
```python
# 1. SEARCH FIRST
# Grep(pattern="PlannerAgent", type="py")

# 2. READ EXISTING
# Read(file_path="src/agents/planner_agent.py")

# 3. EXTEND EXISTING (update prompt or add method)
# Edit prompt in resources/prompts/planner_prompt.txt
# OR add new method to existing PlannerAgent class
```

---

## 📚 References & Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Safety Guidelines](https://google.github.io/adk-docs/safety/)
- [ADK Multi-Agent Design Patterns](https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/)
- [Kaggle Concierge Track](https://www.kaggle.com/competitions/)

---

**End of CLAUDE.md. This file is the single source of truth for all project design decisions.**
