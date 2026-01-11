import os
import shutil
import subprocess
from src.tools.base import BaseTool
from src.core.prompt_manager import PromptManager

class GnomeOpenerTool(BaseTool):
    @property
    def name(self):
        return "gnome_opener"

    @property
    def description(self):
        return "Opens files, folders, URLs, or launches system applications (e.g., 'firefox', 'gnome-terminal')."

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "The file path, URL, or application name to open/launch."
                }
            },
            "required": ["target"]
        }

    def execute(self, target: str, status_callback=None, **kwargs):
        pm = PromptManager()
        
        # Handle backward compatibility if 'uri' was passed in kwargs by old prompt
        if not target and 'uri' in kwargs:
            target = kwargs['uri']

        if status_callback:
            status_callback(pm.get("gnome_opener.status_opening", uri=target))
            
        try:
            # 1. Try gio open if it looks like a file/URL or exists on disk
            is_file_or_url = os.path.exists(target) or "://" in target or target.startswith("mailto:") or target.startswith("/")
            
            # 2. Check if it is a command
            cmd_path = shutil.which(target)
            
            if is_file_or_url:
                cmd = ["gio", "open", target]
                subprocess.run(cmd, check=True)
                return pm.get("gnome_opener.success", uri=target)
            
            elif cmd_path:
                # Launch application detached
                subprocess.Popen([cmd_path], 
                               cwd=os.path.expanduser("~"),
                               start_new_session=True)
                return f"Successfully launched application: {target}"
            
            else:
                # Fallback: Try gio open anyway (might handle magic names?)
                try:
                    cmd = ["gio", "open", target]
                    subprocess.run(cmd, check=True)
                    return pm.get("gnome_opener.success", uri=target)
                except:
                     return f"Could not open or launch '{target}'. It does not appear to be a file, URL, or installed application."

        except Exception as e:
            return pm.get("gnome_opener.error_failed", error=str(e))
