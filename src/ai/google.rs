use async_trait::async_trait;
use reqwest::Client;
use serde_json::{Value, json};
use std::collections::HashMap;

use crate::ai::base::AiProvider;

pub struct GoogleProvider {
    http: Client,
    api_key: String,
    model: String,
}

impl GoogleProvider {
    pub fn new(api_key: String, model: String) -> Self {
        GoogleProvider {
            http: Client::new(),
            api_key,
            model,
        }
    }
}

#[async_trait]
impl AiProvider for GoogleProvider {
    async fn generate_response(&self, messages: &[Value], tools: Option<&[Value]>) -> Value {
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            self.model, self.api_key
        );

        let (system_instruction, contents) = convert_to_gemini_format(messages);

        let mut body = json!({
            "contents": contents,
        });

        if let Some(sys) = system_instruction {
            body["system_instruction"] = sys;
        }

        let mut generation_config = HashMap::new();
        generation_config.insert("maxOutputTokens".to_string(), json!(4096));
        body["generationConfig"] = json!(generation_config);

        if let Some(t) = tools {
            body["tools"] = json!(t);
        }

        match self
            .http
            .post(&url)
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
        {
            Ok(resp) => {
                let status = resp.status();
                let json_val: Value = resp.json().await.unwrap_or_else(
                    |e| json!({"error": format!("Failed to parse response: {}", e)}),
                );
                if status.is_success() {
                    json_val
                } else {
                    json!({"error": json_val.to_string()})
                }
            }
            Err(e) => json!({"error": format!("Gemini API error: {}", e)}),
        }
    }

    async fn list_models(&self) -> Vec<String> {
        vec![self.model.clone()]
    }
}

fn convert_to_gemini_format(messages: &[Value]) -> (Option<Value>, Vec<Value>) {
    let mut system_parts: Vec<Value> = Vec::new();
    let mut contents: Vec<Value> = Vec::new();

    for msg in messages {
        let role = msg["role"].as_str().unwrap_or("user");
        let content = &msg["content"];

        if role == "system" {
            system_parts.push(json!({"text": content}));
        } else {
            let gemini_role = if role == "assistant" { "model" } else { "user" };
            let parts = if content.is_string() {
                vec![json!({"text": content})]
            } else if content.is_array() {
                content
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|c| {
                        if c.is_string() {
                            json!({"text": c})
                        } else {
                            c.clone()
                        }
                    })
                    .collect()
            } else {
                vec![json!({"text": content.to_string()})]
            };

            contents.push(json!({
                "role": gemini_role,
                "parts": parts,
            }));
        }
    }

    let system_instruction = if system_parts.is_empty() {
        None
    } else {
        Some(json!({"parts": system_parts}))
    };

    (system_instruction, contents)
}
