import sys
import time
import threading
import itertools
import random
from typing import Optional

# ======================================================================
#                             SPINNER                                   
# ======================================================================
"""
SPINNERS = {
    "sparkle": ["✽", "✻", "∴", "✽", "✻", "∴", "·", "*"],  # Your original characters
    "mystical": ["✽", "✺", "✻", "✹", "✸", "✧", "✦", "✶"],  # Gradual brightness change
    "pulse": ["✽", "✽", "✻", "✻", "∴", "∴", "·", "·", "*", "*"],  # Pulse effect
    "wave": ["✽", "✻", "✹", "✸", "✧", "✦", "✶", "·", "·", "✶", "✦", "✧", "✸", "✹", "✻"],  # Back and forth
    "twinkle": ["✽", "·", "✻", "·", "✹", "·", "✸", "·", "✦", "·"],  # Twinkling effect
    "rotation": ["✽", "✹", "✺", "✻", "✸", "✧", "✶", "✽"],  # Rotating through star-like shapes
    "comet": ["·", "*", "✽", "✻", "✹", "✸", "✧", "✶", " ", " ", " "],  # Comet tail effect
    "double_ring": ["✽✻", "✻✽", "✽·", "✻·", "·✽", "·✻"],  # Two characters side by side
    "spiral": ["✽", "✻", "∴", "·", " ", "·", "∴", "✻", "✽"],  # Expanding and contracting
}
"""
# Frames for different animations
SPINNERS = {
    "sparkle": ["✽", "✻", "∴", "✽", "✻", "∴", "·", "*"]
}

THINKING_VERBS = [
    "Thinking.."
]

class ThinkingAnimation:
    """
    A non-blocking terminal animation that runs in a separate thread.
    Displays a rotating spinner and a random 'thinking verb'.
    """
    # \033[38;5;202m            ->  Coral-ish
    # \033[38;2;255;255;255m    ->  True White
    # \033[97m                  ->  Bright White
    def __init__(self, color_code: str = "\033[38;5;202m"): 
        self.color_code = color_code
        self.reset_code = "\033[0m"
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Choose a random spinner type
        spinner_type = random.choice(list(SPINNERS.keys()))
        self.frames = itertools.cycle(SPINNERS[spinner_type])
        self.verb = random.choice(THINKING_VERBS)

    def _animate(self):
        while not self._stop_event.is_set():
            frame = next(self.frames)
            # \r returns cursor to start of line
            sys.stdout.write(f"\r{self.color_code}{frame} {self.reset_code} {self.verb}")
            sys.stdout.flush()
            time.sleep(0.2)

    def start(self):
        self._stopped = False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self):
        if getattr(self, '_stopped', False):  # ← guard
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        # Clear the line
        sys.stdout.write("\r" + " " * 50 + "\r")
        sys.stdout.flush()

def start_thinking():
    """Convenience function to start the animation."""
    anim = ThinkingAnimation()
    anim.start()
    return anim

def stop_thinking(anim: ThinkingAnimation):
    """Convenience function to stop the animation."""
    anim.stop()
