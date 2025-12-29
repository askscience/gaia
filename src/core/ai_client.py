from src.core.config import ConfigManager
from src.core.providers.ollama import OllamaProvider
from src.core.providers.openai_provider import OpenAIProvider
from src.core.providers.google_provider import GoogleProvider
from src.core.providers.anthropic_provider import AnthropicProvider

class AIClient:
    def __init__(self):
        self.config = ConfigManager()
        self.provider = self._get_provider()

    def _get_provider(self):
        provider_type = self.config.get("provider", "ollama")
        
        # Get provider-specific model
        model_key = f"{provider_type}_model"
        model = self.config.get(model_key)
        if not model: # Fallback to generic for backward compatibility
            model = self.config.get("model", "granite4:latest")
        
        # Get provider-specific API key
        key_name = f"{provider_type}_api_key"
        api_key = self.config.get(key_name, "")
        if not api_key: # Fallback to generic for backward compatibility
            api_key = self.config.get("api_key", "")

        if provider_type == "ollama":
            return OllamaProvider(model)
        elif provider_type == "openai":
            return OpenAIProvider(api_key, model_name=model)
        elif provider_type == "gemini":
            return GoogleProvider(api_key, model_name=model)
        elif provider_type == "anthropic":
            return AnthropicProvider(api_key, model_name=model)
        elif provider_type == "zai":
            # Check if coding plan API should be used
            use_coding = self.config.get("zai_coding_plan", False)
            if use_coding:
                base_url = "https://api.z.ai/api/coding/paas/v4/"
            else:
                base_url = "https://api.z.ai/api/paas/v4/"
            return OpenAIProvider(api_key, base_url=base_url, model_name=model)
        elif provider_type == "mistral":
            return OpenAIProvider(api_key, base_url="https://api.mistral.ai/v1", model_name=model)
        
        return OllamaProvider(model)

    def generate_response(self, messages, tools=None):
        try:
            return self.provider.generate_response(messages, tools)
        except Exception as e:
            return {"message": {"content": f"Error: {str(e)}", "role": "assistant"}}

    def stream_response(self, messages, tools=None):
        try:
            yield from self.provider.stream_response(messages, tools)
        except Exception as e:
            yield {"message": {"content": f"Error: {str(e)}", "role": "assistant"}}

    def list_models(self):
        return self.provider.list_models()
