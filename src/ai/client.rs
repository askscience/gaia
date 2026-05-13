use crate::ai::{AiProvider, AnthropicProvider, GoogleProvider, OllamaProvider, OpenAIProvider};
use crate::config::ConfigManager;
use serde_json::Value;

pub struct AIClient {
    provider: Box<dyn AiProvider>,
}

impl AIClient {
    pub fn new() -> Self {
        let config = ConfigManager::global();
        let provider_type = config.get("provider");

        let provider: Box<dyn AiProvider> = match provider_type.as_str() {
            "openai" => {
                let api_key = config.get("openai_api_key");
                let model = config.get("openai_model");
                Box::new(OpenAIProvider::new(api_key, None, model))
            }
            "anthropic" => {
                let api_key = config.get("anthropic_api_key");
                let model = config.get("anthropic_model");
                Box::new(AnthropicProvider::new(api_key, model))
            }
            "gemini" => {
                let api_key = config.get("google_api_key");
                let model = config.get("google_model");
                Box::new(GoogleProvider::new(api_key, model))
            }
            "zai" => {
                let api_key = config.get("zai_api_key");
                let model = config.get("zai_model");
                Box::new(OpenAIProvider::new(
                    api_key,
                    Some("https://api.z.ai/api/paas/v4/".to_string()),
                    model,
                ))
            }
            "mistral" => {
                let api_key = config.get("mistral_api_key");
                let model = config.get("mistral_model");
                Box::new(OpenAIProvider::new(
                    api_key,
                    Some("https://api.mistral.ai/v1".to_string()),
                    model,
                ))
            }
            _ => {
                let model = config.get("ollama_model");
                let host = config.get("ollama_host");
                Box::new(OllamaProvider::new(
                    if host.is_empty() {
                        "http://localhost:11434".to_string()
                    } else {
                        host
                    },
                    model,
                ))
            }
        };

        AIClient { provider }
    }

    pub async fn generate_response(&self, messages: &[Value], tools: Option<&[Value]>) -> Value {
        self.provider.generate_response(messages, tools).await
    }

    pub async fn list_models(&self) -> Vec<String> {
        self.provider.list_models().await
    }
}
