import os
import importlib.util
import inspect
from src.tools.base import BaseTool
from src.core.config import ConfigManager

class ToolManager:
    def __init__(self):
        self.tools = {}
        self.tools_dir = os.path.dirname(os.path.abspath(__file__))
        self.config = ConfigManager()

    def load_tools(self):
        self.tools = {}
        # Scan subdirectories for tools
        # Structure: src/tools/<tool_name>/tool.py
        for item in os.listdir(self.tools_dir):
            item_path = os.path.join(self.tools_dir, item)
            if os.path.isdir(item_path):
                tool_file = os.path.join(item_path, "tool.py")
                if os.path.exists(tool_file):
                    self._load_tool_from_file(tool_file)

    def _load_tool_from_file(self, path):
        try:
            spec = importlib.util.spec_from_file_location("dynamic_tool", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:
                    tool_instance = obj()
                    self.tools[tool_instance.name] = tool_instance
                    print(f"Loaded tool: {tool_instance.name}")
        except Exception as e:
            print(f"Error loading tool from {path}: {e}")

    def get_ollama_tools_definitions(self):
        enabled_map = self.config.get("enabled_tools", {})
        active_tools = []
        for name, tool in self.tools.items():
            # Default to True if not in map
            if enabled_map.get(name, True):
                active_tools.append(tool.to_ollama_format())
        return active_tools

    def execute_tool(self, tool_name, status_callback=None, **kwargs):
        # check if enabled
        enabled_map = self.config.get("enabled_tools", {})
        if not enabled_map.get(tool_name, True):
            return f"Tool '{tool_name}' is disabled in settings."

        if tool_name in self.tools:
            tool = self.tools[tool_name]
            sig = inspect.signature(tool.execute)
            
            # Prepare status callback wrapper
            from src.core.status.manager import StatusManager
            
            project_id = kwargs.get("project_id", "unknown")
            
            def report_status(message):
                # 1. Emit via centralized manager
                StatusManager().emit_status(project_id, message)
                # 2. Call legacy callback if provided
                if status_callback:
                    status_callback(message)

            # Pass our wrapper if the tool accepts 'status_callback'
            if "status_callback" in sig.parameters:
                kwargs["status_callback"] = report_status
                
            return tool.execute(**kwargs)
        return f"Tool {tool_name} not found."
