use once_cell::sync::Lazy;
use serde_json::Value;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

const PROMPTS_JSON: &str = include_str!("prompts.json");

pub struct PromptManager {
    prompts: Value,
}

impl PromptManager {
    fn new() -> Self {
        let prompts: Value =
            serde_json::from_str(PROMPTS_JSON).expect("Failed to parse embedded prompts.json");

        PromptManager { prompts }
    }

    pub fn instance() -> Arc<Mutex<PromptManager>> {
        INSTANCE.clone()
    }

    pub fn get(&self, key: &str) -> String {
        let parts: Vec<&str> = key.split('.').collect();
        let mut current = &self.prompts;

        for &part in &parts {
            match current {
                Value::Object(map) => match map.get(part) {
                    Some(v) => current = v,
                    None => return key.to_string(),
                },
                _ => return key.to_string(),
            }
        }

        match current {
            Value::String(s) => s.clone(),
            Value::Array(arr) => arr
                .iter()
                .filter_map(|v| v.as_str())
                .collect::<Vec<&str>>()
                .join("\n"),
            _ => current.as_str().unwrap_or(key).to_string(),
        }
    }

    pub fn get_system_prompt(&self, enabled_tools: &HashMap<String, bool>) -> String {
        let intro = self.get("system_prompt_intro");
        let critical = self.get("critical_instruction");
        let exception = self.get("exception_instruction");
        let header = self.get("guidelines_header");

        let mut guidelines = Vec::new();

        let web_builder = enabled_tools.get("web_builder").copied().unwrap_or(false);
        let file_editor = enabled_tools.get("file_editor").copied().unwrap_or(false);
        let web_search = enabled_tools.get("web_search").copied().unwrap_or(false);
        let calendar = enabled_tools.get("calendar").copied().unwrap_or(false);

        if web_builder {
            guidelines.push(self.get("guidelines.web_builder_enabled"));
        } else {
            guidelines.push(self.get("guidelines.web_builder_disabled"));
        }

        if file_editor {
            let items = self.get("guidelines.file_editor_enabled");
            guidelines.push(items);
        } else {
            guidelines.push(self.get("guidelines.file_editor_disabled"));
        }

        guidelines.push(self.get("guidelines.conciseness"));

        if web_search {
            guidelines.push(self.get("guidelines.web_search_enabled"));
        } else {
            guidelines.push(self.get("guidelines.web_search_disabled"));
        }

        if calendar {
            guidelines.push(self.get("guidelines.calendar_enabled"));
        }

        let joined_guidelines = guidelines.join("\n\n");

        format!("{intro}\n\n{critical}\n\n{exception}\n\n{header}\n{joined_guidelines}")
    }
}

static INSTANCE: Lazy<Arc<Mutex<PromptManager>>> =
    Lazy::new(|| Arc::new(Mutex::new(PromptManager::new())));
