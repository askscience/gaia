use once_cell::sync::Lazy;
use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::RwLock;

pub struct ConfigManager {
    values: RwLock<HashMap<String, Value>>,
    config_path: Option<PathBuf>,
}

impl ConfigManager {
    pub fn global() -> &'static ConfigManager {
        static INSTANCE: Lazy<ConfigManager> = Lazy::new(|| ConfigManager::load());
        &INSTANCE
    }

    fn load() -> Self {
        let mut values = HashMap::new();

        values.insert("provider".to_string(), Value::String("ollama".into()));
        values.insert(
            "ollama_host".to_string(),
            Value::String("http://localhost:11434".into()),
        );
        values.insert("model".to_string(), Value::String("granite4:latest".into()));
        values.insert("app_language".to_string(), Value::String("auto".into()));
        values.insert("proxy_enabled".to_string(), Value::Bool(false));
        values.insert("proxy_url".to_string(), Value::String(String::new()));
        values.insert(
            "brave_search_api_key".to_string(),
            Value::String(String::new()),
        );
        values.insert("dr_max_loops".to_string(), Value::from(3));
        values.insert("dr_max_results".to_string(), Value::from(3));
        values.insert("dr_outline_steps".to_string(), Value::from(5));
        values.insert("dr_search_breadth".to_string(), Value::from(3));
        values.insert("dr_max_scrape_length".to_string(), Value::from(5000));
        values.insert("dr_max_concurrent_searches".to_string(), Value::from(1));
        values.insert("dr_max_concurrent_llm".to_string(), Value::from(1));
        values.insert("dr_integrate_images".to_string(), Value::Bool(true));
        values.insert("voice_mode_enabled".to_string(), Value::Bool(false));
        values.insert("zai_coding_plan".to_string(), Value::Bool(false));
        values.insert(
            "enabled_tools".to_string(),
            Value::Object(serde_json::Map::new()),
        );
        values.insert(
            "scrape_settings".to_string(),
            serde_json::json!({
                "min_extracted_size": 250,
                "min_output_size": 1,
                "min_extracted_comm_size": 1,
                "extraction_timeout": 0
            }),
        );
        values.insert("web_builder_max_files".to_string(), Value::from(5));
        values.insert(
            "voice_preferences".to_string(),
            Value::Object(serde_json::Map::new()),
        );
        values.insert(
            "unsplash_access_key".to_string(),
            Value::String(String::new()),
        );
        values.insert("pexels_api_key".to_string(), Value::String(String::new()));

        let config_path = config_file_path();

        if let Some(ref path) = config_path {
            if let Ok(content) = fs::read_to_string(path) {
                if let Ok(json) = serde_json::from_str::<Value>(&content) {
                    if let Some(obj) = json.as_object() {
                        for (key, val) in obj {
                            values.insert(key.clone(), val.clone());
                        }
                    }
                }
            }
        }

        ConfigManager {
            values: RwLock::new(values),
            config_path,
        }
    }

    pub fn get(&self, key: &str) -> String {
        self.values
            .read()
            .unwrap()
            .get(key)
            .and_then(|v| v.as_str().map(|s| s.to_string()))
            .unwrap_or_default()
    }

    pub fn get_bool(&self, key: &str, default: bool) -> bool {
        self.values
            .read()
            .unwrap()
            .get(key)
            .and_then(|v| v.as_bool())
            .unwrap_or(default)
    }

    pub fn get_int(&self, key: &str, default: i64) -> i64 {
        self.values
            .read()
            .unwrap()
            .get(key)
            .and_then(|v| v.as_i64())
            .unwrap_or(default)
    }

    pub fn get_json(&self, key: &str) -> Option<Value> {
        self.values.read().unwrap().get(key).cloned()
    }

    pub fn set(&self, key: &str, value: Value) {
        self.values.write().unwrap().insert(key.to_string(), value);
        self.save();
    }

    pub fn set_str(&self, key: &str, value: &str) {
        self.set(key, Value::String(value.to_string()));
    }

    pub fn set_bool(&self, key: &str, value: bool) {
        self.set(key, Value::Bool(value));
    }

    pub fn set_int(&self, key: &str, value: i64) {
        self.set(key, Value::from(value));
    }

    fn save(&self) {
        if let Some(ref path) = self.config_path {
            if let Some(parent) = path.parent() {
                let _ = fs::create_dir_all(parent);
            }
            let map: HashMap<String, Value> = self.values.read().unwrap().clone();
            if let Ok(json) = serde_json::to_string_pretty(&map) {
                let _ = fs::write(path, json);
            }
        }
    }
}

pub fn get_artifacts_dir() -> PathBuf {
    let home = dirs::data_dir().unwrap_or_else(|| PathBuf::from("."));
    let dir = home.join("gaia").join("artifacts");
    let _ = fs::create_dir_all(&dir);
    dir
}

fn config_file_path() -> Option<PathBuf> {
    if let Ok(path) = std::env::var("GAIA_CONFIG") {
        return Some(PathBuf::from(path));
    }
    let config_dir = dirs::config_dir()?;
    Some(config_dir.join("gaia").join("config.json"))
}
