# CLAUDE.md - Health Action Squad (Concierge Agent)

**Documentation Version:** 3.2 (ADK Production - Fully Implemented)
**Last Updated:** 2025-11-22
**Project:** Health Action Squad (Kaggle Concierge Track)
**Tech Stack:** Python, Google ADK (Agent Development Kit), Gemini 2.5 Flash, Event-Driven Architecture
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
- **NEVER** bypass ADK's automatic state injection via output_keys - state flows through placeholders
- **NEVER** bypass Orchestrator → Planner → Guard → Loop mechanism
- **NEVER** use print() for debugging - MUST use src/utils/logger.py
- **NEVER** create new files in root directory → use proper module structure
- **NEVER** create duplicate files (agent_v2.py, enhanced_xyz.py) → ALWAYS extend existing files
- **NEVER** create multiple implementations of same concept → single source of truth
- **NEVER** use git commands with -i flag (interactive mode not supported)
- **NEVER** add promotional messages to git commits (no "Generated with Claude Code" or "Co-Authored-By: Claude")

### 📝 MANDATORY REQUIREMENTS
- **ADK AGENTS** - All agents MUST use factory pattern returning `google.adk.agents.LlmAgent` instances
- **STATE FLOW** - All workflow communication flows through ADK output_keys, prompts use `{placeholders}` for injection
- **TOOL WRAPPING** - All external tools MUST use ADK Tool interface (FunctionTool wrapper)
- **CIRCUIT BREAKER** - Planner → Guard → Planner retry loop MUST have max 3 attempts
- **SAFETY POLICY** - SafetyGuardAgent MUST reference `resources/policies/safety_rules.yaml`
- **MEDICAL GUIDELINES** - ReportAnalystAgent MUST reference `resources/policies/medical_guidelines.yaml` for evidence-based thresholds
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
- [ ] Does agent use factory pattern returning LlmAgent instances?
- [ ] Is state flowing through ADK output_keys (not manual passing)?
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
│   ├── parsers/               # PDF parsing & OCR module
│   │   ├── pdf_processor.py   # PDF → image conversion (pdf2image)
│   │   ├── ocr_engine.py      # OCR wrapper (PaddleOCR)
│   │   ├── data_extractor.py  # Regex template matching
│   │   ├── llm_parser.py      # LLM-based structured extraction
│   │   └── templates/         # Hospital-specific templates
│   │       ├── ntuh_template.py
│   │       ├── tvgh_template.py
│   │       └── generic_template.py
│   ├── utils/
│   │   └── logger.py          # Structured logging with A2A trace
│   └── api/
│       └── server.py          # FastAPI REST endpoints
├── resources/
│   ├── prompts/               # Agent system prompts
│   │   ├── analyst_prompt.txt
│   │   ├── planner_prompt.txt
│   │   ├── guard_prompt.txt
│   │   └── llm_parser_prompt.txt
│   ├── data/                  # Health report mocks
│   └── policies/              # Safety rules YAML
│       └── safety_rules.yaml
├── tests/
│   ├── unit/                  # Unit tests
│   │   └── parsers/           # Parser unit tests
│   ├── integration/           # Integration tests
│   │   └── test_pdf_upload_flow.py
│   └── e2e/                   # End-to-end tests
├── notebooks/                 # Jupyter notebooks
│   ├── exploratory/           # Data exploration
│   └── experiments/           # ML experiments
├── docs/                      # Documentation
│   └── pdf_parser_guide.md    # PDF parser implementation guide
├── output/                    # Generated outputs
│   └── parsed_pdfs/           # Audit trail of parsed PDFs
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
    model="gemini-2.5-flash",
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
analyst = ReportAnalystAgent.create_agent(model_name="gemini-2.5-flash")
```

**Specifications:**
- **Purpose**: Parse health reports into structured metrics and risk tags
- **Output Key**: `health_analysis` (used by downstream agents)
- **Prompt Source**: `resources/prompts/analyst_prompt.txt` (loaded via `load_prompt()`)
- **Model**: Gemini 2.5 Flash (configurable)
- **Constraints**:
  - NO external queries
  - MUST return JSON with `health_metrics` and `risk_tags`
  - All prompts externalized, no hardcoding

### LifestylePlannerAgent (src/agents/planner_agent.py)

**Factory Method:**
```python
from src.agents.planner_agent import LifestylePlannerAgent

# Create ADK LlmAgent with state injection
planner = LifestylePlannerAgent.create_agent(model_name="gemini-2.5-flash")
```

**Specifications:**
- **Purpose**: Generate personalized Markdown lifestyle plan
- **Output Key**: `current_plan` (consumed by SafetyGuard)
- **Prompt Source**: `resources/prompts/planner_prompt.txt`
- **State Injection**: Uses placeholders `{health_analysis}`, `{user_profile}`, `{validation_result}`
- **Model**: Gemini 2.5 Flash (configurable)
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
guard = SafetyGuardAgent.create_agent(model_name="gemini-2.5-flash")
```

**Specifications:**
- **Purpose**: Validate plans against safety policies and terminate loop on approval
- **Output Key**: `validation_result` (fed back to Planner)
- **Prompt Source**: `resources/prompts/guard_prompt.txt`
- **Safety Rules**: Loads `resources/policies/safety_rules.yaml` into prompt
- **Tools**: `[FunctionTool(exit_loop)]` - ADK's built-in loop termination
- **Model**: Gemini 2.5 Flash (configurable)
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
orchestrator = Orchestrator(model_name="gemini-2.5-flash")

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

## 🩺 Medical Guideline Management

### Evidence-Based Approach

**Problem**: AI health systems often use LLM knowledge without traceable medical sources, creating trust issues with domain experts.

**Solution**: Transparent, evidence-based thresholds documented in `resources/policies/medical_guidelines.yaml`.

### Architecture Decision: YAML vs RAG vs API

**Current approach (MVP/POC)**: Static YAML with quarterly review

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Static YAML** | Transparent, zero cost, stable, audit-friendly | Manual updates required | ✅ Current (POC) |
| **RAG** | Auto-updates, handles rare conditions | Complex, costly, retrieval errors | ⏳ Future |
| **Public APIs** | Real-time updates | No free clinical threshold APIs exist | ❌ Not viable |

**Rationale**:
- Standard health metrics (cholesterol, BP, glucose, BMI) have stable guidelines (updated annually, not daily)
- Transparency > automation for medical credibility
- Zero runtime cost suitable for MVP phase
- Easy for medical professionals to audit and validate

### Medical Guidelines File Structure

```yaml
# resources/policies/medical_guidelines.yaml
version: "1.0.0"
last_reviewed: "2025-11-22"
next_review_due: "2026-02-22"  # Enforced by CI/CD tests

lipid_panel:
  total_cholesterol:
    reference_ranges:
      optimal: "<200"
      borderline_high: "200-239"
      high: "≥240"
    source:
      guideline: "NCEP ATP III Guidelines"
      year: 2002
      url: "https://www.ncbi.nlm.nih.gov/books/NBK542294/"
```

**Key Features**:
- Every threshold cites published guidelines (NCEP, AHA, ACC, ADA, WHO)
- Asian-specific adjustments (e.g., BMI ≥23 for overweight in Taiwan)
- Version tracking and review dates
- Legal disclaimer and maintenance protocol

### Automated Validation

**Test Suite**: `tests/validation/test_guideline_integrity.py`

**Critical Tests**:
1. **Expiry Check**: Fails if guidelines >90 days old (enforces quarterly review)
2. **Known Thresholds**: Validates evidence-based thresholds (e.g., cholesterol ≥200, HbA1c ≥6.5%)
3. **Source Citations**: Ensures all sections cite medical guideline sources
4. **Asian Adjustments**: Verifies Taiwan-specific standards present

**CI/CD Integration**:
```bash
# Automated tests run on every commit
pytest tests/validation/test_guideline_integrity.py
# Fails if guidelines expired → forces review before merging
```

### Quarterly Review Protocol

**Checklist** (documented in medical_guidelines.yaml):
1. Check ADA Standards (released annually in January)
2. Check ACC/AHA cardiovascular guideline updates
3. Review Taiwan MOH recommendations: https://www.mohw.gov.tw/
4. Update version number and changelog
5. Re-run validation test suite

**Workflow**:
```bash
# Review → Update YAML → Run tests → Commit
vim resources/policies/medical_guidelines.yaml
pytest tests/validation/
git commit -m "docs: Update medical guidelines to v1.1.0 (2026-Q1 review)"
git push origin main
```

### Integration with Agents

**ReportAnalystAgent** (`resources/prompts/analyst_prompt.txt`):
```
## Medical Guideline Reference

All risk thresholds are based on evidence-based clinical guidelines:
- Source: resources/policies/medical_guidelines.yaml
- Version: 1.0.0 (Last Reviewed: 2025-11-22)
- Guidelines: NCEP ATP III, ACC/AHA 2017/2019, ADA 2025, WHO 2004

Example:
- `high_cholesterol`: Total cholesterol ≥200 mg/dL (NCEP ATP III)
- `high_blood_pressure`: Systolic ≥130 OR Diastolic ≥80 mmHg (ACC/AHA 2017)
```

**Benefits**:
- Analysts can verify every threshold against published guidelines
- Medical professionals can audit and challenge specific thresholds
- Clear upgrade path to RAG when justified by user needs

### Future Scaling Considerations

**When to upgrade to RAG**:
- Handling rare conditions not in standard health screenings
- Real-time integration of latest medical research
- Revenue justifies infrastructure cost (~$200-500/month)
- User feedback indicates need for more dynamic updates

**When to stay with YAML**:
- Standard health metrics (current scope)
- MVP/POC phase with limited budget
- Quarterly guideline updates are sufficient
- Transparency requirements outweigh automation benefits

---

## 📄 PDF Parser Architecture

### Overview

**Purpose**: Enable direct PDF health report uploads with automatic data extraction, reducing manual data entry and improving user experience.

**Data Extraction Priority** (highest to lowest):

1. **Template Matching** - Known hospital format regex patterns
2. **OCR + LLM** - PaddleOCR text extraction + Gemini structured parsing
3. **Manual Input** - User provides data directly (fallback)

### Module Structure

```
src/
├── parsers/                    # PDF parsing module
│   ├── __init__.py
│   ├── pdf_processor.py        # Main PDF → image conversion
│   ├── ocr_engine.py           # PaddleOCR wrapper + extraction
│   ├── data_extractor.py       # Regex pattern matching & validation
│   ├── llm_parser.py           # LLM-based structured extraction (fallback)
│   └── templates/              # Hospital-specific templates
│       ├── __init__.py
│       ├── ntuh_template.py    # National Taiwan University Hospital
│       ├── tvgh_template.py    # Taipei Veterans General Hospital
│       └── generic_template.py # Generic health report format
```

### PDF Processing Flow

```
User Upload (PDF)
  ↓
PDFProcessor.convert_to_images()
  ↓ (pdf2image + poppler)
Image Sequence
  ↓
DataExtractor.match_templates()
  ├─ Tries NTUH template (confidence ≥ 0.85) → SUCCESS
  ├─ Tries TVGH template (confidence ≥ 0.85)
  └─ Tries Generic template (confidence ≥ 0.85)
  ↓ (if no match)
OCREngine.extract_text()
  ↓ (paddleocr)
Raw Text
  ↓
LLMParser.parse_structured()
  ↓ (Gemini + structured prompt)
Extracted Data (confidence score)
  ↓ (confidence ≥ 0.85?)
Return to Analyst Agent
```

### Template System

#### Hospital Template Structure (example: NTUH)

```python
# src/parsers/templates/ntuh_template.py
class NTUHTemplate:
    """National Taiwan University Hospital report format."""

    # Header pattern to detect format
    HEADER_PATTERN = r"National Taiwan University Hospital|NTUH"
    CONFIDENCE_THRESHOLD = 0.85

    # Field extraction patterns
    PATTERNS = {
        "total_cholesterol": r"Total Cholesterol[:\s]+(\d+)",
        "hdl": r"HDL[:\s]+(\d+)",
        "ldl": r"LDL[:\s]+(\d+)",
        "triglycerides": r"Triglycerides[:\s]+(\d+)",
        "blood_pressure": r"BP[:\s]+(\d+)/(\d+)",
        "fasting_glucose": r"Fasting Glucose[:\s]+(\d+)",
        "hba1c": r"HbA1c[:\s]+([\d.]+)",
    }

    @classmethod
    def match(cls, text: str) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Match template to text and extract data.

        Returns:
            (is_match, confidence_score, extracted_data)
        """
        pass
```

### Adding New Hospital Templates

#### Step 1: Create template file

```python
# src/parsers/templates/my_hospital_template.py
from typing import Tuple, Dict, Any
import re

class MyHospitalTemplate:
    """My Hospital report format."""

    HEADER_PATTERN = r"My Hospital|MH"
    CONFIDENCE_THRESHOLD = 0.85

    PATTERNS = {
        "total_cholesterol": r"Cholesterol[:\s]+(\d+)",
        "blood_pressure": r"BP[:\s]+(\d+)/(\d+)",
        # Add more patterns...
    }

    @classmethod
    def match(cls, text: str) -> Tuple[bool, float, Dict[str, Any]]:
        # Check if header pattern matches
        if not re.search(cls.HEADER_PATTERN, text):
            return False, 0.0, {}

        # Extract fields using patterns
        extracted = {}
        matches_found = 0

        for field, pattern in cls.PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted[field] = match.group(1)
                matches_found += 1

        # Calculate confidence
        confidence = matches_found / len(cls.PATTERNS)
        is_match = confidence >= cls.CONFIDENCE_THRESHOLD

        return is_match, confidence, extracted
```

#### Step 2: Register template in DataExtractor

```python
# src/parsers/data_extractor.py
from parsers.templates import (
    NTUHTemplate,
    TVGHTemplate,
    MyHospitalTemplate,  # Add import
    GenericTemplate
)

class DataExtractor:
    TEMPLATES = [
        NTUHTemplate,
        TVGHTemplate,
        MyHospitalTemplate,  # Register
        GenericTemplate
    ]

    @classmethod
    def match_templates(cls, text: str) -> Tuple[str, float, Dict]:
        """Try templates in order until match found."""
        for template in cls.TEMPLATES:
            is_match, confidence, data = template.match(text)
            if is_match:
                return template.__name__, confidence, data

        # No template matched - return generic match
        return "unknown", 0.0, {}
```

#### Step 3: Test the template

```bash
pytest tests/unit/parsers/test_my_hospital_template.py -v
```

### OCR Fallback Strategy

**When used**: Template matching confidence < 0.85 OR no template matches

**Process**:

1. PDFProcessor converts PDF to images
2. OCREngine runs PaddleOCR on all pages
3. Text combined into single document
4. LLMParser uses Gemini to extract structured health data

**LLMParser Prompt** (resources/prompts/llm_parser_prompt.txt):

```
Extract structured health metrics from this OCR text.

Requirements:
1. Return JSON with fields: total_cholesterol, hdl, ldl, blood_pressure, fasting_glucose, hba1c
2. If value not found, return null
3. Include confidence score (0-1) for entire extraction
4. List any uncertain fields in "uncertain_fields" array

OCR Text:
{ocr_text}

Return JSON only:
{
  "total_cholesterol": number or null,
  "hdl": number or null,
  ...
  "confidence": 0.75,
  "uncertain_fields": ["field_name"]
}
```

**Confidence Thresholds**:

- ≥ 0.85: Auto-use extracted data
- 0.70-0.84: LLM requests manual verification before proceeding
- < 0.70: Reject extraction, ask user to manually enter data

### Integration with ReportAnalystAgent

**Modified analyst_prompt.txt**:

```
## Data Source
{data_source}

## Extraction Method
{parsing_method}  # "template_match" | "ocr_fallback" | "manual_input"

## Extraction Confidence
{extraction_confidence}  # 0-1 score

## Raw Health Data
{health_report}
```

**Modified HealthReportRequest Pydantic model**:

```python
class HealthReportRequest(BaseModel):
    # Direct input
    health_report: Optional[Dict] = None

    # PDF upload (new)
    pdf_file: Optional[UploadFile] = None

    user_profile: Optional[Dict] = None

    # System will auto-parse PDF and populate health_report
```

### Performance Considerations

- **PDF Size Limit**: 20MB max (prevents memory issues)
- **Timeout**: 30 seconds for OCR + LLM fallback
- **Caching**: Store parsed PDFs in `output/parsed_pdfs/` for audit trail
- **Model Caching**: PaddleOCR models cached locally (~500MB disk)

### Testing Strategy

```python
# tests/unit/parsers/test_template_system.py
def test_ntuh_template_extraction():
    """Test NTUH template pattern matching."""
    text = """
    National Taiwan University Hospital
    Total Cholesterol: 240 mg/dL
    HDL: 35 mg/dL
    """
    is_match, confidence, data = NTUHTemplate.match(text)
    assert is_match
    assert confidence >= 0.85
    assert data["total_cholesterol"] == "240"

# tests/unit/parsers/test_ocr_fallback.py
def test_ocr_fallback_confidence():
    """Test OCR fallback confidence calculation."""
    ocr_text = "Cholesterol 250 Blood Pressure 140/90"
    result = OCREngine.extract_health_metrics(ocr_text)
    assert 0.5 <= result.confidence <= 1.0

# tests/integration/test_pdf_upload_flow.py
def test_pdf_upload_end_to_end(sample_pdf_path):
    """Test full PDF → extraction → plan generation."""
    response = client.post(
        "/api/v1/upload_report",
        files={"file": open(sample_pdf_path, "rb")}
    )
    assert response.status_code == 200
    assert "extracted_data" in response.json()
    assert "parsing_method" in response.json()
```

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
