import sys
import time
import threading
import random
from typing import Optional

class ThinkingAnimation:
    """A simple spinner animation that runs in a separate thread with synchronization lock"""
    
    def __init__(self, message:str="Thinking", color_code:str = "\033[38;2;227;114;94m", speed:float=5):
        self.message = message
        self.color_code = color_code
        self.reset_code = "\033[0m"
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.lock = threading.Lock() # Lock for synchronized stdout access
        
        self.speed = 1/speed
        self.frames =  ["·", "✢", "✶", "✻", "✽", "✻", "✶", "✢"]
        self.actions = [
            "Doodling",
            "Thinking",
            "Unfolding",
            "Finding",
            "Reconstructing",
            "Doomscrolling",
            "Killing braincell"
        ]
        self.action = random.choice(self.actions)
        
    def _animate(self):
        idx = 0
        while not self._stop_event.is_set():
            frame = self.frames[idx % len(self.frames)]
            with self.lock:
                sys.stdout.write(f"\r{self.color_code}{frame} {self.action} {self.reset_code}")
                sys.stdout.flush()
            time.sleep(self.speed)
            idx += 1
            
    def start(self):
        """Start the spinner animation"""
        self.action = random.choice(self.actions)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the spinner animation and clear the line"""
        self._stop_event.set()
        if self._thread:
            self._thread.join() # Wait indefinitely for the thread to finish its last loop
        
        with self.lock:
            # Clear the line completely
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()
