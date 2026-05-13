use once_cell::sync::Lazy;
use std::collections::HashMap;

pub static PROVIDER_LIMITS: Lazy<HashMap<&str, usize>> = Lazy::new(|| {
    let mut m = HashMap::new();
    m.insert("ollama", 4);
    m.insert("openai", 8);
    m.insert("anthropic", 4);
    m.insert("gemini", 4);
    m.insert("zai", 2);
    m.insert("mistral", 4);
    m
});

pub fn get_limit_for_provider(provider: &str) -> usize {
    PROVIDER_LIMITS.get(provider).copied().unwrap_or(4)
}
