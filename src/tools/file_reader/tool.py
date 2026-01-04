import os
from src.tools.base import BaseTool
from src.core.config import get_artifacts_dir

class FileReaderTool(BaseTool):
    @property
    def name(self) -> str:
        return "file_reader"

    @property
    def description(self) -> str:
        return "Read the contents of a file from the current project's artifact directory. Use this to inspect existing code before making modifications."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The name of the file to read (e.g., 'index.html', 'style.css')."
                },
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project (chat) where the file is located."
                }
            },
            "required": ["filename", "project_id"]
        }

    def execute(self, filename: str, project_id: str, status_callback=None, **kwargs):
        if status_callback:
            status_callback(f"Reading {os.path.basename(filename)}...")

        artifacts_dir = os.path.join(get_artifacts_dir(), project_id)
        file_path = os.path.join(artifacts_dir, filename)
        
        if not os.path.exists(file_path):
            return f"Error: File '{filename}' not found in project '{project_id}'."
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"--- CONTENT OF {filename} ---\n{content}\n--- END OF {filename} ---"
        except Exception as e:
            return f"Error reading file {filename}: {str(e)}"
