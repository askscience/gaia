use async_trait::async_trait;
use futures::stream::BoxStream;
use serde_json::Value;

#[async_trait]
pub trait AiProvider: Send + Sync {
    async fn generate_response(&self, messages: &[Value], tools: Option<&[Value]>) -> Value;
    async fn list_models(&self) -> Vec<String>;
}

#[async_trait]
pub trait AiStreamer: Send + Sync {
    async fn stream_response(
        &self,
        messages: &[Value],
        tools: Option<&[Value]>,
    ) -> BoxStream<'static, Value>;
}
