# ======================================================================||
# Directories  Setup                                                    ||
# ======================================================================||
from pathlib import Path
import shutil
from datetime import datetime
from rich.console import Console
import json

console = Console()
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
config_file = Path.home() / ".momobot" / "config.json"
config = json.loads(config_file.read_text())

# Base directory for all persistent agent data
MOMO_HOME = Path.home() / ".momobot"

SCRIPT_DIR              =       Path(__file__).parent
STATE_DIR               =       SCRIPT_DIR / "STATE"
CONVERSATION_DIR        =       SCRIPT_DIR / "CONVERSATION"
WORKSPACE_DIR           =       Path.cwd()
PROMPT_DIR              =       SCRIPT_DIR / "PROMPT"
OUTPUTS_DIR             =       WORKSPACE_DIR / "OUTPUT"
CWD                     =       Path.cwd

paths_to_check  =   [
    STATE_DIR,
    CONVERSATION_DIR,
    WORKSPACE_DIR,
    OUTPUTS_DIR,
]

# Skills folder copying - Skills remain in the script dir for packaging, 
# but are copied to the workspace for agent use.
SRC = SCRIPT_DIR / "WORKSPACE" / "skills"
DST = WORKSPACE_DIR / "skills"
if not DST.exists():
    shutil.copytree(SRC, DST, dirs_exist_ok=False)


# Colors Tetradic
terracota = "#E3725E"
green_oli = "#8DE35E"
cyan_blue = "#5ECFE3"
pink_purp = "#B45EE3"

# ======================================================================
# FIRST: Create all necessary directories
# ======================================================================

for path in paths_to_check:
    path.mkdir(parents=True, exist_ok=True)


# ======================================================================
# SECOND: Define file paths
# ======================================================================
soul_file       = PROMPT_DIR / "SOUL.md"
skills_file     = PROMPT_DIR / "SKILL.md"
sub_sys_file    = PROMPT_DIR / "SUB_SOUL.md"
compactionPrompt= PROMPT_DIR / "compaction.md"

# ======================================================================
# THIRD: Create files if they don't exist (Editable mode: Read from repo)
# ======================================================================

def ensure_prompt_exists(path):
    if not path.exists():
        console.print(f"[bold red]X [/bold red] [dim]Critical Prompt Missing: {path.name} not found in {path.parent}[/dim]")
        return False
    return True

ensure_prompt_exists(soul_file)
ensure_prompt_exists(skills_file)
ensure_prompt_exists(sub_sys_file)

# ======================================================================
# FOURTH: Verify all files exist, then read them safely
# ======================================================================
required_files = {
    'soul_file': soul_file,
    'skills_file': skills_file
}

missing = [name for name, path in required_files.items() if not path.exists()]
if missing:
    raise FileNotFoundError(
        f"Critical setup error: {missing} were not created.\\n"
        f"Check directory permissions and try running setup again."
    )

# Safe to read now
soul = soul_file.read_text(encoding='utf-8')
skill = skills_file.read_text(encoding='utf-8')

system_prompt = soul + "\\n\\n" + "\\n\\n" + skill

# For subagent its system prompt
if sub_sys_file.exists():
    sub_agent_soul = sub_sys_file.read_text(encoding='utf-8')
else:
    sub_agent_soul = soul

sub_agent_sys_prompt = sub_agent_soul
