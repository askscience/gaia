use chrono::Utc;
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use std::fs;
use std::io;
use std::path::PathBuf;
use std::sync::Mutex;
use uuid::Uuid;

static INSTANCE: Lazy<Mutex<ChatStorage>> = Lazy::new(|| Mutex::new(ChatStorage::new(None)));

#[derive(Clone)]
pub struct ChatStorage {
    storage_dir: PathBuf,
}

impl ChatStorage {
    pub fn global() -> &'static Lazy<Mutex<ChatStorage>> {
        &INSTANCE
    }

    pub fn new(storage_dir: Option<PathBuf>) -> Self {
        let storage_dir = storage_dir.unwrap_or_else(|| {
            dirs::data_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("gaia")
                .join("chats")
        });
        let _ = fs::create_dir_all(&storage_dir);
        ChatStorage { storage_dir }
    }

    pub fn create_chat(&self, title: &str, save: bool) -> serde_json::Value {
        let chat_id = Uuid::new_v4().to_string();
        let now = Utc::now().to_rfc3339();

        let chat = serde_json::json!({
            "id": chat_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "history": [],
        });

        if save {
            self.save_chat(&chat);
        }

        chat
    }

    pub fn save_chat(&self, chat: &serde_json::Value) {
        let mut chat = chat.clone();
        chat["updated_at"] = serde_json::Value::String(Utc::now().to_rfc3339());

        let chat_id = chat["id"].as_str().unwrap_or("unknown");
        let file_path = self.storage_dir.join(format!("{}.json", chat_id));

        if let Ok(json) = serde_json::to_string_pretty(&chat) {
            let _ = fs::write(&file_path, json);
        }
    }

    pub fn load_chat(
        &self,
        chat_id: &str,
        limit_messages: Option<usize>,
    ) -> Option<serde_json::Value> {
        let file_path = self.storage_dir.join(format!("{}.json", chat_id));

        if !file_path.exists() {
            return None;
        }

        let contents = fs::read_to_string(&file_path).ok()?;
        let mut chat: serde_json::Value = serde_json::from_str(&contents).ok()?;

        if let Some(limit) = limit_messages {
            if let Some(history) = chat.get("history").and_then(|h| h.as_array()) {
                if history.len() > limit {
                    let truncated: Vec<_> = history
                        .iter()
                        .skip(history.len() - limit)
                        .cloned()
                        .collect();
                    chat["history"] = serde_json::Value::Array(truncated);
                }
            }
        }

        Some(chat)
    }

    pub fn delete_chat(&self, chat_id: &str) -> bool {
        let file_path = self.storage_dir.join(format!("{}.json", chat_id));

        // Remove associated artifacts directory
        let artifacts_dir = crate::config::get_artifacts_dir().join(chat_id);
        if artifacts_dir.exists() {
            let _ = fs::remove_dir_all(&artifacts_dir);
        }

        if file_path.exists() {
            fs::remove_file(&file_path).is_ok()
        } else {
            false
        }
    }

    pub fn list_chats(&self) -> Vec<serde_json::Value> {
        let mut chats: Vec<serde_json::Value> = Vec::new();

        let entries = match fs::read_dir(&self.storage_dir) {
            Ok(entries) => entries,
            Err(_) => return chats,
        };

        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }

            if let Ok(contents) = fs::read_to_string(&path) {
                if let Ok(chat) = serde_json::from_str::<serde_json::Value>(&contents) {
                    let id = chat.get("id").cloned().unwrap_or_default();
                    let title = chat
                        .get("title")
                        .cloned()
                        .unwrap_or(serde_json::Value::String("New Chat".into()));
                    let created_at = chat.get("created_at").cloned().unwrap_or_default();
                    let updated_at = chat.get("updated_at").cloned().unwrap_or_default();
                    let history_len = chat
                        .get("history")
                        .and_then(|h| h.as_array())
                        .map(|a| a.len())
                        .unwrap_or(0);

                    chats.push(serde_json::json!({
                        "id": id,
                        "title": title,
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "_history_length": history_len,
                    }));
                }
            }
        }

        chats.sort_by(|a, b| {
            let a_time = a.get("updated_at").and_then(|v| v.as_str()).unwrap_or("");
            let b_time = b.get("updated_at").and_then(|v| v.as_str()).unwrap_or("");
            b_time.cmp(a_time)
        });

        chats
    }

    pub fn update_chat_title(&self, chat_id: &str, title: &str) {
        if let Some(mut chat) = self.load_chat(chat_id, None) {
            chat["title"] = serde_json::Value::String(title.to_string());
            self.save_chat(&chat);
        }
    }

    pub fn add_message(
        &self,
        chat_id: &str,
        role: &str,
        content: &str,
        metadata: Option<serde_json::Value>,
    ) {
        let mut chat = match self.load_chat(chat_id, None) {
            Some(c) => c,
            None => return,
        };

        let mut message = serde_json::json!({
            "role": role,
            "content": content,
            "timestamp": Utc::now().to_rfc3339(),
        });

        if let Some(meta) = metadata {
            message["metadata"] = meta;
        }

        if let Some(history) = chat.get_mut("history").and_then(|h| h.as_array_mut()) {
            history.push(message);
        }

        // Auto-generate title from first user message
        if chat.get("title").and_then(|t| t.as_str()) == Some("New Chat") && role == "user" {
            let title = if content.len() > 30 {
                format!("{}...", &content[..30])
            } else {
                content.to_string()
            };
            chat["title"] = serde_json::Value::String(title);
        }

        self.save_chat(&chat);
    }
}
