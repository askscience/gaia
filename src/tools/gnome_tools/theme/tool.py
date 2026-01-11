import subprocess
from src.tools.base import BaseTool
from src.core.prompt_manager import PromptManager

class GnomeThemeTool(BaseTool):
    @property
    def name(self):
        return "gnome_theme"

    @property
    def description(self):
        return "Switches the system theme to light or dark."

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "theme": {
                    "type": "string",
                    "enum": ["light", "dark"],
                    "description": "The theme to switch to ('light' or 'dark')."
                }
            },
            "required": ["theme"]
        }

    def execute(self, theme: str, status_callback=None, **kwargs):
        pm = PromptManager()
        theme = theme.lower()
        
        if theme not in ["light", "dark"]:
            return pm.get("gnome_theme.error_invalid", theme=theme)
            
        if status_callback:
            status_callback(pm.get("gnome_theme.status_changing", theme=theme))
            
        try:
            val = 'prefer-dark' if theme == 'dark' else 'default'
            if theme == 'light': val = 'prefer-light'
            
            cmd = ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", val]
            subprocess.run(cmd, check=True)
            return pm.get("gnome_theme.success", theme=theme)
        except Exception as e:
            return pm.get("gnome_theme.error_failed", error=str(e))
