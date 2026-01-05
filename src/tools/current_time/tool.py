from datetime import datetime
from src.tools.base import BaseTool
from src.core.prompt_manager import PromptManager

class CurrentTimeTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "Get the current system time."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def execute(self, **kwargs):
        prompt_manager = PromptManager()
        return datetime.now().strftime(prompt_manager.get("current_time.format"))
