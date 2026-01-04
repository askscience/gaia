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
        return "MANDATORY: Use this tool to create ANY file (HTML, CSS, JS). Do NOT print code in chat. After building, use the 'web_console' tool to debug runtime errors."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "description": "A list of files to create.",
                    "items": {
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
                            }
                        },
                        "required": ["filename", "content"]
                    }
                },
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project (chat) where the files should be saved."
                }
            },
            "required": ["files", "project_id"]
        }

    def execute(self, files: list, project_id: str, status_callback=None, **kwargs):
        # Log to status
        if status_callback:
            names = [f.get('filename') for f in files if isinstance(f, dict) and f.get('filename')]
            if names:
                desc = ", ".join(names[:2])
                if len(names) > 2: desc += "..."
                status_callback(f"Building {desc}...")
            else:
                status_callback("Building web project...")

        # Defensive check: if files is a string (due to parsing issues), try to load it as JSON
        if isinstance(files, str):
            try:
                files = json.loads(files)
            except:
                return f"Error: 'files' parameter must be a list, but received a string that could not be parsed as JSON: {files[:100]}..."

        if not isinstance(files, list):
            return f"Error: 'files' parameter must be a list, but received {type(files).__name__}."

        # Organize artifacts by project_id
        project_dir = os.path.join(get_artifacts_dir(), project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        results = []
        artifact_tags = []
        
        for file_info in files:
            filename = file_info.get('filename')
            content = file_info.get('content')
            language = file_info.get('language')
            
            if not language:
                _, ext = os.path.splitext(filename)
                ext = ext.lower().replace(".", "")
                if ext == "html": language = "html"
                elif ext == "css": language = "css"
                elif ext in ["js", "javascript"]: language = "javascript"
                else: language = "text"

            file_path = os.path.join(project_dir, filename)
            
            try:
                with open(file_path, "w") as f:
                    f.write(content)
                
                artifact_data = {
                    "filename": filename,
                    "path": file_path,
                    "language": language,
                    "type": "code" if language != "html" else "web"
                }
                
                results.append(f"Successfully created {filename}")
                artifact_tags.append(f"[ARTIFACT]{json.dumps(artifact_data)}[/ARTIFACT]")
            except Exception as e:
                results.append(f"Error creating file {filename}: {str(e)}")
        
        return "\n".join(results) + "\n" + "".join(artifact_tags)
