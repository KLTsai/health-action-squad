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
analyst = ReportAnalystAgent.create_agent(model_name="gemini-2.5-flash")
planner = LifestylePlannerAgent.create_agent(model_name="gemini-2.5-flash")
guard = SafetyGuardAgent.create_agent(model_name="gemini-2.5-flash")
```

### Key ADK Features

- **Declarative Workflows**: `SequentialAgent` and `LoopAgent` for orchestration
- **Automatic State Injection**: Prompts use `{placeholders}` for state
- **Tool-based Control**: `exit_loop` tool terminates retry loop
- **Async Execution**: `await workflow.run()` for concurrent LLM calls
- **No Manual Loops**: ADK manages iterations and state flow

### Tech Stack

- **Framework**: Google ADK (>=0.1.0, agent-based architecture)
- **LLM**: Gemini 2.5 Flash (via ADK ModelClient)
- **API**: FastAPI
- **State Management**: ADK automatic state injection via output_keys
- **Safety**: Policy-based validation (YAML) with `exit_loop` termination

---

## 📁 Project Structure

```
health-action-squad/
├── src/
│   ├── domain/            # Business logic and domain models
│   │   └── state.py       # SessionState (DEPRECATED - testing only)
│   ├── workflow/          # Orchestration logic
│   │   └── orchestrator.py # Main workflow coordinator
│   ├── common/            # Shared configuration
│   │   └── config.py      # Config management
│   ├── ai/                # AI/LLM abstractions
│   │   ├── client.py      # ModelClient factory
│   │   ├── prompts.py     # Prompt loading utilities
│   │   └── tools.py       # Tool wrappers (DEPRECATED - placeholder)
│   ├── agents/            # ADK Agents (Analyst, Planner, Guard)
│   ├── utils/             # Logger, helpers
│   └── api/               # FastAPI endpoints
├── resources/
│   ├── prompts/           # Agent system prompts
│   ├── data/              # Sample health reports
│   └── policies/          # safety_rules.yaml
├── tests/                 # Unit, integration, e2e, manual tests
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── e2e/              # End-to-end tests
│   └── manual/           # Manual testing scripts
├── notebooks/             # Jupyter notebooks for experiments
├── docs/                  # Documentation
├── output/                # Generated outputs
└── main.py                # Entry point
```

---

## 📡 API Reference

### Endpoints

#### POST /api/v1/generate_plan

Generate personalized health plan from health report

- Request: `HealthReportRequest` (health_report, optional user_profile)
- Response: `PlanGenerationResponse` with plan, risk_tags, iterations

#### GET /health and GET /api/v1/health

Health check endpoint

- Returns: service status, version, model, uptime

#### GET /

API information and documentation links

- Returns: API name, version, documentation URLs

### Response Fields (POST /api/v1/generate_plan)

```json
{
  "session_id": "uuid",              // Unique session identifier
  "status": "approved",               // "approved" | "rejected" | "fallback"
  "plan": "# Markdown Plan...",      // Generated lifestyle plan
  "risk_tags": ["high_cholesterol"], // Identified health risks
  "iterations": 2,                    // Planner-Guard loop count (1-3)
  "timestamp": "2025-11-22T...",     // ISO-8601 timestamp
  "health_analysis": {...},          // Parsed health metrics
  "validation_result": {...},        // Safety validation details
  "message": null                    // Optional info message
}
```

#### Status Values

- `approved`: Guard validated plan successfully
- `rejected`: Failed validation after max retries
- `fallback`: Workflow error, generic advice provided

---

## 🛡️ Development Guidelines

### Pre-Task Compliance (MANDATORY)
Before starting any task, verify:
- [ ] ✅ I acknowledge all ADK standards in CLAUDE.md
- [ ] Search first before creating new files (prevent duplicates)
- [ ] Use Task agents for operations >30 seconds
- [ ] Use TodoWrite for 3+ step tasks
- [ ] All agents use factory pattern returning `LlmAgent` instances
- [ ] All context flows through ADK output_keys (automatic state injection)
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

## 🧪 Testing and Coverage

### Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest --cov=src tests/

# Generate HTML coverage report
pytest --cov=src --cov-report=html tests/
# View at: htmlcov/index.html

# Run specific test suites
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
```

### Current Test Coverage

- **Total Coverage**: 79%
- **Unit Tests**: 38 tests
- **Integration Tests**: 9 tests
- **All tests passing** ✅

### Test Structure

- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - API and workflow integration tests
- `tests/manual/` - Manual testing and debugging scripts

---

## 📊 ADK State Management

State flows automatically through ADK's output_key mechanism:

- **ReportAnalyst** → output_key: `health_analysis`
- **LifestylePlanner** → output_key: `current_plan` (uses {health_analysis}, {user_profile})
- **SafetyGuard** → output_key: `validation_result` (uses {current_plan})

ADK automatically injects state into prompts via `{placeholder}` syntax. No manual state management required.

**Note**: SessionState class exists for backward compatibility and testing only (DEPRECATED).

---

## 📊 Logging and Observability

The project uses structured logging for comprehensive observability:

### AgentLogger Features

- Session-level tracing with unique `session_id`
- Agent lifecycle tracking (creation, execution, completion)
- Loop iteration counting in Planner-Guard cycles
- Guard decision logging (APPROVE/REJECT) with feedback
- Error tracking with full context and stack traces

### Log Configuration

- Default level: INFO (configurable via `LOG_LEVEL` env var)
- Format: JSON structured logs (configurable via `LOG_FORMAT`)
- Output: Console and file (`logs/` directory)

### Example Log Entry

```json
{
  "timestamp": "2025-11-22T10:30:00Z",
  "level": "INFO",
  "logger": "Orchestrator",
  "session_id": "abc-123",
  "agent": "SafetyGuard",
  "iteration": 2,
  "decision": "APPROVE",
  "message": "Plan approved after validation"
}
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
