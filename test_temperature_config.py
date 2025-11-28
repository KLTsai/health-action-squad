"""驗證 agents 使用 Config.TEMPERATURE 和 Config.MAX_TOKENS"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.agents.analyst_agent import ReportAnalystAgent
from src.agents.planner_agent import LifestylePlannerAgent
from src.agents.guard_agent import SafetyGuardAgent
from src.common.config import Config

def test_analyst_agent_config():
    agent = ReportAnalystAgent.create_agent()
    assert agent.generate_content_config is not None, "generate_content_config should be set"
    assert agent.generate_content_config.temperature == Config.TEMPERATURE, \
        f"Temperature should be {Config.TEMPERATURE}, got {agent.generate_content_config.temperature}"
    assert agent.generate_content_config.max_output_tokens == Config.MAX_TOKENS, \
        f"Max tokens should be {Config.MAX_TOKENS}, got {agent.generate_content_config.max_output_tokens}"
    print(f"[OK] ReportAnalyst: temp={agent.generate_content_config.temperature}, tokens={agent.generate_content_config.max_output_tokens}")

def test_planner_agent_config():
    agent = LifestylePlannerAgent.create_agent()
    assert agent.generate_content_config is not None, "generate_content_config should be set"
    assert agent.generate_content_config.temperature == Config.TEMPERATURE, \
        f"Temperature should be {Config.TEMPERATURE}, got {agent.generate_content_config.temperature}"
    assert agent.generate_content_config.max_output_tokens == Config.MAX_TOKENS, \
        f"Max tokens should be {Config.MAX_TOKENS}, got {agent.generate_content_config.max_output_tokens}"
    print(f"[OK] LifestylePlanner: temp={agent.generate_content_config.temperature}, tokens={agent.generate_content_config.max_output_tokens}")

def test_guard_agent_config():
    agent = SafetyGuardAgent.create_agent()
    assert agent.generate_content_config is not None, "generate_content_config should be set"
    assert agent.generate_content_config.temperature == Config.TEMPERATURE, \
        f"Temperature should be {Config.TEMPERATURE}, got {agent.generate_content_config.temperature}"
    assert agent.generate_content_config.max_output_tokens == Config.MAX_TOKENS, \
        f"Max tokens should be {Config.MAX_TOKENS}, got {agent.generate_content_config.max_output_tokens}"
    print(f"[OK] SafetyGuard: temp={agent.generate_content_config.temperature}, tokens={agent.generate_content_config.max_output_tokens}")

if __name__ == "__main__":
    print(f"Testing with Config.TEMPERATURE={Config.TEMPERATURE} (expected: 0.6), Config.MAX_TOKENS={Config.MAX_TOKENS}\n")
    try:
        test_analyst_agent_config()
        test_planner_agent_config()
        test_guard_agent_config()
        print("\n[SUCCESS] All agent configuration tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
