import sys
from core.engine import MomobotAgent
from core.state import AgentState
from ui.animation import ThinkingAnimation
from rich.console import Console

# Mock callback to capture updates
updates = []
def mock_on_update(text):
    updates.append(text)

def test_tool_ui_updates():
    print("Testing tool UI updates...")
    config = {"model": "gemma4:31b-cloud"}
    agent = MomobotAgent(config)
    
    # Create a state that forces a tool call
    # Since we can't easily simulate a real LLM call here without an API,
    # we will manually trigger a tool from the tools list to see if it uses the callback.
    
    from tools.basic_tools import read
    
    # Set the global callback in the agent
    MomobotAgent.current_callback = mock_on_update
    
    print("Executing read tool with mock callback...")
    # Create a dummy file to read
    with open("test_ui_sync.txt", "w") as f:
        f.write("Hello UI Sync")
    
    try:
        read(filePath="test_ui_sync.txt", on_update=MomobotAgent.current_callback)
        
        if any("Reading test_ui_sync.txt" in u for u in updates):
            print("✓ Tool update captured successfully!")
        else:
            print("✗ Tool update not captured.")
            print(f"Captured updates: {updates}")
            sys.exit(1)
    finally:
        import os
        if os.path.exists("test_ui_sync.txt"):
            os.remove("test_ui_sync.txt")

if __name__ == "__main__":
    test_tool_ui_updates()
