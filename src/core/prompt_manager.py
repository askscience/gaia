import json
import os
from datetime import datetime

class PromptManager:
    _instance = None

    def __new__(cls, prompts_path=None):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, prompts_path=None):
        if self._initialized: return
        
        if prompts_path is None:
            # Default to src/core/prompts/en.json relative to this file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            prompts_path = os.path.join(base_dir, "prompts", "en.json")
        
        self.prompts = self._load_prompts(prompts_path)
        self._initialized = True

    def _load_prompts(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading prompts from {path}: {e}")
            return {}

    def get(self, key, **kwargs):
        """
        Get a prompt by dot-notation key (e.g. 'deep_research.outline') and format it.
        """
        keys = key.split('.')
        val = self.prompts
        for k in keys:
            val = val.get(k)
            if val is None:
                return f"[Missing prompt: {key}]"
        
        if isinstance(val, str):
            try:
                return val.format(**kwargs)
            except KeyError as e:
                return val # Return raw if formatting fails or no args matching
        return val

    def get_system_prompt(self, enabled_tools_map):
        """
        Generates the full system prompt based on enabled tools.
        """
        p = self.prompts
        guidelines = []
        
        # Helper to check if tool is enabled
        def is_enabled(name):
            return enabled_tools_map.get(name, True)

        # 1. WEB PROJECTS
        if is_enabled("web_builder"):
            guidelines.append(p["guidelines"]["web_builder_enabled"])
        else:
            guidelines.append(p["guidelines"]["web_builder_disabled"])

        # 2. TARGETED EDITS (List of strings in JSON)
        if is_enabled("file_editor"):
            for line in p["guidelines"]["file_editor_enabled"]:
                guidelines.append(line)
        else:
            guidelines.append(p["guidelines"]["file_editor_disabled"])

        # 3. Conciseness
        guidelines.append(p["guidelines"]["conciseness"])

        # 4. WEB SEARCH
        if is_enabled("web_search"):
            guidelines.append(p["guidelines"]["web_search_enabled"])
        else:
            guidelines.append(p["guidelines"]["web_search_disabled"])

        # 5. CALENDAR
        if any(is_enabled(t) for t in ["calendar_add_event", "calendar_list_events"]):
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            calendar_prompt = p["guidelines"]["calendar_enabled"].format(current_time=current_time_str)
            guidelines.append(calendar_prompt)

        # Assemble logic
        parts = [
            p["system_prompt_intro"],
            p["critical_instruction"],
            p["exception_instruction"],
            "",
            p["guidelines_header"],
            "\n".join(guidelines)
        ]
        
        return "\n".join(parts)
