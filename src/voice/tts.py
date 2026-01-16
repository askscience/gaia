import subprocess
import os

class PiperTTS:
    def __init__(self, model_path=None):
        self.executable = "piper" # Default system command
        
    def set_executable_path(self, path):
        if os.path.exists(path):
            self.executable = path

    def speak(self, text: str, model: str = "en_US-lessac-medium"):
        """
        Speak the given text using Piper TTS.
        
        Args:
            text (str): The text to speak.
            model (str): The voice model to use.
        """
        try:
            # Basic implementation using subprocess
            # piper --model en_US-lessac-medium --output_raw | aplay -r 22050 -f S16_LE -t raw -
            
            # Note: This requires 'aplay' (alsa-utils) which is standard on Linux
            # We construct the pipeline
            
            # Resolve model path
            final_model = model
            if model == "Default" or not os.path.exists(model):
                # Try to find any onnx in ~/.gaia/voice/piper
                possible_path = os.path.join(os.path.expanduser("~/.gaia/voice/piper"), f"{model}.onnx")
                if os.path.exists(possible_path):
                     final_model = possible_path
                else:
                    # Search specifically for any onnx
                    piper_dir = os.path.expanduser("~/.gaia/voice/piper")
                    if os.path.exists(piper_dir):
                        for f in os.listdir(piper_dir):
                            if f.endswith(".onnx"):
                                final_model = os.path.join(piper_dir, f)
                                break
            
            print(f"[PiperTTS] Speaking: '{text}' using model {final_model}")
            
            # Ensure final model is absolute path
            final_model = os.path.abspath(final_model)
            if not os.path.exists(final_model):
                 print(f"[PiperTTS] Error: Model file not found: {final_model}")
                 return

            piper_cmd = [self.executable, "--model", final_model, "--output_raw"]
            aplay_cmd = ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"]
            
            # Pipe text to piper
            # Enable stderr for debugging
            p1 = subprocess.Popen(piper_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p2 = subprocess.Popen(aplay_cmd, stdin=p1.stdout, stderr=subprocess.PIPE)
            p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
            
            p1.communicate(input=text.encode('utf-8'))
            out, err = p2.communicate()
            
            # Check for piper errors using p1.poll()?
            # We already communicated.
            # p1.stderr might have content
            if p1.returncode != 0 and p1.stderr:
                 print(f"[PiperTTS] Piper Error: {p1.stderr.read().decode()}")
            if p2.returncode != 0:
                 print(f"[PiperTTS] Aplay Error: {err.decode() if err else 'Unknown'}")
            
        except FileNotFoundError:
            print("Error: 'piper' or 'aplay' not found in PATH.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error speaking text: {e}")

    def stop(self):
        # Todo: Implement process killing if needed
        pass
