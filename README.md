# Health Action Squad - Kaggle Concierge Agent

> **Multi-agent health concierge system powered by Google ADK**
>
> Interprets health reports and generates personalized, safety-validated lifestyle plans using a strict Planner-Guard loop architecture.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4.svg)](https://google.github.io/adk-docs/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🚀 Quick Start

### 1. Read CLAUDE.md First
**IMPORTANT**: Before any development work, read [CLAUDE.md](CLAUDE.md) - it contains essential rules and ADK standards that must be followed.

### 2. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY (get from https://aistudio.google.com/app/apikey)
# Required: GEMINI_API_KEY
# Optional: MODEL_NAME, TEMPERATURE, MAX_TOKENS, LOG_LEVEL
```

### 3. Run the Application

```bash
# Run main entry point
python main.py --input resources/data/sample_health_report.json

# Or start API server
uvicorn src.api.server:app --reload --port 8000
```

---

## 🏗️ ADK Architecture Overview

### ADK Workflow (Declarative Composition)

```
Orchestrator (async execute)
    ↓
HealthActionSquad (SequentialAgent)
    ├─> ReportAnalyst (LlmAgent)
    │     └─> output_key: health_analysis
    │
    └─> PlanningLoop (LoopAgent, max_iterations=3)
          ├─> LifestylePlanner (LlmAgent)
          │     └─> output_key: current_plan
          │           uses: {health_analysis}, {user_profile}, {validation_result}
          │
          └─> SafetyGuard (LlmAgent)
                └─> output_key: validation_result
                      tools: [exit_loop]
                      APPROVE → calls exit_loop → workflow END
                      REJECT → loop continues (if < max_iterations)
```

### ADK Agent Factory Pattern

All agents use **factory pattern** returning `LlmAgent` instances:

```python
from src.agents.analyst_agent import ReportAnalystAgent
from src.agents.planner_agent import LifestylePlannerAgent
from src.agents.guard_agent import SafetyGuardAgent

# Create ADK agents
analyst = ReportAnalystAgent.create_agent(model_name="gemini-pro")
planner = LifestylePlannerAgent.create_agent(model_name="gemini-pro")
guard = SafetyGuardAgent.create_agent(model_name="gemini-pro")
```

### Key ADK Features

- **Declarative Workflows**: `SequentialAgent` and `LoopAgent` for orchestration
- **Automatic State Injection**: Prompts use `{placeholders}` for state
- **Tool-based Control**: `exit_loop` tool terminates retry loop
- **Async Execution**: `await workflow.run()` for concurrent LLM calls
- **No Manual Loops**: ADK manages iterations and state flow

### Tech Stack

- **Framework**: Google ADK 1.19.0 (Agent Development Kit)
- **LLM**: Gemini Pro (via ADK ModelClient)
- **API**: FastAPI
- **State Management**: ADK automatic state injection
- **Safety**: Policy-based validation (YAML) with `exit_loop` termination

---

## 📁 Project Structure

```
health-action-squad/
├── src/
│   ├── domain/            # Business logic and domain models
│   │   └── state.py       # SessionState, WorkflowStatus
│   ├── workflow/          # Orchestration logic
│   │   └── orchestrator.py # Main workflow coordinator
│   ├── common/            # Shared configuration
│   │   └── config.py      # Config management
│   ├── ai/                # AI/LLM abstractions
│   │   ├── client.py      # ModelClient factory
│   │   ├── prompts.py     # Prompt loading utilities
│   │   └── tools.py       # ADK Tool wrappers
│   ├── agents/            # ADK Agents (Analyst, Planner, Guard)
│   ├── utils/             # Logger, helpers
│   └── api/               # FastAPI endpoints
├── resources/
│   ├── prompts/           # Agent system prompts
│   ├── data/              # Sample health reports
│   └── policies/          # safety_rules.yaml
├── tests/                 # Unit, integration, e2e tests
├── notebooks/             # Jupyter notebooks for experiments
├── docs/                  # Documentation
├── output/                # Generated outputs
└── main.py                # Entry point
```

---

## 🛡️ Development Guidelines

### Pre-Task Compliance (MANDATORY)
Before starting any task, verify:
- [ ] ✅ I acknowledge all ADK standards in CLAUDE.md
- [ ] Search first before creating new files (prevent duplicates)
- [ ] Use Task agents for operations >30 seconds
- [ ] Use TodoWrite for 3+ step tasks
- [ ] All agents inherit from `google.adk.agents.Agent`
- [ ] All context flows through SessionState (immutable)
- [ ] Prompts are in resources/prompts/ (not hardcoded)

### Code Quality Standards
```bash
# Format code (MUST run before commit)
black src/ tests/

# Lint check
pylint src/ tests/

# Type check
mypy src/ tests/

# Run tests
pytest tests/
```

### Git Workflow
```bash
# After completing a task
git add .
git commit -m "feat: description of changes"

# MANDATORY: Push to GitHub immediately
git push origin main
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/unit/              # Unit tests
pytest tests/integration/       # Integration tests
pytest tests/e2e/              # End-to-end tests

# With coverage
pytest --cov=src tests/
```

---

## 📊 SessionState Schema

All agent communication uses this immutable state object:

```python
@dataclass(frozen=True)
class SessionState:
    user_profile: dict              # User data
    health_metrics: dict            # Parsed health data
    risk_tags: List[str]            # Risk flags
    current_plan: str               # Generated plan (Markdown)
    feedback_history: List[Dict]    # Guard feedback per iteration
    retry_count: int                # Loop counter
    status: str                     # Enum: INIT|ANALYZING|PLANNING|REVIEWING|APPROVED|FAILED
```

---

## 🔒 Safety & Privacy

- **Safety Validation**: All plans validated against `resources/policies/safety_rules.yaml`
- **Circuit Breaker**: Max 3 Planner-Guard retry loops
- **Fallback**: Generic safe advice on validation failure
- **Privacy**: No raw health data in logs
- **Rate Limiting**: 10 requests/hour/IP on API endpoints

---

## 📚 Resources

- [CLAUDE.md](CLAUDE.md) - Project rules and standards (READ FIRST)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Safety Guidelines](https://google.github.io/adk-docs/safety/)
- [Kaggle Concierge Track](#)

---

## 🤝 Contributing

1. Read [CLAUDE.md](CLAUDE.md) thoroughly
2. Follow the pre-task compliance checklist
3. Ensure all tests pass
4. Run code quality checks (black, pylint, mypy)
5. Commit frequently with descriptive messages
6. Push to GitHub after every commit

---

## 📝 License

[Add your license here]

---

**Generated with Claude Code initialization workflow**
**Project initialized: 2025-11-20**
