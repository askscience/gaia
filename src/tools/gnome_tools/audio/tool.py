import subprocess
import shutil
import re
from src.tools.base import BaseTool
from src.core.prompt_manager import PromptManager

class GnomeAudioControlTool(BaseTool):
    @property
    def name(self):
        return "gnome_audio_control"

    @property
    def description(self):
        return "Controls system audio volume (get, set, mute, unmute)."

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_volume", "set_volume", "mute", "unmute"],
                    "description": "The action to perform."
                },
                "level": {
                    "type": "integer",
                    "description": "Volume level (0-100) for 'set_volume' action.",
                    "minimum": 0,
                    "maximum": 150
                }
            },
            "required": ["action"]
        }

    def execute(self, action: str, level: int = None, status_callback=None, **kwargs):
        pm = PromptManager()
        
        if status_callback:
            status_callback(pm.get("gnome_audio_control.status_working", action=action))

        try:
            if action == "get_volume":
                return self._get_volume(pm)
            elif action == "set_volume":
                if level is None:
                    return "Error: 'level' is required for set_volume."
                return self._set_volume(level, pm)
            elif action == "mute":
                return self._set_mute(True, pm)
            elif action == "unmute":
                return self._set_mute(False, pm)
            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return pm.get("gnome_audio_control.error_failed", error=str(e))

    def _get_volume(self, pm):
        # Try pactl first
        if shutil.which("pactl"):
            # pactl get-sink-volume @DEFAULT_SINK@
            # Output: Volume: front-left: 32768 /  50% / -18.06 dB,   front-right: 32768 /  50% / -18.06 dB
            try:
                res = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], capture_output=True, text=True, check=True)
                match = re.search(r"(\d+)%", res.stdout)
                if match:
                    return pm.get("gnome_audio_control.success_get", volume=match.group(1))
            except:
                pass
        
        # Fallback to amixer
        try:
            res = subprocess.run(["amixer", "get", "Master"], capture_output=True, text=True, check=True)
            match = re.search(r"\[(\d+)%\]", res.stdout)
            if match:
                return pm.get("gnome_audio_control.success_get", volume=match.group(1))
        except:
            pass
            
        return "Could not determine volume."

    def _set_volume(self, level, pm):
        # pactl support
        if shutil.which("pactl"):
            cmd = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"]
            subprocess.run(cmd, check=True)
            return pm.get("gnome_audio_control.success_set", level=level)
        
        # amixer support
        cmd = ["amixer", "sset", "Master", f"{level}%"]
        subprocess.run(cmd, check=True)
        return pm.get("gnome_audio_control.success_set", level=level)

    def _set_mute(self, mute: bool, pm):
        state = "mute" if mute else "unmute"
        if shutil.which("pactl"):
            # pactl set-sink-mute @DEFAULT_SINK@ 1
            val = "1" if mute else "0"
            cmd = ["pactl", "set-sink-mute", "@DEFAULT_SINK@", val]
            subprocess.run(cmd, check=True)
            return pm.get("gnome_audio_control.success_mute", state=state)
            
        cmd = ["amixer", "sset", "Master", state]
        subprocess.run(cmd, check=True)
        return pm.get("gnome_audio_control.success_mute", state=state)
