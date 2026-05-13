use async_openai::Client;
use async_openai::config::OpenAIConfig;
use async_openai::types::{
    ChatCompletionRequestAssistantMessage, ChatCompletionRequestAssistantMessageContent,
    ChatCompletionRequestMessage, ChatCompletionRequestSystemMessage,
    ChatCompletionRequestSystemMessageContent, ChatCompletionRequestUserMessage,
    ChatCompletionRequestUserMessageContent, CreateChatCompletionRequestArgs,
};
use async_trait::async_trait;
use reqwest::Client as ReqwestClient;
use serde_json::{Value, json};

use crate::ai::base::AiProvider;

pub struct OpenAIProvider {
    http: ReqwestClient,
    api_key: String,
    base_url: String,
    openai_client: Client<OpenAIConfig>,
    model: String,
}

impl OpenAIProvider {
    pub fn new(api_key: String, base_url: Option<String>, model: String) -> Self {
        let base = base_url.unwrap_or_else(|| "https://api.openai.com/v1".to_string());
        let mut config = OpenAIConfig::default().with_api_key(api_key.clone());
        config = config.with_api_base(base.clone());
        let openai_client = Client::with_config(config);
        OpenAIProvider {
            http: ReqwestClient::new(),
            api_key,
            base_url: base,
            openai_client,
            model,
        }
    }
}

#[async_trait]
impl AiProvider for OpenAIProvider {
    async fn generate_response(&self, messages: &[Value], tools: Option<&[Value]>) -> Value {
        match self.generate_via_async_openai(messages, tools).await {
            Ok(value) => value,
            Err(_) => self.generate_via_raw(messages, tools).await,
        }
    }

    async fn list_models(&self) -> Vec<String> {
        match self.openai_client.models().list().await {
            Ok(response) => response.data.into_iter().map(|m| m.id).collect(),
            Err(_) => vec![],
        }
    }
}

impl OpenAIProvider {
    async fn generate_via_async_openai(
        &self,
        messages: &[Value],
        tools: Option<&[Value]>,
    ) -> Result<Value, String> {
        let chat_messages: Vec<ChatCompletionRequestMessage> = messages
            .iter()
            .map(convert_message)
            .collect::<Option<Vec<_>>>()
            .ok_or_else(|| "Failed to convert messages".to_string())?;

        let mut builder = CreateChatCompletionRequestArgs::default();
        builder.model(&self.model);
        builder.messages(chat_messages);

        if let Some(t) = tools {
            if !t.is_empty() {
                return Err("tools require raw request".to_string());
            }
        }

        let request = builder
            .build()
            .map_err(|e| format!("Failed to build request: {}", e))?;

        let response = self
            .openai_client
            .chat()
            .create(request)
            .await
            .map_err(|e| format!("OpenAI API error: {}", e))?;

        serde_json::to_value(response).map_err(|e| format!("Failed to serialize: {}", e))
    }

    async fn generate_via_raw(&self, messages: &[Value], tools: Option<&[Value]>) -> Value {
        let mut body = json!({
            "model": self.model,
            "messages": messages,
        });

        if let Some(t) = tools {
            body["tools"] = t.into();
        }

        let url = format!("{}/chat/completions", self.base_url.trim_end_matches('/'));

        match self
            .http
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.api_key))
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
            Err(e) => json!({"error": format!("HTTP request failed: {}", e)}),
        }
    }
}

fn convert_message(msg: &Value) -> Option<ChatCompletionRequestMessage> {
    let role = msg["role"].as_str()?;
    match role {
        "system" => {
            let content = extract_text_content(&msg["content"])?;
            Some(ChatCompletionRequestMessage::System(
                ChatCompletionRequestSystemMessage {
                    content: ChatCompletionRequestSystemMessageContent::Text(content),
                    name: msg["name"].as_str().map(String::from),
                },
            ))
        }
        "user" => {
            let content = extract_text_content(&msg["content"]).unwrap_or_default();
            Some(ChatCompletionRequestMessage::User(
                ChatCompletionRequestUserMessage {
                    content: ChatCompletionRequestUserMessageContent::Text(content),
                    name: msg["name"].as_str().map(String::from),
                },
            ))
        }
        "assistant" => {
            let content = extract_text_content(&msg["content"]);
            let tool_calls = msg["tool_calls"]
                .as_array()
                .and_then(|tc| serde_json::from_value(json!(tc)).ok());
            Some(ChatCompletionRequestMessage::Assistant(
                ChatCompletionRequestAssistantMessage {
                    content: content.map(ChatCompletionRequestAssistantMessageContent::Text),
                    name: msg["name"].as_str().map(String::from),
                    tool_calls,
                    function_call: None,
                    refusal: None,
                    audio: None,
                },
            ))
        }
        "tool" => Some(serde_json::from_value(msg.clone()).ok()?),
        _ => None,
    }
}

fn extract_text_content(content: &Value) -> Option<String> {
    if let Some(s) = content.as_str() {
        return Some(s.to_string());
    }
    if let Some(arr) = content.as_array() {
        let texts: Vec<&str> = arr.iter().filter_map(|c| c["text"].as_str()).collect();
        if !texts.is_empty() {
            return Some(texts.join(""));
        }
    }
    None
}
