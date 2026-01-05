import json
import locale
import os
from src.core.config import ConfigManager

class LanguageManager:
    _instance = None

    def __new__(cls, language=None, languages_path=None):
        if cls._instance is None:
            cls._instance = super(LanguageManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, language=None, languages_path=None):
        if self._initialized: return
        
        # 1. Platform/Arg override (if passed explicitly)
        if language is None:
            # 2. Check Config
            config = ConfigManager()
            cfg_lang = config.get("app_language", "auto")
            
            if cfg_lang and cfg_lang != "auto":
                language = cfg_lang
            else:
                # 3. System Detection
                language = self._detect_system_language()
        
        self.language = language
        
        if languages_path is None:
            # Default to src/core/languages/lang_{lang}.json
            base_dir = os.path.dirname(os.path.abspath(__file__))
            languages_path = os.path.join(base_dir, "languages", f"lang_{language}.json")
            
            # Fallback to en if specific language file doesn't exist
            if not os.path.exists(languages_path) and language != "en":
                 print(f"Language file for '{language}' not found, falling back to 'en'")
                 languages_path = os.path.join(base_dir, "languages", "lang_en.json")
        
        self.strings = self._load_strings(languages_path)
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

    def _load_strings(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading languages from {path}: {e}")
            return {}

    def get(self, key, **kwargs):
        """
        Get a UI string by dot-notation key (e.g. 'window.title') and format it.
        """
        keys = key.split('.')
        val = self.strings
        for k in keys:
            val = val.get(k)
            if val is None:
                return f"[Missing string: {key}]"
        
        if isinstance(val, str):
            try:
                return val.format(**kwargs)
            except KeyError as e:
                return val # Return raw if formatting fails
        return val
