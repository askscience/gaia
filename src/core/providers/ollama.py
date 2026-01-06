import ollama
from src.core.providers.base import BaseProvider

class OllamaProvider(BaseProvider):
    def __init__(self, model_name="granite4:latest"):
        self.model_name = model_name

    def generate_response(self, messages, tools=None):
        kwargs = {}
        if tools:
            kwargs['tools'] = tools
        
        client = ollama.Client(timeout=1200.0)
        return client.chat(model=self.model_name, messages=messages, **kwargs)

    def stream_response(self, messages, tools=None):
        kwargs = {'stream': True}
        if tools:
            kwargs['tools'] = tools
        
        # Use a custom client with increased timeout to prevent "Read operation timed out"
        # during long code generation tasks.
        client = ollama.Client(timeout=1200.0) 
        stream = client.chat(model=self.model_name, messages=messages, **kwargs)
        
        for chunk in stream:
            # Convert attributes to dict, handling both object and dict styles for safety
            res = {}
            
            # Helper to safely get attribute or dict key
            def get_val(obj, key, default=None):
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)

            # Get message
            msg_obj = get_val(chunk, 'message')
            if msg_obj:
                msg_dict = {
                    "role": get_val(msg_obj, 'role'),
                    "content": get_val(msg_obj, 'content')
                }
                
                # Handle tool calls
                tool_calls = get_val(msg_obj, 'tool_calls')
                if tool_calls:
                    msg_dict["tool_calls"] = []
                    for tc in tool_calls:
                        function = get_val(tc, 'function')
                        msg_dict["tool_calls"].append({
                            "function": {
                                "name": get_val(function, 'name'),
                                "arguments": get_val(function, 'arguments')
                            }
                        })
                
                res["message"] = msg_dict
            
            yield res

    def list_models(self):
        try:
            response = ollama.list()
            models = []
            raw_models = []
            if isinstance(response, dict):
                raw_models = response.get('models', [])
            elif hasattr(response, 'models'):
                raw_models = response.models
            
            for m in raw_models:
                if isinstance(m, dict):
                    name = m.get('model') or m.get('name')
                else:
                    name = getattr(m, 'model', None) or getattr(m, 'name', None)
                if name:
                    models.append(name)
            return sorted(models)
        except Exception as e:
            print(f"Error listing Ollama models: {e}")
            return []
