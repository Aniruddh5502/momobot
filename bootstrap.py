import os
from pathlib import Path
import json


# Setting workspace with respect to the location where momobot is invoked
root            =   Path(__file__).parent
WORKSPACE_DIR   =   Path.cwd() 

STATE_DIR = root / "states"
STATE_DIR.mkdir(parents=True, exist_ok=True)     

soul_file       =   root / "prompts" / "soul.md"

sessions_dir    =   root / "sessions"
sessions_dir.mkdir(parents=True, exist_ok=True)
sessions_db     =   sessions_dir / "sessions.db"

# Load config from the config module or a default dictionary
try:
    import config
    _config_data = config.config
except Exception:
    _config_data = {}

config = _config_data

if __name__ == "__main__":
    print(f"Workspace Directory initialized to: {WORKSPACE_DIR}")
    print(f"Config loaded: {bool(config)}")
