from src.tools.base import BaseTool
import os
import json
from src.core.config import get_artifacts_dir

class WebConsoleTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_console"

    @property
    def description(self) -> str:
        return "Reads the browser console logs/errors for a specific project. Use this after building a website to check for runtime errors (JavaScript crashes, etc)."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project to inspect."
                }
            },
            "required": ["project_id"]
        }

    def execute(self, project_id: str, status_callback=None, **kwargs):
        if status_callback:
            status_callback("Reading console logs...")

        project_dir = os.path.join(get_artifacts_dir(), project_id)
        log_file = os.path.join(project_dir, "console.json")
        
        if not os.path.exists(log_file):
            return "No console logs found. Has the preview been run?"
            
        logs = []
        try:
            with open(log_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        logs.append(json.loads(line))
                    except:
                        pass
        except Exception as e:
            return f"Error reading logs: {e}"

        if not logs:
            return "Console is empty (no errors or logs)."
            
        # Format logs for AI
        output = []
        for entry in logs:
            type_ = entry.get("type", "log").upper()
            msg = entry.get("message", "")
            source = entry.get("source", "")
            lineno = entry.get("lineno", 0)
            stack = entry.get("stack", "")
            
            line_info = f" ({source}:{lineno})" if lineno else ""
            output.append(f"[{type_}]{line_info} {msg}")
            if stack:
                # Indent stack trace
                output.append(f"  Stack: {stack}")
                
        return "\n".join(output)
