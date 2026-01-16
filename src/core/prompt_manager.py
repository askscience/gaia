import json
import os
import locale
from datetime import datetime
from src.core.config import ConfigManager

class PromptManager:
    _instance = None

    def __new__(cls, language=None, prompts_path=None):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, language=None, prompts_path=None):
        if self._initialized: return
        
        # 1. Platform/Arg override (if passed explicitly)
        if language is None:
            # 2. Check Config
            config = ConfigManager()
            cfg_lang = config.get("app_language", "auto")
            
            if cfg_lang and cfg_lang != "auto":
                language = cfg_lang
            else:
                # 3. System Detection (Duplicate logic or import LanguageManager? 
                # Better to keep it self-contained or depend on LanguageManager. 
                # Let's replicate simple detection to avoid circular deps if LanguageManager uses PromptManager)
                language = self._detect_system_language()
        
        self.language = language or "en"
        
        if prompts_path is None:
            # Default to src/core/prompts/prompts_{lang}.json
            base_dir = os.path.dirname(os.path.abspath(__file__))
            prompts_path = os.path.join(base_dir, "prompts", f"prompts_{self.language}.json")
            
            # Fallback to en if specific language file doesn't exist
            if not os.path.exists(prompts_path) and self.language != "en":
                 print(f"Prompts for language '{self.language}' not found, falling back to 'en'")
                 prompts_path = os.path.join(base_dir, "prompts", "prompts_en.json")
        
        self.prompts = self._load_prompts(prompts_path)
        self._initialized = True

    def _detect_system_language(self):
        """Detect the system language code (e.g. 'en', 'es', 'fr')."""
        try:
            # Get default locale like 'en_US.UTF-8'
            loc = locale.getdefaultlocale()[0]
            if loc:
                return loc.split('_')[0]
        except Exception as e:
            print(f"Error detecting locale: {e}")
        return "en"

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

        # 6. VOICE MODE
        is_voice = enabled_tools_map.get("voice_mode", False)
        if is_voice:
             # Use voice mode prompt if available, else a default hardcoded one for safety
             voice_prompt = p.get("voice_mode_guidelines", 
                "You are in Voice Mode. Keep answers conversational, short, and purely text. Do not use markdown, lists, or code blocks.")
             guidelines.append(voice_prompt)

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
