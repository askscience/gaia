from src.tools.base import BaseTool
import os
import json
from src.core.config import get_artifacts_dir

class WebBuilderTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_builder"

    @property
    def description(self) -> str:
        return "MANDATORY: Use this tool to create ANY file (HTML, CSS, JS). Do NOT print code in chat, always save it using this tool."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The name of the file (e.g., 'index.html', 'style.css')."
                },
                "content": {
                    "type": "string",
                    "description": "The full content of the file."
                },
                "language": {
                    "type": "string",
                    "description": "Optional: The programming language (e.g., 'html', 'css', 'javascript')."
                },
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project (chat) where the file should be saved."
                }
            },
            "required": ["filename", "content", "project_id"]
        }

    def execute(self, filename: str, content: str, project_id: str, language: str = None):
        if not language:
            _, ext = os.path.splitext(filename)
            ext = ext.lower().replace(".", "")
            if ext == "html": language = "html"
            elif ext == "css": language = "css"
            elif ext in ["js", "javascript"]: language = "javascript"
            else: language = "text"

        # Organize artifacts by project_id
        project_dir = os.path.join(get_artifacts_dir(), project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        file_path = os.path.join(project_dir, filename)
        
        try:
            with open(file_path, "w") as f:
                f.write(content)
            
            # Return a structured response that the UI can parse
            artifact_data = {
                "filename": filename,
                "path": file_path,
                "language": language,
                "type": "code" if language != "html" else "web"
            }
            
            return f"Successfully created {filename} in project {project_id}. [ARTIFACT]{json.dumps(artifact_data)}[/ARTIFACT]"
        except Exception as e:
            return f"Error creating file {filename}: {str(e)}"
