"""Demonstration of async/await issue in main.py"""
import asyncio


async def async_function():
    """Simulates orchestrator.execute()"""
    await asyncio.sleep(0.1)  # Simulate API call
    return {"session_id": "123", "status": "success"}


def wrong_way():
    """❌ Wrong: Calling async function without await (like old main.py)"""
    print("\n=== WRONG WAY (Before Fix) ===")
    result = async_function()  # Missing await!

    print(f"Type of result: {type(result)}")
    print(f"Value of result: {result}")

    try:
        session_id = result['session_id']  # This will fail!
        print(f"Session ID: {session_id}")
    except TypeError as e:
        print(f"[ERROR] {e}")
        print("   ^ This is why main.py was broken!")


def correct_way():
    """[OK] Correct: Using asyncio.run() (like fixed main.py)"""
    print("\n=== CORRECT WAY (After Fix) ===")
    result = asyncio.run(async_function())  # Proper async execution
    print(f"Type of result: {type(result)}")
    print(f"Value of result: {result}")

    try:
        session_id = result['session_id']  # This works!
        print(f"[OK] Session ID: {session_id}")
        print(f"[OK] Status: {result['status']}")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Demonstrating async/await issue in Health Action Squad")
    print("=" * 60)

    wrong_way()
    correct_way()

    print("\n" + "=" * 60)
    print("Conclusion:")
    print("  - Without asyncio.run(), async functions don't execute")
    print("  - They return coroutine objects instead of results")
    print("  - This is why main.py needed the async fix")
    print("=" * 60)
