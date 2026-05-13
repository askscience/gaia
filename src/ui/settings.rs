use gtk4::prelude::*;
use gtk4::{glib};
use libadwaita::prelude::*;
use libadwaita as adw;

use crate::config::ConfigManager;
use crate::network::proxy::apply_proxy_settings;
use crate::i18n::LANG;

pub struct SettingsWindow {
    window: adw::PreferencesWindow,
}

impl SettingsWindow {
    pub fn new(parent: &impl gtk4::prelude::IsA<gtk4::Window>) -> Self {
        let window = adw::PreferencesWindow::builder()
            .transient_for(parent)
            .title("Settings")
            .build();

        let lang = LANG.lock().unwrap();

        // ── General Page ──
        let general_page = adw::PreferencesPage::builder()
            .title(lang.get("settings.general"))
            .build();

        let gen_group = adw::PreferencesGroup::builder()
            .title("General")
            .build();

        let lang_row = adw::ComboRow::new();
        lang_row.set_title(&lang.get("settings.language"));
        let lang_model = gtk4::StringList::new(&["English", "Español", "Français", "Deutsch", "Italiano"]);
        lang_row.set_model(Some(&lang_model));
        let config_lang = ConfigManager::global().get("app_language");
        if config_lang == "es" { lang_row.set_selected(1); }
        else if config_lang == "fr" { lang_row.set_selected(2); }
        else if config_lang == "de" { lang_row.set_selected(3); }
        else if config_lang == "it" { lang_row.set_selected(4); }
        else { lang_row.set_selected(0); }
        lang_row.connect_selected_notify(|row| {
            let langs = ["en", "es", "fr", "de", "it"];
            let idx = row.selected() as usize;
            if idx < langs.len() {
                ConfigManager::global().set_str("app_language", langs[idx]);
            }
        });
        gen_group.add(&lang_row);

        let ai_group = adw::PreferencesGroup::builder()
            .title("AI Provider")
            .build();

        let provider_row = adw::ComboRow::new();
        provider_row.set_title(&lang.get("settings.ai_provider"));
        let providers = gtk4::StringList::new(&["Ollama", "OpenAI", "Gemini", "Anthropic", "Mistral", "Z.ai"]);
        provider_row.set_model(Some(&providers));
        let current_provider = ConfigManager::global().get("provider");
        if current_provider == "openai" { provider_row.set_selected(1); }
        else if current_provider == "gemini" { provider_row.set_selected(2); }
        else if current_provider == "anthropic" { provider_row.set_selected(3); }
        else if current_provider == "mistral" { provider_row.set_selected(4); }
        else if current_provider == "zai" { provider_row.set_selected(5); }
        else { provider_row.set_selected(0); }

        let api_key_row = adw::PasswordEntryRow::new();
        api_key_row.set_title(&lang.get("settings.api_key"));
        let saved_key = ConfigManager::global().get("api_key");
        api_key_row.set_text(&saved_key);

        let model_row = adw::ComboRow::new();
        model_row.set_title(&lang.get("settings.model"));
        let default_models = gtk4::StringList::new(&["granite4:latest", "llama3.2:latest"]);
        model_row.set_model(Some(&default_models));

        provider_row.connect_selected_notify({
            let api_key_row = api_key_row.clone();
            let model_row = model_row.clone();
            move |row| {
                let providers = ["ollama", "openai", "gemini", "anthropic", "mistral", "zai"];
                let idx = row.selected() as usize;
                if idx < providers.len() {
                    let provider = providers[idx];
                    ConfigManager::global().set_str("provider", provider);
                    api_key_row.set_visible(idx != 0);
                }
                model_row.set_selected(0);
            }
        });

        api_key_row.connect_changed(|row| {
            let provider = ConfigManager::global().get("provider");
            let key_name = format!("{}_api_key", provider);
            ConfigManager::global().set_str(&key_name, &row.text());
            ConfigManager::global().set_str("api_key", &row.text());
        });

        model_row.connect_selected_notify(|row| {
            let models = ["granite4:latest", "llama3.2:latest"];
            let idx = row.selected() as usize;
            if idx < models.len() {
                ConfigManager::global().set_str("model", models[idx]);
            }
        });

        ai_group.add(&provider_row);
        ai_group.add(&api_key_row);
        ai_group.add(&model_row);

        let net_group = adw::PreferencesGroup::builder()
            .title("Network")
            .build();

        let proxy_row = adw::SwitchRow::new();
        proxy_row.set_title("Enable Proxy");
        proxy_row.set_active(ConfigManager::global().get_bool("proxy_enabled", false));
        proxy_row.connect_active_notify(|row| {
            ConfigManager::global().set_bool("proxy_enabled", row.is_active());
            apply_proxy_settings();
        });
        net_group.add(&proxy_row);

        let proxy_url_row = adw::EntryRow::new();
        proxy_url_row.set_title("Proxy URL");
        proxy_url_row.set_text(&ConfigManager::global().get("proxy_url"));
        proxy_url_row.connect_changed(|row| {
            ConfigManager::global().set_str("proxy_url", &row.text());
        });
        net_group.add(&proxy_url_row);

        general_page.add(&gen_group);
        general_page.add(&ai_group);
        general_page.add(&net_group);
        window.add(&general_page);

        // ── Tools Page ──
        let tools_page = adw::PreferencesPage::builder()
            .title("Tools")
            .build();

        let tools_group = adw::PreferencesGroup::builder()
            .title("Enable/Disable Tools")
            .build();

        let tool_defs: Vec<(&str, &str)> = vec![
            ("web_search", "Web Search"),
            ("web_builder", "Web Builder"),
            ("file_reader", "File Reader"),
            ("file_editor", "File Editor"),
            ("file_list", "File List"),
            ("current_time", "Current Time"),
            ("gnome_background", "GNOME Background"),
            ("gnome_theme", "GNOME Theme"),
            ("gnome_audio", "GNOME Audio"),
            ("gnome_radio", "GNOME Radio"),
            ("gnome_document", "GNOME Document"),
        ];

        for (tool_name, display_name) in &tool_defs {
            let row = adw::SwitchRow::new();
            row.set_title(display_name);
            let is_active = ConfigManager::global()
                .get_json("enabled_tools")
                .unwrap_or(serde_json::json!({}))
                .get(*tool_name)
                .and_then(|v| v.as_bool())
                .unwrap_or(true);
            row.set_active(is_active);

            let tool_name = tool_name.to_string();
            row.connect_active_notify(move |row| {
                let mut map = ConfigManager::global()
                    .get_json("enabled_tools")
                    .unwrap_or(serde_json::json!({}));
                if let Some(obj) = map.as_object_mut() {
                    obj.insert(tool_name.clone(), serde_json::Value::Bool(row.is_active()));
                    ConfigManager::global().set("enabled_tools", map);
                }
            });
            tools_group.add(&row);
        }

        tools_page.add(&tools_group);
        window.add(&tools_page);

        // ── Voice Page ──
        let voice_page = adw::PreferencesPage::builder()
            .title("Voice")
            .build();

        let voice_group = adw::PreferencesGroup::builder()
            .title("Voice Settings")
            .build();

        let voice_row = adw::SwitchRow::new();
        voice_row.set_title("Enable Voice Mode");
        voice_row.set_active(ConfigManager::global().get_bool("voice_mode_enabled", false));
        voice_row.connect_active_notify(|row| {
            ConfigManager::global().set_bool("voice_mode_enabled", row.is_active());
        });
        voice_group.add(&voice_row);

        voice_page.add(&voice_group);
        window.add(&voice_page);

        // ── Deep Research Page ──
        let dr_page = adw::PreferencesPage::builder()
            .title("Deep Research")
            .build();

        let dr_group = adw::PreferencesGroup::builder()
            .title("Research Parameters")
            .build();

        let adjustment = gtk4::Adjustment::new(3.0, 1.0, 20.0, 1.0, 5.0, 0.0);
        let max_loops_row = adw::SpinRow::new(Some(&adjustment), 1.0, 0u32);
        max_loops_row.set_title("Max Loops");
        max_loops_row.set_value(ConfigManager::global().get_int("dr_max_loops", 3) as f64);
        max_loops_row.connect_changed(|row| {
            ConfigManager::global().set_int("dr_max_loops", row.value() as i64);
        });
        dr_group.add(&max_loops_row);

        dr_page.add(&dr_group);
        window.add(&dr_page);

        SettingsWindow { window }
    }

    pub fn present(&self) {
        self.window.present();
    }
}
