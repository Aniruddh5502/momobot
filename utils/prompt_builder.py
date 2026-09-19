import json, subprocess, platform, sys
from TOOLS.taskState import Task
from typing import Dict
from TOOLS.taskState import load
from bootstrap import system_prompt

result = subprocess.run("echo %COMSPEC%", shell=True, capture_output=True, text=True)
systemInfo = {
    "OS":{platform.system()},
    "OS Version":{platform.version()},
    "Node":{platform.node},
    "Architecture":{platform.machine()},
    "Pyhton Version":{sys.version},
    "Pyhton Executable":{sys.executable},
    "shell info":{result.stdout}
}

def get_system_info():
    systemInfo = {
        "OS":{platform.system()},
        "OS Version":{platform.version()},
        "Node":{platform.node},
        "Architecture":{platform.machine()},
        "Pyhton Version":{sys.version},
        "Pyhton Executable":{sys.executable},
        "shell info":{result.stdout}
    }
    return systemInfo

def build_system_prompt(systemPrompt:str, summary:str, taskState:Dict[str, Task])->str:
    system_prompt = f"{systemPrompt} \n\n# Summary:\n{summary}\n\n# System Information: \n{systemInfo}\n\n# Task State: \n{str(json.dumps(taskState, indent=2))}\n"
    return system_prompt

if __name__=="__main__":
    summary = "this is the summary section"
    systemPrompt = build_system_prompt(system_prompt, summary, load())
    print(systemPrompt)