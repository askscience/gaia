import os
from src.tools.base import BaseTool
from src.core.config import get_artifacts_dir

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

    def execute(self, project_id: str):
        artifacts_dir = os.path.join(get_artifacts_dir(), project_id)
        
        if not os.path.exists(artifacts_dir):
            return f"No files found. Project directory does not exist yet."
        
        try:
            files = []
            for item in os.listdir(artifacts_dir):
                item_path = os.path.join(artifacts_dir, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    files.append(f"  - {item} ({size} bytes)")
            
            if not files:
                return "No files in project directory."
            
            return f"Files in project:\n" + "\n".join(files)
            
        except Exception as e:
            return f"Error listing files: {str(e)}"
