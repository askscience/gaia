use async_trait::async_trait;
use reqwest::Client;
use serde_json::{Value, json};

use crate::ai::base::AiProvider;

pub struct AnthropicProvider {
    http: Client,
    api_key: String,
    model: String,
}

impl AnthropicProvider {
    pub fn new(api_key: String, model: String) -> Self {
        AnthropicProvider {
            http: Client::new(),
            api_key,
            model,
        }
    }
}

#[async_trait]
impl AiProvider for AnthropicProvider {
    async fn generate_response(&self, messages: &[Value], tools: Option<&[Value]>) -> Value {
        let (system_prompt, chat_messages) = separate_system_messages(messages);

        let mut body = json!({
            "model": self.model,
            "max_tokens": 4096,
            "messages": chat_messages,
        });

        if let Some(sys) = system_prompt {
            body["system"] = json!(sys);
        }

        if let Some(t) = tools {
            body["tools"] = json!(t);
        }

        match self
            .http
            .post("https://api.anthropic.com/v1/messages")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
        {
            Ok(resp) => {
                let status = resp.status();
                let json: Value = resp.json().await.unwrap_or_else(
                    |e| json!({"error": format!("Failed to parse response: {}", e)}),
                );
                if status.is_success() {
                    json
                } else {
                    json!({"error": json.to_string()})
                }
            }
            Err(e) => json!({"error": format!("Anthropic API error: {}", e)}),
        }
    }

    async fn list_models(&self) -> Vec<String> {
        vec![self.model.clone()]
    }
}

fn separate_system_messages(messages: &[Value]) -> (Option<String>, Vec<Value>) {
    let mut system_parts: Vec<String> = Vec::new();
    let mut chat: Vec<Value> = Vec::new();

    for msg in messages {
        let role = msg["role"].as_str().unwrap_or("user");
        if role == "system" {
            if let Some(content) = msg["content"].as_str() {
                system_parts.push(content.to_string());
            } else if let Some(content) = msg["content"].as_array() {
                let text: String = content
                    .iter()
                    .filter_map(|c| c["text"].as_str())
                    .collect::<Vec<_>>()
                    .join("\n");
                system_parts.push(text);
            }
        } else {
            chat.push(msg.clone());
        }
    }

    let system_prompt = if system_parts.is_empty() {
        None
    } else {
        Some(system_parts.join("\n\n"))
    };

    (system_prompt, chat)
}
