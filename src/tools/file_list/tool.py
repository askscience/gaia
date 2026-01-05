import os
from src.tools.base import BaseTool
from src.core.config import get_artifacts_dir
from src.core.prompt_manager import PromptManager

class FileListTool(BaseTool):
    @property
    def name(self) -> str:
        return "file_list"

    @property
    def description(self) -> str:
        return "List all files in the current project's artifact directory. Use this to see what files exist before creating or editing."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project (chat) to list files from."
                }
            },
            "required": ["project_id"]
        }

    def execute(self, project_id: str, status_callback=None, **kwargs):
        prompt_manager = PromptManager()
        if status_callback:
            status_callback(prompt_manager.get("file_list.status_listing"))

        artifacts_dir = os.path.join(get_artifacts_dir(), project_id)
        
        if not os.path.exists(artifacts_dir):
            return prompt_manager.get("file_list.error_not_found")
        
        try:
            files = []
            for root, dirs, filenames in os.walk(artifacts_dir):
                for filename in filenames:
                    # Calculate relative path from artifacts_dir
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, artifacts_dir)
                    
                    size = os.path.getsize(full_path)
                    files.append(prompt_manager.get("file_list.item_format", rel_path=rel_path, size=size))
            
            if not files:
                return prompt_manager.get("file_list.empty_directory")
            
            # Sort for consistent output
            files.sort()
            return prompt_manager.get("file_list.success_header") + "\n".join(files)
            
        except Exception as e:
            return prompt_manager.get("file_list.error_generic", error=str(e))
