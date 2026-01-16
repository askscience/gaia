from src.tools.base import BaseTool
from src.core.prompt_manager import PromptManager
from src.tools.gnome_tools.document.finder import find_files
from src.tools.gnome_tools.document.reader import DocumentReader

class GnomeDocumentTool(BaseTool):
    """
    Tool to find, read, and query local documents (PDF, DOCX, TXT).
    """
    
    @property
    def name(self):
        return "gnome_document"

    @property
    def description(self):
        return "Find files, read their content (PDF, DOCX, TXT), and answer questions about them."

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["find", "read"],
                    "description": "The action to perform: 'find' a file or 'read' a file's content."
                },
                "filename": {
                    "type": "string",
                    "description": "The name of the file to find or read."
                },
                "query": {
                    "type": "string",
                    "description": "Optional question to ask about the file (used for context, though 'read' returns raw text)."
                }
            },
            "required": ["action", "filename"]
        }

    def execute(self, action: str, filename: str, query: str = None, status_callback=None, **kwargs):
        prompt_manager = PromptManager()
        reader = DocumentReader()
        
        if action == "find":
            if status_callback:
                status_callback(prompt_manager.get("gnome_document.status_finding", filename=filename))
                
            results = find_files(filename)
            if not results:
                return prompt_manager.get("gnome_document.error_not_found", filename=filename)
            
            # If only one result, we can clarify
            msg = prompt_manager.get("gnome_document.found_files", count=len(results), files=", ".join(results))
            return msg

        elif action == "read":
            # If path is not absolute, try to find it first
            target_path = filename
            if not filename.startswith("/"):
                results = find_files(filename, max_results=1)
                if not results:
                     return prompt_manager.get("gnome_document.error_not_found", filename=filename)
                target_path = results[0]
            
            if status_callback:
                status_callback(prompt_manager.get("gnome_document.status_reading", filename=target_path))
                
            try:
                content = reader.read(target_path)
                return prompt_manager.get("gnome_document.read_success", filename=target_path, content=content)
            except Exception as e:
                return prompt_manager.get("gnome_document.error_read", filename=target_path, error=str(e))
        
        return "Invalid action."
