from anthropic import Anthropic
from src.core.providers.base import BaseProvider

class AnthropicProvider(BaseProvider):
    def __init__(self, api_key, model_name="claude-3-5-sonnet-20240620"):
        self.api_key = api_key
        self.model_name = model_name
        self._client = None

    def _get_client(self):
        if not self._client:
            if not self.api_key:
                raise ValueError("Anthropic API key is missing.")
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def generate_response(self, messages, tools=None):
        # Claude expects system prompt separately
        system_msg = next((m['content'] for m in messages if m['role'] == 'system'), "")
        other_msgs = [m for m in messages if m['role'] != 'system']
        
        kwargs = {}
        if tools:
            kwargs['tools'] = self._convert_tools(tools)
        
        response = self._get_client().messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=system_msg,
            messages=other_msgs,
            **kwargs
        )
        return self._convert_to_ollama_format(response)

    def stream_response(self, messages, tools=None):
        system_msg = next((m['content'] for m in messages if m['role'] == 'system'), "")
        other_msgs = [m for m in messages if m['role'] != 'system']
        
        with self._get_client().messages.stream(
            model=self.model_name,
            max_tokens=4096,
            system=system_msg,
            messages=other_msgs
        ) as stream:
            for text in stream.text_stream:
                yield {"message": {"role": "assistant", "content": text}}

    def _convert_tools(self, tools):
        # Conversion logic for Anthropic tool format if needed
        return tools 

    def _convert_to_ollama_format(self, response):
        return {
            "message": {
                "role": "assistant",
                "content": response.content[0].text if response.content else ""
            }
        }

    def list_models(self):
        try:
            if not self.api_key:
                return ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
            # Anthropic handles listing models via client.models.list() in newer SDKs
            models = self._get_client().models.list()
            return sorted([m.id for m in models])
        except Exception as e:
            print(f"Error listing Anthropic models: {e}")
            return ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
