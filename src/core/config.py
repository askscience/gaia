import json
import os
from pathlib import Path

def get_artifacts_dir():
    """Get the centralized directory for artifacts."""
    # Use XDG_DATA_HOME or default to ~/.local/share
    xdg_data = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
    artifacts_dir = os.path.join(xdg_data, 'gaia', 'artifacts')
    os.makedirs(artifacts_dir, exist_ok=True)
    return artifacts_dir

class ConfigManager:
    _instance = None
    
    DEFAULT_CONFIG = {
        "model": "granite4:latest",
        "system_prompt": "You are a helpful AI assistant for Linux users."
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        self.config_dir = os.path.join(Path.home(), ".config", "gaia")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)
            
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()
