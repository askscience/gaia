from google import genai
from google.genai import types
from src.core.providers.base import BaseProvider

class GoogleProvider(BaseProvider):
    def __init__(self, api_key, model_name="gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self._client = None

    def _get_client(self):
        if not self._client:
            if not self.api_key:
                print("DEBUG: Gemini API key is missing!")
                raise ValueError("Gemini API key is missing. Please set it in Settings.")
            print(f"DEBUG: Initializing Gemini Client with key: {self.api_key[:5]}...{self.api_key[-5:] if len(self.api_key) > 5 else ''}")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate_response(self, messages, tools=None):
        print(f"DEBUG: Gemini generate_response called with model: {self.model_name}")
        history, system_instruction = self._process_messages(messages)
        print(f"DEBUG: Processed history: {history}")
        print(f"DEBUG: System instruction: {system_instruction}")
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction
        )
        
        try:
            response = self._get_client().models.generate_content(
                model=self.model_name,
                contents=history,
                config=config
            )
            print(f"DEBUG: Gemini raw response: {response}")
            return {
                "message": {
                    "role": "assistant",
                    "content": response.text
                }
            }
        except Exception as e:
            print(f"DEBUG: Gemini generate_response error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def stream_response(self, messages, tools=None):
        print(f"DEBUG: Gemini stream_response called with model: {self.model_name}")
        history, system_instruction = self._process_messages(messages)
        print(f"DEBUG: Processed history: {history}")
        print(f"DEBUG: System instruction: {system_instruction}")
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction
        )
        
        try:
            response = self._get_client().models.generate_content_stream(
                model=self.model_name,
                contents=history,
                config=config
            )
            for chunk in response:
                print(f"DEBUG: Gemini chunk: {chunk.text if hasattr(chunk, 'text') else 'NO TEXT'}")
                yield {
                    "message": {
                        "role": "assistant",
                        "content": chunk.text
                    }
                }
        except Exception as e:
            print(f"DEBUG: Gemini stream_response error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def list_models(self):
        try:
            if not self.api_key:
                return ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"]
            
            # Fetch ALL models from the SDK
            models = self._get_client().models.list()
            gemini_models = []
            for m in models:
                # Get the name, which is the unique ID
                name = getattr(m, 'name', None)
                if not name:
                    # If name is missing, try to see what's actually in there
                    print(f"DEBUG: Gemini Model object missing 'name'. Attributes: {dir(m)}")
                    continue
                
                # We show the ID exactly as the API gives it (or stripped for display)
                model_id = name.replace("models/", "")
                gemini_models.append(model_id)
            
            if not gemini_models:
                print("DEBUG: Gemini API returned empty model list.")
                return ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"]
                
            # Sort newest first (highest numbers/latest versions)
            return sorted(list(set(gemini_models)), reverse=True)
        except Exception as e:
            print(f"Error listing Gemini models: {e}")
            import traceback
            traceback.print_exc()
            return ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"]

    def _process_messages(self, messages):
        """Extract system instruction and prepare history."""
        system_instructions = []
        history = []
        
        for msg in messages:
            if msg['role'] == "system":
                system_instructions.append(msg['content'])
            else:
                role = "user" if msg['role'] == "user" else "model"
                history.append({"role": role, "parts": [{"text": msg['content']}]})
        
        system_instruction = "\n".join(system_instructions) if system_instructions else None
        return history, system_instruction

    def _prepare_history(self, messages):
        # Deprecated: use _process_messages instead
        history, _ = self._process_messages(messages)
        return history
