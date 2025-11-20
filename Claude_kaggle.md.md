<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 請提供

以下是修正過、符合 ADK 現代多代理實作規範的 CLAUDE.md，可直接儲存使用：

***

# CLAUDE.md - Health Action Squad (Concierge Agent)

**Documentation Version:** 3.0 (ADK Production Edition)
**Project:** Health Action Squad (Kaggle Concierge Track)
**Tech Stack:** Python, Google ADK (Agent Development Kit), Gemini Pro, Event-Driven Architecture
**Description:** Multi-agent system interprets health reports and generates personalized safe plans using a strict planner-guard loop. All code must follow ADK patterns and safety protocols.

***

## 🚨 CRITICAL RULES

### ⚠️ RULE ADHERENCE SYSTEM ACTIVE

Claude Code 必須明確應答：
`✅ ADK STANDARDS ACKNOWLEDGED`

***

## ❌ 絕對禁止

- 絕不混用 ADK 與 LangGraph 概念，專案僅用 ADK event-driven workflow。
- 禁止任何原生 LLM API 呼叫（如直接 requests.post），必須用 ADK ModelClient。
- System Instruction 不得硬寫於 .py，僅允許 resources/prompts/ 下的文本。
- 都必須使用 SessionState 管理 context，不得 stateless 傳遞參數。
- Agent 執行流程必須走 Orchestrator → Planner → Guard → Loop 機制。
- Debug 請使用 src/utils/logger.py，絕不允許 print()。

***

## 📝 ADK 多代理規範

- 所有 Agent 必須繼承 `google.adk.agents.Agent`，單一職責原則。
- Workflow 與代理溝通不得直接 message passing，僅使用 `SessionState`。
- 所有外部工具必須用 ADK Tool 介面包裝。
- Planner → Guard → Planner 的 retry 循環必須有 Circuit Breaker（Max 3）。
- Agent Logic 如需修改，請調整 prompt，不可重複造新代理。
- SafetyGuardAgent 必須引用 `resources/policies/safety_rules.yaml`，不可常數寫死。

***

## 🏗️ 架構與目錄

```
health-action-squad/
├── src/
│   ├── core/
│   │   ├── orchestrator.py
│   │   ├── state.py        # SessionState dataclass，務必 immutable（frozen=True）
│   │   └── config.py
│   ├── agents/
│   │   ├── analyst_agent.py
│   │   ├── planner_agent.py
│   │   └── guard_agent.py
│   ├── tools/
│   │   └── search_tool.py  # ADK 搜尋包裝
│   ├── utils/
│   │   └── logger.py   # 結構化日誌，必須 trace A2A (Agent-to-Agent)
│   └── api/
│       └── server.py   # FastAPI 負責 RESTful 呼叫
├── resources/
│   ├── prompts/
│   ├── data/           # health report mock
│   └── policies/       # safety_rules.yaml
├── tests/
├── main.py
├── requirements.txt
└── README.md
```


***

## SessionState 標準

```python
@dataclass(frozen=True)
class SessionState:
    user_profile: dict        # 固定使用者資料
    health_metrics: dict      # 報告解析結果
    risk_tags: List[str]      # 風險標誌
    current_plan: str         # Markdown計劃
    feedback_history: List[Dict] # 每一回合Feedback
    retry_count: int          # Planner-Guard循環次數
    status: str               # 工作流狀態，僅允許列舉值
```


***

## 代理責任說明

**ReportAnalystAgent**

- 僅做健康報告解析為 metrics/risk tags，不得外部查詢。
- 輸出需符合 SessionState schema。

**LifestylePlannerAgent**

- 必須結合 health_metrics/risk_tags/user_profile 產生 Markdown 計劃。
- 必須用 ADK Tool（如 GoogleSearchTool）查找知識；計劃需引入 Guard feedback 循環。
- 計劃長度限 1500 字內，醫療推薦必須有資料來源。

**SafetyGuardAgent**

- 只負責驗證 current_plan 及 risk_tags，使用 safety_rules.yaml。
- 必須給出明確 decision/feedback/violations。
- 驗證不過時進行 Planner retry，max 3 次；超過走 Fallback。

***

## Orchestrator 工作流（精要）

```python
while state.retry_count < MAX_RETRIES:
    plan = planner.execute(state)
    state = update_state(state, current_plan=plan)
    result = guard.execute(state)
    if result.decision == "APPROVE":
        return state.final_output
    state = update_state(state, feedback_history=..., retry_count=state.retry_count+1)
# 超過循環限制
fallback = generate_fallback(state.risk_tags)
```


***

## 觀測和安全最佳實踐

- **日誌**：AgentLogger 必須 trace 所有主要狀態轉移，格式須結構化、含 session/agent/iteration 標記。
- **安全**：API 輸入必須 Pydantic 驗證，不容錯誤格式；不得log健康原始資料。
- **Rate Limit**：FastAPI route 必須加 slowapi 限制 (如 10/hr/IP)。
- **Fallback**：若三次循環均不過，輸出統一安全建議（見 Orchestrator）。

***

## 指令與測試流程

- 安裝 ADK：`pip install google-adk`
- 執行入口：`python main.py --input ...`
- 單元測試：`pytest tests/unit/`
- 集成測試：`pytest tests/integration/`
- E2E 流程測試：`pytest tests/e2e/`
- Black/Lint/Type Check 必須過。

***

## 審查檢查點

- 修改行為請優先確認 Agent 是否已存在。
- 所有新欄位只可加於 SessionState，不可散傳。
- 新的代理/工具需對應 unit test 。
- Proxy prompt 只允許放於 resources/prompts/。
- 交付前需通過全部測試與 Black 格式化、無 lint/type 錯誤。

***

## 參考與資源

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Safety Guidelines](https://google.github.io/adk-docs/safety/)
- [ADK 多代理設計 Patterns](https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/)
- [Kaggle Concierge Forum](#)

***

**End of CLAUDE.md. 本檔案為本專案唯一規範副本，所有設計決策請以此為準。**

