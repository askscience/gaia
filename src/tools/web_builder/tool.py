from src.tools.base import BaseTool
import os
import json
from src.core.config import get_artifacts_dir
from src.core.prompt_manager import PromptManager
from src.tools.web_builder.manager import BackgroundWebBuilderManager

class WebBuilderTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_builder"

    @property
    def description(self) -> str:
        return "MANDATORY: Use this tool to create web projects. Provide a 'description' to generate a plan. Once the user approves the plan via the UI, call with action='execute' to build."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform: 'plan' (default if description provided) or 'execute' (to run a pending plan).",
                    "enum": ["plan", "execute"]
                },
                "files": {
                    "type": "array",
                    "description": "Optional: A list of files to create directly (legacy sync mode).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": { "type": "string" },
                            "content": { "type": "string" },
                            "language": { "type": "string" }
                        },
                        "required": ["filename", "content"]
                    }
                },
                "description": {
                    "type": "string",
                    "description": "Optional: A high-level description of the web project to build. Generates a plan for user approval."
                },
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project (chat)."
                }
            },
            "required": ["project_id"]
        }

    def execute(self, files: list = None, description: str = None, project_id: str = None, action: str = None, status_callback=None, **kwargs):
        prompt_manager = PromptManager()
        
        if project_id is None:
            return "Error: Missing required argument 'project_id'."

        # MODE 1: EXECUTE PENDING
        if action == "execute":
            manager = BackgroundWebBuilderManager()
            return manager.execute_pending_plan(project_id)

        # MODE 2: PLAN (Asynchronous Description provided)
        if description:
            manager = BackgroundWebBuilderManager()
            result = manager.create_plan(description, project_id)
            
            if isinstance(result, dict) and "error" in result:
                return f"Error creating plan: {result['error']}"
                
            # Result is a list of file plans
            plan_artifact = {
                "type": "implementation_plan",
                "files": result,
                "project_id": project_id,
                "description": description
            }
            
            count = len(result)
            msg = prompt_manager.get("web_builder.plan_pending", count=count)
            # FORCE STOP INSTRUCTION
            return f"{msg}\n[ARTIFACT]{json.dumps(plan_artifact)}[/ARTIFACT]\n\nSYSTEM: The plan is now visible to the user. STOP. Do not proceed until you receive a 'Plan approved' message."

        # MODE 3: LEGACY SYNC (Files provided)
        if files is None:
            return "Error: Must provide either 'files' or 'description' (for planning)."

        # Defensive check: if files is a string
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
            
            # Ensure subdirectory exists
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            except OSError as e:
                results.append(prompt_manager.get("web_builder.error_file", filename=filename, error=f"Failed to create directory: {e}"))
                continue
            
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
