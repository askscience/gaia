use async_trait::async_trait;
use ollama_rs::Ollama;
use ollama_rs::generation::completion::request::GenerationRequest;
use serde_json::{Value, json};
use url::Url;

use crate::ai::base::AiProvider;

pub struct OllamaProvider {
    ollama: Ollama,
    model: String,
}

impl OllamaProvider {
    pub fn new(host_url: String, model: String) -> Self {
        let parsed = Url::parse(&host_url).unwrap_or_else(|_| {
            Url::parse("http://localhost:11434").expect("invalid default ollama url")
        });
        let host = parsed.host_str().unwrap_or("localhost").to_string();
        let port = parsed.port().unwrap_or(11434);
        let ollama = Ollama::new(host, port);
        OllamaProvider { ollama, model }
    }
}

#[async_trait]
impl AiProvider for OllamaProvider {
    async fn generate_response(&self, messages: &[Value], tools: Option<&[Value]>) -> Value {
        let (system_prompt, prompt) = build_prompt(messages);

        let mut request = GenerationRequest::new(self.model.clone(), prompt);
        if let Some(sys) = system_prompt {
            request = request.system(sys);
        }

        if let Some(t) = tools {
            if !t.is_empty() {
                let _ = t;
            }
        }

        match self.ollama.generate(request).await {
            Ok(response) => {
                json!({
                    "content": response.response,
                    "model": self.model,
                    "done": response.done,
                })
            }
            Err(e) => {
                json!({"error": format!("Ollama generation failed: {}", e)})
            }
        }
    }

    async fn list_models(&self) -> Vec<String> {
        match self.ollama.list_local_models().await {
            Ok(models) => models.into_iter().map(|m| m.name).collect(),
            Err(_) => vec![],
        }
    }
}

fn build_prompt(messages: &[Value]) -> (Option<String>, String) {
    let mut system_prompt: Option<String> = None;
    let mut parts: Vec<String> = Vec::new();

    for msg in messages {
        let role = msg["role"].as_str().unwrap_or("user");
        let content = msg["content"].as_str().unwrap_or("");

        match role {
            "system" => {
                if system_prompt.is_none() {
                    system_prompt = Some(content.to_string());
                } else {
                    let existing = system_prompt.take().unwrap();
                    system_prompt = Some(format!("{}\n{}", existing, content));
                }
            }
            "user" => parts.push(format!("User: {}", content)),
            "assistant" => parts.push(format!("Assistant: {}", content)),
            _ => parts.push(format!("{}: {}", role, content)),
        }
    }

    (system_prompt, parts.join("\n"))
}
