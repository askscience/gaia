import asyncio
import json
import os
from src.tools.base import BaseTool
from src.tools.deep_research.graph import DeepResearchGraph

class DeepResearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "deep_research"

    @property
    def description(self) -> str:
        return (
            "Perform an autonomous, multi-step deep research on a topic. "
            "This tool plans, searches multiple queries, scrapes page content, "
            "reflects on findings, and synthesizes a final report with citations. "
            "Use this for complex questions requiring thorough investigation."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The complex research query or topic"
                }
            },
            "required": ["query"]
        }

    def execute(self, query: str, status_callback=None, **kwargs):
        """
        Execute the Deep Research Agent in the background.
        """
        try:
            from src.tools.deep_research.manager import BackgroundResearchManager
            
            project_id = kwargs.get("project_id", "unknown")
            manager = BackgroundResearchManager()
            
            # Start research in background and return immediate feedback
            # Note: We use project_id as chat_id for now as it identifies the current workspace/chat
            result_msg = manager.start_research(query, project_id, project_id)
            
            # Formulate the response for the AI
            # We want the agent to tell the user that it's working in background
            response = f"[AI_CONTEXT]\n{result_msg}\n[/AI_CONTEXT]\n\n"
            response += f"IMPORTANT: Deep research has started in the background. "
            response += "Respond to the user with a VERY CONCISE confirmation (1 small sentence). "
            response += "Explain that you will notify them via system notification when ready. "
            response += "Then, ask if there is anything else they need while the research runs."
            
            return response

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error starting background deep research: {str(e)}"
