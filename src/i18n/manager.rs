use once_cell::sync::Lazy;
use serde_json::Value;
use std::sync::{Arc, Mutex};

pub struct LanguageManager {
    strings: Value,
    current_lang: String,
}

impl LanguageManager {
    fn new() -> Self {
        let fallback: Value = serde_json::from_str(include_str!("lang_en.json"))
            .expect("Failed to parse embedded lang_en.json");

        let lang = std::env::var("LANG")
            .unwrap_or_default()
            .chars()
            .take(2)
            .collect::<String>()
            .to_lowercase();

        let supported = ["en", "es", "fr", "de", "it"];
        let lang = if supported.contains(&lang.as_str()) {
            lang
        } else {
            "en".to_string()
        };

        let strings = if lang == "en" {
            fallback.clone()
        } else {
            // For non-English, fall back to English strings until
            // language files are added to the project.
            // To add a language, create src/i18n/lang_XX.json and
            // use include_str! above.
            fallback.clone()
        };

        LanguageManager {
            strings,
            current_lang: lang,
        }
    }

    pub fn instance() -> Arc<Mutex<LanguageManager>> {
        LANG.clone()
    }

    pub fn current_language(&self) -> &str {
        &self.current_lang
    }

    pub fn get(&self, key: &str) -> String {
        let parts: Vec<&str> = key.split('.').collect();
        let mut current = &self.strings;

        for &part in &parts {
            match current {
                Value::Object(map) => match map.get(part) {
                    Some(v) => current = v,
                    None => return key.to_string(),
                },
                _ => return key.to_string(),
            }
        }

        current.as_str().unwrap_or(key).to_string()
    }
}

pub static LANG: Lazy<Arc<Mutex<LanguageManager>>> =
    Lazy::new(|| Arc::new(Mutex::new(LanguageManager::new())));
