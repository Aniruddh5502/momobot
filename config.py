"""
This file will save the configuration settings storing and editing 
"""

# we will define a config variable that will be saved as a json file and its settings
# can be changed by commands and saved into the config.json and when any configuration
# data is needed the code will read it form the location.

# let's test json data saving and loading
import json, os
from pathlib import Path

# now we define a settings criteria and specify the fields.
config = {
    "provider"          :       "ollama",
    "model"             :       "gemma4:31b-cloud",
    "base_url"          :       "http://localhost:11434",
    "recent_window"     :       6,
    # prompts
    "system_prompt"     :       "prompts/soul.md",
    "compaction_prompt" :       "prompts/compaction.md",
    "user_details"      :       "prompts/user.md",
}

root = Path(__file__).parent
config_dir = root / "config"
config_file = config_dir / "config.json"

os.makedirs(config_dir, exist_ok=True)

with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)
    
# reading it from source for testing
read_content = {}
with open(config_file, 'r') as f:
    read_content = json.load(f)
    
config = read_content