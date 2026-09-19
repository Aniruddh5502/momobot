import sys
import time
import threading
from ui.animation import ThinkingAnimation

def test_sync():
    print("Starting synchronization stress test...")
    anim = ThinkingAnimation()
    anim.start()
    
    # Simulate rapid updates from the agent
    updates = [f"Update message {i}: Testing synchronization stability..." for i in range(50)]
    
    def on_agent_update(text):
        with anim.lock:
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()
            print(text)
    
    try:
        for up in updates:
            on_agent_update(up)
            time.sleep(0.01) # Rapid fire
        
        print("\nSuccessfully printed all updates without visible interference.")
    finally:
        anim.stop()
        print("Animation stopped.")

if __name__ == "__main__":
    test_sync()
