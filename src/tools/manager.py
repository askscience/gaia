import os
import importlib.util
import inspect
from src.tools.base import BaseTool

class ToolManager:
    def __init__(self):
        self.tools = {}
        self.tools_dir = os.path.dirname(os.path.abspath(__file__))

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
        return [tool.to_ollama_format() for tool in self.tools.values()]

    def execute_tool(self, tool_name, status_callback=None, **kwargs):
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            sig = inspect.signature(tool.execute)
            
            # Only pass status_callback if the tool's execute method handles it
            if status_callback and "status_callback" in sig.parameters:
                kwargs["status_callback"] = status_callback
                
            return tool.execute(**kwargs)
        return f"Tool {tool_name} not found."
