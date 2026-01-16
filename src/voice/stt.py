import os
import json
import queue
import sys
import time
import threading
try:
    import sounddevice as sd
except OSError:
    sd = None
    print("Warning: PortAudio library not found. Voice mode will be unavailable.")
except ImportError:
    sd = None
    print("Warning: sounddevice module not found. Voice mode will be unavailable.")

from vosk import Model, KaldiRecognizer

class VoskListener:
    def __init__(self, language="en"):
        self.language = language
        self.q = queue.Queue()
        self.model = self._load_model()
        self.recognizer = None
        self.running = False
        self.paused = False
        self.device = None # Default device
        
        if sd is None:
             print("VoskListener: sounddevice/PortAudio not available.")

    def _load_model(self):
        # Helper to find model path based on language
        # For now, we look in ~/.vosk or local 'model' folder
        # This is a placeholder for robust model loading logic
        return None # We will load lazily or need a configured path

    def set_model_path(self, path):
        if not os.path.exists(path):
            print(f"Vosk model path not found: {path}")
            return False
        try:
            self.model = Model(path)
            return True
        except Exception as e:
            print(f"Failed to load Vosk model: {e}")
            return False

    def listen_loop(self, on_result):
        """
        Continuously listen.
        on_result(text, is_final) callback.
        """
        if not self.model:
            print("No Vosk model loaded.")
            return

        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.running = True

        def callback(indata, frames, time, status):
            if status:
                print(status, file=sys.stderr)
            self.q.put(bytes(indata))

        if sd is None:
             print("Error: sounddevice not initialized (missing PortAudio?).")
             return

        print("[VoskListener] Starting audio stream...")
        try:
            with sd.RawInputStream(samplerate=16000, blocksize=8000, device=self.device, dtype='int16',
                                   channels=1, callback=callback):
                print("[VoskListener] Audio stream active. Listening...")
                utterance_start = None

                while self.running:
                    data = self.q.get()
                    if self.paused:
                        continue
                    if self.recognizer.AcceptWaveform(data):
                        res = json.loads(self.recognizer.Result())
                        if res.get('text'):
                            print(f"[Vosk] Final recognized: '{res['text']}'")
                            # Pass the start time of this utterance if we captured it, else now
                            t_start = utterance_start if utterance_start else time.time()
                            on_result(res['text'], final=True, timestamp=t_start)
                        
                        # Reset for next utterance
                        utterance_start = None
                    else:
                        # Partial results debugging
                        partial = json.loads(self.recognizer.PartialResult())
                        p_text = partial.get('partial', '')
                        if p_text:
                            # If this is the start of a new utterance (or we haven't marked it yet)
                            if utterance_start is None:
                                utterance_start = time.time()
                            print(f"[Vosk] Partial: {p_text}", end='\r', flush=True)
                        
        except Exception as e:
            print(f"Error in listen loop: {e}")
        finally:
            self.running = False

    def stop(self):
        self.running = False
        
    def pause(self):
        """Temporarily ignore audio."""
        self.paused = True
    
    def resume(self):
        """Resume processing audio."""
        self.paused = False
