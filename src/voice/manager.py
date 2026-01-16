import threading
import time
import os
from src.voice.stt import VoskListener
from src.voice.tts import PiperTTS
from src.core.config import ConfigManager

class VoiceManager:
    _instance = None

    def __new__(cls, app_window=None):
        if cls._instance is None:
            cls._instance = super(VoiceManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, app_window=None):
        if self.initialized:
            if app_window:
                self.window = app_window
            return
            
        self.config = ConfigManager()
        self.window = app_window
        self.listener = VoskListener()
        self.tts = PiperTTS()
        self.active = False
        self.listening_thread = None
        self.interaction_active = False # True when processing a request
        self.conversation_deadline = 0 # Timestamp until which wake word is optional
        
        # Load model path based on language
        current_lang = self.config.get("app_language", "en")
        if current_lang == "auto": current_lang = "en"
        
        # Try language specific path first
        model_path = self.config.get(f"vosk_model_path_{current_lang}")
        
        # If not set, try to find folder matching language in local directory
        # This fixes the issue where switching language (e.g. to IT) falls back to generic (EN) model 
        # because defaults were prioritized over discovery.
        if not model_path:
             local_vosk = os.path.join(os.path.expanduser("~/.gaia/voice/vosk"))
             if os.path.exists(local_vosk):
                 # Try to find folder matching language
                 # e.g vosk-model-small-fr-0.22 or similar
                 for f in os.scandir(local_vosk):
                     if f.is_dir() and f"model" in f.name and f"-{current_lang}" in f.name:
                         # Found a potential match on disk
                         model_path = f.path
                         print(f"[VoiceManager] Discovered localized model: {model_path}")
                         # Update config to persist this finding
                         self.config.set(f"vosk_model_path_{current_lang}", model_path)
                         break

        # Fallback to generic path (likely English or last installed)
        if not model_path:
             model_path = self.config.get("vosk_model_path")
             
        # Final fallback: pick ANY model in the directory
        if not model_path:
             local_vosk = os.path.join(os.path.expanduser("~/.gaia/voice/vosk"))
             if os.path.exists(local_vosk):
                 subdirs = [f.path for f in os.scandir(local_vosk) if f.is_dir()]
                 if subdirs: model_path = subdirs[0]

        if model_path:
             print(f"[VoiceManager] Loading Vosk model from: {model_path}")
             self.listener.set_model_path(model_path)
            
        # Configure TTS path if installed locally
        local_piper_bin = os.path.join(os.path.expanduser("~/.gaia/voice/piper/piper/piper"))
        if os.path.exists(local_piper_bin):
            self.tts.set_executable_path(local_piper_bin)

        self.initialized = True
        
        # Helper or init logic can go here if needed
        pass

    def get_voice_for_language(self, lang_code):
        """Get the preferred voice model for a specific language."""
        if lang_code == "auto": lang_code = "en"
        
        # 1. Check Preferences
        voice_prefs = self.config.get("voice_preferences", {})
        preferred = voice_prefs.get(lang_code)
        
        # Verify preference validity (must match language prefix to be safe? or just trust user?)
        # Let's trust the user selection, but maybe check file existence if we were strict. 
        # For now, if it exists, use it.
        if preferred:
            return preferred
            
        # 2. Discovery / Fallback
        # No preference found, let's find a default for this language
        lang_map = { "en": "en_", "fr": "fr_", "de": "de_", "es": "es_", "it": "it_" }
        prefix = lang_map.get(lang_code, "en_")
        
        found_model = None
        piper_dir = os.path.join(os.path.expanduser("~/.gaia/voice/piper"))
        
        if os.path.exists(piper_dir):
             # Try to find any model starting with the language prefix
             for f in os.listdir(piper_dir):
                 if f.endswith(".onnx") and f.startswith(prefix):
                     found_model = f[:-5]
                     break
        
        # 3. Last Resort (English default)
        if not found_model:
            found_model = "en_US-lessac-medium"
            
        # Save this discovery as the preference so we remember it
        voice_prefs[lang_code] = found_model
        self.config.set("voice_preferences", voice_prefs)
            
        return found_model

    def start_voice_mode(self):
        """Enable voice mode: Hide GUI, start listening loop."""
        if self.active: return
        
        # Always check if we need to reload or load model (e.g. language change or first install)
        # Check current language
        current_lang = self.config.get("app_language", "en")
        if current_lang == "auto": current_lang = "en"
        
        target_model_path = self.config.get(f"vosk_model_path_{current_lang}")
        if not target_model_path: target_model_path = self.config.get("vosk_model_path")
        
        # If we have a path and (no model loaded OR different path?)
        # For simplicity, if model is not loaded, load it.
        # If we want to support switching languages dynamically without restart, we should compare paths.
        # Vosk Model object doesn't easily expose path. 
        # But we can store it in listener.
        
        if not self.listener.model and target_model_path:
             print(f"[VoiceManager] Late loading model: {target_model_path}")
             self.listener.set_model_path(target_model_path)
             
        if not self.listener.model:
             print("VoiceManager: Cannot start, no model loaded.")
             return 

        self.active = True
        if self.window:
            self.window.set_visible(False)
            
        self.start_listening()

    def stop_voice_mode(self):
        """Disable voice mode: Stop listening."""
        self.active = False
        self.interaction_active = False
        if self.listener:
            self.listener.stop()

    def start_listening(self):
        if self.listening_thread and self.listening_thread.is_alive():
            return

        def run_loop():
            # Initial greeting?
            # self.tts.speak("Voice mode active.")
            
            self.listener.listen_loop(self.on_speech_result)
            
        self.listening_thread = threading.Thread(target=run_loop, daemon=True)
        self.listening_thread.start()

    def on_speech_result(self, text, final, timestamp=None):
        if not self.active: return
        
        text = text.lower().strip()
        if not text: return

        # Simple State Machine
        # 1. Waiting for Wake Word
        # 2. Listening for Command (Active Interaction)
        
        # Check context: Are we in an active conversation?
        # Use the start time of the utterance if available to determine if user spoke within the window
        check_time = timestamp if timestamp else time.time()
        
        if check_time < self.conversation_deadline:
             print(f"[VoiceManager] In conversation context. Bypassing wake word (Latency: {time.time() - check_time:.2f}s).")
             self.process_request(text)
             return

        # Localized/Error-prone variations of "Hey"
        wake_words = [
            "hey", "hi", "hello",       # English
            "ehi", "ei", "ciao",        # Italian
            "bonjour", "salut", "hé",   # French
            "hallo", "he",              # German
            "hola", "oye",              # Spanish
        ]
        
        text_lower = text.lower()
        
        # Check if text STARTS with any of these (followed by space or is the only word matches widely)
        # Simplify: just check existence at start
        is_wake = False
        for w in wake_words:
            if text_lower.startswith(w):
                is_wake = True
                break
        
        # Also keep robust "hey gaia" / "hey guys" check just in case
        if "hey gaia" in text_lower or "hey guys" in text_lower:
            is_wake = True

        if is_wake:
            print(f"[VoiceManager] Wake word detected in: '{text}'")
            # Extract query
            # We might want to strip "hey gaia"
            # But user said "the entire text request will be passed"
            
            self.process_request(text)
        else:
            print(f"[VoiceManager] Ignored (no wake word): '{text}'")
        
    def process_request(self, text):
        if self.interaction_active: return # Already working?
        self.interaction_active = True
        
        print(f"[Voice] Processing: {text}")
        
        # We need to run the AI through the ChatPage logic to utilize tools
        # We assume the MainWindow has an active page
        if self.window and hasattr(self.window, 'get_active_chat_page'):
            page = self.window.get_active_chat_page()
            if page:
                # We need to run_ai on the main thread safely? 
                # run_ai is threaded internally, but UI updates need main thread.
                # However, run_ai takes a text input.
                
                def result_callback(response_text, has_artifacts=False):
                    # This runs when AI is done (or finding chunks)
                    # We want the FINAL text for TTS.
                    # Or streaming? Piper is fast, but let's wait for full sentence or full text.
                    # For now, let's assume we get the full text at the end or chunks.
                    
                    if has_artifacts and self.window:
                        print("[VoiceManager] Artifacts detected. Maximizing view.")
                        # Ensure artifacts panel is detected/loaded via refresh logic in ChatPage (already triggered)
                        
                        # FORCE Window Visibility since we are in Voice Mode (hidden)
                        self.window.set_visible(True)
                        self.window.present()
                        
                        # Just enable visibility and fullscreen
                        self.window.show_artifacts()
                        
                        # Toggle fullscreen if not already?
                        # toggle_artifact_fullscreen logic: if visible, hide chat.
                        # We want to ensure we ARE in fullscreen mode.
                        # Check current state?
                        # MainWindow.toggle_artifact_fullscreen toggles based on ChatView visibility.
                        # If ChatView is Visible -> Hide it (Fullscreen mode).
                        
                        # We need to access main_paned children to check state?
                        # Or just blindly call toggle if chat is visible.
                        # self.window.main_paned usually has start_child (Overview) and end_child (Artifacts).
                        # Actually start_child is TabOverview.
                        
                        # Let's trust toggle_artifact_fullscreen acts as a toggle.
                        # We want it ON.
                        # If TabOverview is visible, we toggle.
                        if self.window.tab_overview.get_visible():
                             self.window.toggle_artifact_fullscreen()

                    if response_text:
                        # Get selected voice or default based on CURRENT language
                        # This ensures multi-language support works dynamically
                        current_lang = self.config.get("app_language", "en")
                        if current_lang == "auto": current_lang = "en"
                        
                        voice_model = self.get_voice_for_language(current_lang)
                        
                        # Stop listening while speaking to avoid self-trigger
                        print("[VoiceManager] Pausing listener for TTS...")
                        self.listener.pause()
                        
                        self.tts.speak(response_text, model=voice_model)
                        
                        print("[VoiceManager] Resuming listener...")
                        self.listener.resume()
                        
                        # Set conversation deadline extensions (10 seconds)
                        # So user can reply without wake word
                        self.conversation_deadline = time.time() + 10.0
                        print(f"[VoiceManager] Conversation active for 10s (until {self.conversation_deadline})")

                    self.interaction_active = False

                from gi.repository import GLib
                GLib.idle_add(page.run_ai_voice, text, result_callback)
            else:
                 print("No active chat page found for voice request.")
                 self.interaction_active = False
        else:
            print("Window not connected or ready.")
            self.interaction_active = False

