"""Test script to understand ADK SequentialAgent.run_async() API"""

import asyncio
from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.client import ModelClient

async def test_run_async():
    """Test how to consume SequentialAgent.run_async() async generator"""

    # Create simple test workflow
    client = ModelClient(model="gemini-2.5-flash")

    test_agent = LlmAgent(
        name="TestAgent",
        model=client,
        instruction="You are a test agent. Return 'Hello' when you receive input.",
    )

    workflow = SequentialAgent(
        name="TestWorkflow",
        agents=[test_agent]
    )

    # Test different consumption patterns
    print("Testing run_async() consumption patterns...\n")

    # Pattern 1: Iterate over async generator
    print("Pattern 1: async for loop")
    try:
        initial_state = {"test_input": "hello"}
        events = []
        async for event in workflow.run_async(initial_state):
            events.append(event)
            print(f"  Event: {type(event).__name__}")
            if hasattr(event, 'is_final_response') and event.is_final_response():
                print(f"  Final event found!")
                print(f"  Event attributes: {[k for k in dir(event) if not k.startswith('_')]}")
                break

        print(f"  Total events: {len(events)}")
        if events:
            final_event = events[-1]
            print(f"  Final event type: {type(final_event).__name__}")
            print(f"  Has dict(): {hasattr(final_event, 'dict')}")
            if hasattr(final_event, 'dict'):
                print(f"  Event dict: {final_event.dict()}")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_run_async())
