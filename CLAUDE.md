# CLAUDE.md - Health Action Squad (Concierge Agent)

**Documentation Version:** 3.0 (ADK Production Edition)
**Last Updated:** 2025-11-20
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

## 📊 SessionState Standard

All context MUST flow through this immutable state object:

```python
@dataclass(frozen=True)
class SessionState:
    user_profile: dict              # Fixed user data
    health_metrics: dict            # Parsed health report results
    risk_tags: List[str]            # Risk flags
    current_plan: str               # Markdown plan
    feedback_history: List[Dict]    # Feedback from each Guard iteration
    retry_count: int                # Planner-Guard loop counter
    status: str                     # Workflow status (enum only)
```

**Rules:**
- MUST be immutable (frozen=True)
- NO stateless parameter passing
- ALL agents read/write through SessionState
- Status MUST be enum: INIT, ANALYZING, PLANNING, REVIEWING, APPROVED, FAILED

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

## 🤖 Agent Responsibilities

### ReportAnalystAgent
- **Purpose**: Parse health reports into metrics/risk tags
- **Input**: Raw health report (from SessionState)
- **Output**: Updated SessionState with health_metrics and risk_tags
- **LLM Client**: Uses AIClientFactory.create_default_client() (Gemini Pro)
- **Constraints**:
  - NO external queries
  - MUST conform to SessionState schema
  - MUST use prompt from resources/prompts/analyst_prompt.txt
  - Uses centralized AI client from ai/ module

### LifestylePlannerAgent
- **Purpose**: Generate personalized Markdown lifestyle plan
- **Input**: health_metrics, risk_tags, user_profile (from SessionState)
- **Output**: Updated SessionState with current_plan
- **LLM Client**: Uses AIClientFactory.create_default_client() (Gemini Pro)
- **Constraints**:
  - MUST use ADK Tool for knowledge search (MedicalKnowledgeSearchTool)
  - Plan length ≤ 1500 words
  - Medical recommendations MUST cite sources
  - MUST incorporate Guard feedback in retry loop
  - MUST use prompt from resources/prompts/planner_prompt.txt
  - Uses centralized AI client from ai/ module

### SafetyGuardAgent
- **Purpose**: Validate current_plan against safety policies
- **Input**: current_plan, risk_tags (from SessionState)
- **Output**: Updated SessionState with feedback_history and decision
- **LLM Client**: Uses AIClientFactory.create_default_client() (Gemini Pro)
- **Constraints**:
  - MUST use resources/policies/safety_rules.yaml
  - MUST output: decision (APPROVE/REJECT), feedback, violations
  - On REJECT: trigger Planner retry (max 3)
  - MUST use prompt from resources/prompts/guard_prompt.txt
  - Uses centralized AI client from ai/ module

---

## 🔄 Orchestrator Workflow

```python
# Simplified workflow pattern
while state.retry_count < MAX_RETRIES:
    # Planner generates plan
    plan = planner.execute(state)
    state = update_state(state, current_plan=plan)

    # Guard validates plan
    result = guard.execute(state)

    if result.decision == "APPROVE":
        return state.final_output

    # Update state with feedback for retry
    state = update_state(
        state,
        feedback_history=state.feedback_history + [result.feedback],
        retry_count=state.retry_count + 1
    )

# Circuit breaker triggered
fallback = generate_fallback(state.risk_tags)
```

**Key Points:**
- Max 3 retry attempts
- State is immutable - always create new state
- Fallback generates safe generic advice on failure

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

# Run main entry point
python main.py --input path/to/health_report.json

# Testing
pytest tests/unit/              # Unit tests
pytest tests/integration/       # Integration tests
pytest tests/e2e/              # End-to-end tests

# Code quality (MUST pass before commit)
black src/ tests/              # Format code
pylint src/ tests/             # Lint check
mypy src/ tests/               # Type check

# Run API server
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
