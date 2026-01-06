from src.tools.base import BaseTool
import os
import json
from src.core.config import get_artifacts_dir
from src.core.prompt_manager import PromptManager

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
        prompt_manager = PromptManager()

        # Defensive check: if files is a string (due to parsing issues), try to load it as JSON
        if isinstance(files, str):
            try:
                files = json.loads(files)
            except:
                return prompt_manager.get("web_builder.error_parse_files", snippet=files[:100])

        if not isinstance(files, list):
            return prompt_manager.get("web_builder.error_invalid_type", type=type(files).__name__)
        
        # Log to status
        if status_callback:
            names = [f.get('filename') for f in files if isinstance(f, dict) and f.get('filename')]
            if names:
                desc = ", ".join(names[:2])
                if len(names) > 2: desc += "..."
                status_callback(prompt_manager.get("web_builder.status_multiple", names=desc))
            else:
                status_callback(prompt_manager.get("web_builder.status_generic"))

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
                
                results.append(prompt_manager.get("web_builder.success_file", filename=filename))
                artifact_tags.append(f"[ARTIFACT]{json.dumps(artifact_data)}[/ARTIFACT]")
            except Exception as e:
                results.append(prompt_manager.get("web_builder.error_file", filename=filename, error=str(e)))
        
        return "\n".join(results) + "\n" + "".join(artifact_tags)
