from datetime import datetime
from src.tools.base import BaseTool

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
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
