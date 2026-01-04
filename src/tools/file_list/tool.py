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

    def execute(self, project_id: str, status_callback=None, **kwargs):
        if status_callback:
            status_callback("Listing project files...")

        artifacts_dir = os.path.join(get_artifacts_dir(), project_id)
        
        if not os.path.exists(artifacts_dir):
            return f"No files found. Project directory does not exist yet."
        
        try:
            files = []
            for root, dirs, filenames in os.walk(artifacts_dir):
                for filename in filenames:
                    # Calculate relative path from artifacts_dir
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, artifacts_dir)
                    
                    size = os.path.getsize(full_path)
                    files.append(f"  - {rel_path} ({size} bytes)")
            
            if not files:
                return "No files in project directory."
            
            # Sort for consistent output
            files.sort()
            return f"Files in project:\n" + "\n".join(files)
            
        except Exception as e:
            return f"Error listing files: {str(e)}"
