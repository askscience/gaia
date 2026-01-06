import os
import json
from src.tools.base import BaseTool
from src.core.config import get_artifacts_dir
from src.core.prompt_manager import PromptManager

class FileEditorTool(BaseTool):
    @property
    def name(self) -> str:
        return "file_editor"

    @property
    def description(self) -> str:
        return "Edit an existing file by finding and replacing text. Use this to make targeted changes to files without rewriting the entire content."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The name of the file to edit (e.g., 'style.css')."
                },
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project (chat) where the file is located."
                },
                "search": {
                    "type": "string",
                    "description": "The exact text to find in the file. Must match exactly."
                },
                "replace": {
                    "type": "string",
                    "description": "The text to replace the found text with."
                }
            },
            "required": ["filename", "project_id", "search", "replace"]
        }

    def execute(self, filename: str, project_id: str, search: str, replace: str, status_callback=None, **kwargs):
        prompt_manager = PromptManager()
        
        if status_callback:
            status_callback(prompt_manager.get("file_editor.status_editing", filename=os.path.basename(filename)))

        artifacts_dir = os.path.join(get_artifacts_dir(), project_id)
        file_path = os.path.join(artifacts_dir, filename)
        
        if not os.path.exists(file_path):
            return prompt_manager.get("file_editor.error_not_found", filename=filename, project_id=project_id)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check if search text exists
            if search not in content:
                # Try flexible matching
                new_content, count = self._flexible_replace(content, search, replace)
                if count > 0:
                     with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                     return prompt_manager.get("file_editor.success_flexible", filename=filename, count=count, search_preview=search[:50], replace_preview=replace[:50])
                
                return prompt_manager.get("file_editor.error_search_not_found", filename=filename)
            
            # Count occurrences
            count = content.count(search)
            
            # Perform replacement
            new_content = content.replace(search, replace)
            
            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            # Return artifact metadata for UI refresh
            _, ext = os.path.splitext(filename)
            language = ext.lower().replace(".", "")
            if language == "js": language = "javascript"
            
            artifact_data = {
                "filename": filename,
                "path": file_path,
                "language": language,
                "type": "code" if language != "html" else "web"
            }
            
            return prompt_manager.get("file_editor.success", filename=filename, count=count, artifact_json=json.dumps(artifact_data))
        except Exception as e:
            return prompt_manager.get("file_editor.error_generic", filename=filename, error=str(e))

    def _flexible_replace(self, content: str, search: str, replace: str):
        """Attempt to replace text ignoring whitespace differences per line."""
        search_lines = [line.strip() for line in search.splitlines() if line.strip()]
        if not search_lines:
            return content, 0
            
        content_lines = content.splitlines()
        result_lines = []
        i = 0
        count = 0
        
        while i < len(content_lines):
            # Optimization: Check if current line matches first search line (fuzzy)
            if i + len(search_lines) <= len(content_lines):
                match = True
                for j in range(len(search_lines)):
                    if content_lines[i+j].strip() != search_lines[j]:
                        match = False
                        break
                
                if match:
                    # Found a block match!
                    # We skip the matched lines in content and append the replacement
                    result_lines.append(replace)
                    i += len(search_lines)
                    count += 1
                    continue
            
            result_lines.append(content_lines[i])
            i += 1
            
        return "\n".join(result_lines), count
