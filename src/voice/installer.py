import os
import requests
import zipfile
import tarfile
import threading
from pathlib import Path
from src.core.config import ConfigManager

class VoiceInstaller:
    def __init__(self):
        self.config = ConfigManager()
        self.base_dir = os.path.join(Path.home(), ".gaia", "voice")
        self.vosk_dir = os.path.join(self.base_dir, "vosk")
        self.piper_dir = os.path.join(self.base_dir, "piper")
        
        os.makedirs(self.vosk_dir, exist_ok=True)
        os.makedirs(self.piper_dir, exist_ok=True)
        
        # Hardcoded recommended models
        self.VOSK_MODELS = {
            "en": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
            "fr": "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip",
            "de": "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip",
            "es": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
            "it": "https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip"
        }
        
        # Piper - Simplified for Linux Install
        # We fetch the binary release for linux-amd64
        self.PIPER_URL = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz"
        
        # Piper Voices (ONNX + JSON) - Using stable low quality for speed/size
        self.PIPER_VOICES = {
            "en": {
                "name": "en_US-lessac-medium",
                "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
                "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
            },
            "fr": {
                "name": "fr_FR-siwis-medium",
                "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx",
                "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json"
            },
            "de": {
                "name": "de_DE-thorsten-medium",
                "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx",
                "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx.json"
            },
            "es": {
                "name": "es_ES-sharvard-medium",
                "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx",
                "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx.json"
            },
            "it": {
                "name": "it_IT-paola-medium",
                "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx",
                "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx.json"
            }
        }

    def check_status(self):
        """Return dict of status: installed, missing."""
        status = {
            "piper_bin": os.path.exists(os.path.join(self.piper_dir, "piper", "piper")),
            "vosk_models": {},
            "piper_voices": {}
        }
        
        # Check Vosk models (directory exists and not empty)
        for lang in self.VOSK_MODELS:
             # Heuristic: check if subdir exists that matches language code roughly
             # Actual extraction creates a folder like 'vosk-model-small-en-us-0.15'
             # We can save a marker or config to know which one is current
             # For now, let's just check if we have configured it.
             pass
             
        return status

    def install_piper(self, language="en", progress_callback=None):
        if progress_callback: progress_callback(0, "Downloading Piper...")
        try:
             # Only download binary if not exists (or force?)
             # For now, always re-download to be safe or maybe checking existence is better.
             # But if user clicks 'Re-install' they expect re-download.
             self._download_and_extract(self.PIPER_URL, self.piper_dir, is_tar=True, progress_callback=progress_callback)
             
             if progress_callback: progress_callback(0.95, f"Downloading Voice for {language}...")
             
             # Download voice for requested language
             voice_info = self.PIPER_VOICES.get(language)
             if not voice_info:
                 print(f"Warning: No voice model for {language}, falling back to English.")
                 voice_info = self.PIPER_VOICES["en"]
                 
             self._download_file(voice_info["onnx"], self.piper_dir, progress_callback)
             self._download_file(voice_info["json"], self.piper_dir, progress_callback)
             
             # Also ensure English is available as fallback?
             if language != "en":
                 en_voice = self.PIPER_VOICES["en"]
                 if not os.path.exists(os.path.join(self.piper_dir, en_voice["name"] + ".onnx")):
                      self._download_file(en_voice["onnx"], self.piper_dir, None)
                      self._download_file(en_voice["json"], self.piper_dir, None)
             
             if progress_callback: progress_callback(1, "Piper Installed.")
             return True
        except Exception as e:
            print(f"Error installing Piper: {e}")
            if progress_callback: progress_callback(-1, f"Error: {e}")
            return False

    def install_vosk_model(self, language, progress_callback=None):
        url = self.VOSK_MODELS.get(language)
        if not url:
             if progress_callback: progress_callback(-1, f"No model for {language}")
             return False
             
        if progress_callback: progress_callback(0, f"Downloading Vosk model for {language}...")
        try:
             extract_path = self._download_and_extract(url, self.vosk_dir, is_tar=False, progress_callback=progress_callback)
             
             # Save this path to config
             self.config.set(f"vosk_model_path_{language}", extract_path)
             # Also set as default if current language
             if language == self.config.get("app_language", "en") or language == "en":
                  self.config.set("vosk_model_path", extract_path)
                  
             if progress_callback: progress_callback(1, "Vosk Model Installed.")
             return True
        except Exception as e:
             if progress_callback: progress_callback(-1, f"Error: {e}")
             return False

    def _download_and_extract(self, url, dest_dir, is_tar=False, progress_callback=None):
        local_filename = url.split('/')[-1]
        local_path = os.path.join(dest_dir, local_filename)
        
        # Download
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_length = int(r.headers.get('content-length', 0))
            downloaded = 0
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_length > 0:
                         # 0.0 to 0.8 range for download
                         prog = (downloaded / total_length) * 0.8
                         progress_callback(prog, "Downloading...")
                         
        # Extract
        if progress_callback: progress_callback(0.9, "Extracting...")
        
        extracted_folder_name = None
        
        if is_tar:
            with tarfile.open(local_path, "r:gz") as tar:
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    return prefix == abs_directory
                
                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                    tar.extractall(path, members, numeric_owner=numeric_owner) 
                    
                safe_extract(tar, dest_dir)
                # Assume strictly one folder or binary? Piper tar has 'piper/' folder.
                extracted_folder_name = "piper" 
        else:
            with zipfile.ZipFile(local_path, 'r') as zip_ref:
                # Find the root folder name
                name_list = zip_ref.namelist()
                top_level = {n.split('/')[0] for n in name_list}
                if len(top_level) == 1:
                    extracted_folder_name = list(top_level)[0]
                
                zip_ref.extractall(dest_dir)
                
        # Cleanup zip? Keep it for cache? Let's keep it for now or delete.
        os.remove(local_path)
        
        return os.path.join(dest_dir, extracted_folder_name) if extracted_folder_name else dest_dir

    def _download_file(self, url, dest_dir, progress_callback=None):
        local_filename = url.split('/')[-1]
        local_path = os.path.join(dest_dir, local_filename)
        
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
