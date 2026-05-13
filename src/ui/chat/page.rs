use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use gtk4::prelude::*;
use gtk4::{gdk, glib};
use regex::Regex;

use crate::ai::client::AIClient;
use crate::chat::storage::ChatStorage;
use crate::i18n::manager::LanguageManager;
use crate::prompt::manager::PromptManager;
use crate::status::manager::StatusManager;
use crate::tools::manager::ToolManager;
use crate::ui::utils::{markdown_to_pango, parse_markdown_segments, SegmentType};
use crate::ui::components::{
    ArtifactCard, CodeBlock, PlanConfirmationCard, SourceCard, TableBlock, WallpaperGrid,
};

const MAX_TURNS: usize = 5;

struct PageState {
    history: Vec<serde_json::Value>,
    chat_data: serde_json::Value,
}

pub struct ChatPage {
    pub widget: gtk4::Box,
    chat_box: gtk4::Box,
    scrolled: gtk4::ScrolledWindow,
    status_overlay_box: gtk4::Box,
    status_label: gtk4::Label,
    status_spinner: gtk4::Spinner,
    entry: gtk4::Entry,
    send_button: gtk4::Button,

    state: Arc<Mutex<PageState>>,
    storage: ChatStorage,
    is_generating: Arc<AtomicBool>,
    cancel_event: Arc<AtomicBool>,

    markdown_cache: Arc<Mutex<HashMap<String, String>>>,
}

impl ChatPage {
    pub fn new(chat_data: &serde_json::Value, storage: ChatStorage, lazy_loading: bool) -> Self {
        let history = chat_data
            .get("history")
            .and_then(|h| h.as_array())
            .cloned()
            .unwrap_or_default();

        let chat_data = chat_data.clone();

        let lang = LanguageManager::instance();
        let lang = lang.lock().unwrap();

        let widget = gtk4::Box::new(gtk4::Orientation::Vertical, 0);

        let overlay = gtk4::Overlay::new();
        overlay.set_vexpand(true);
        widget.append(&overlay);

        let scrolled = gtk4::ScrolledWindow::new();
        overlay.set_child(Some(&scrolled));

        let status_overlay_box = gtk4::Box::new(gtk4::Orientation::Horizontal, 0);
        status_overlay_box.set_halign(gtk4::Align::Start);
        status_overlay_box.set_valign(gtk4::Align::End);
        status_overlay_box.set_margin_start(20);
        status_overlay_box.set_margin_bottom(20);
        status_overlay_box.set_visible(false);
        status_overlay_box.add_css_class("floating-status-box");

        let status_spinner = gtk4::Spinner::new();
        status_overlay_box.append(&status_spinner);

        let status_label = gtk4::Label::new(None);
        status_label.set_margin_start(10);
        status_label.add_css_class("dim-label");
        status_overlay_box.append(&status_label);

        overlay.add_overlay(&status_overlay_box);

        let chat_box = gtk4::Box::new(gtk4::Orientation::Vertical, 6);
        chat_box.set_margin_top(12);
        chat_box.set_margin_bottom(80);
        chat_box.set_margin_start(12);
        chat_box.set_margin_end(12);
        chat_box.add_css_class("chat-box");
        scrolled.set_child(Some(&chat_box));

        let input_box = gtk4::Box::new(gtk4::Orientation::Horizontal, 10);
        input_box.set_margin_start(12);
        input_box.set_margin_end(12);
        input_box.set_margin_bottom(12);
        input_box.set_margin_top(6);

        let entry = gtk4::Entry::new();
        entry.set_hexpand(true);
        entry.set_placeholder_text(Some(&lang.get("chat.placeholder")));
        input_box.append(&entry);

        let send_button = gtk4::Button::builder()
            .icon_name("mail-send-symbolic")
            .tooltip_text(lang.get("chat.send_tooltip"))
            .css_classes(["suggested-action"])
            .build();
        input_box.append(&send_button);

        widget.append(&input_box);

        let state = Arc::new(Mutex::new(PageState {
            history,
            chat_data,
        }));

        let is_generating = Arc::new(AtomicBool::new(false));
        let cancel_event = Arc::new(AtomicBool::new(false));
        let markdown_cache = Arc::new(Mutex::new(HashMap::new()));

        let page = ChatPage {
            widget,
            chat_box,
            scrolled,
            status_overlay_box,
            status_label,
            status_spinner,
            entry: entry.clone(),
            send_button: send_button.clone(),
            state: state.clone(),
            storage: storage.clone(),
            is_generating: is_generating.clone(),
            cancel_event: cancel_event.clone(),
            markdown_cache: markdown_cache.clone(),
        };

        // Wire up callbacks - use Rc<dyn Fn()> to share the send logic
        let on_send: std::rc::Rc<dyn Fn()> = {
            let entry = entry.clone();
            let send_button = send_button.clone();
            let is_generating = is_generating.clone();
            let cancel_event = cancel_event.clone();
            let chat_box = chat_box.clone();
            let status_label = status_label.clone();
            let status_spinner = status_spinner.clone();
            let status_overlay_box = status_overlay_box.clone();
            let scrolled = scrolled.clone();
            let state = state.clone();
            let storage = storage.clone();

            std::rc::Rc::new(move || {
                if is_generating.load(Ordering::SeqCst) {
                    cancel_event.store(true, Ordering::SeqCst);
                    send_button.set_sensitive(false);
                    return;
                }

                let text = entry.text().trim().to_string();
                if text.is_empty() {
                    return;
                }

                entry.set_sensitive(false);
                entry.set_text("");

                is_generating.store(true, Ordering::SeqCst);
                cancel_event.store(false, Ordering::SeqCst);

                let lang = LanguageManager::instance();
                let lang = lang.lock().unwrap();
                send_button.set_icon_name("process-stop-symbolic");
                send_button.set_tooltip_text(Some(&lang.get("chat.stop_tooltip")));
                drop(lang);

                // Add user message to state
                {
                    let mut state = state.lock().unwrap();
                    state.history.push(serde_json::json!({
                        "role": "user",
                        "content": text.clone(),
                    }));

                    // Auto-title
                    let current_title = state.chat_data["title"].as_str().unwrap_or("");
                    let lang = LanguageManager::instance();
                    let lang_inner = lang.lock().unwrap();
                    let new_chat_str = lang_inner.get("window.new_chat");
                    if current_title.is_empty()
                        || current_title == "New Chat"
                        || current_title == "New chat"
                        || current_title == new_chat_str
                    {
                        let new_title = if text.len() > 30 {
                            format!("{}...", &text[..30])
                        } else {
                            text.clone()
                        };
                        state.chat_data["title"] = serde_json::Value::String(new_title);
                    }
                }

                // Save
                {
                    let state = state.lock().unwrap();
                    let mut data = state.chat_data.clone();
                    data["history"] = serde_json::Value::Array(state.history.clone());
                    storage.save_chat(&data);
                }

                // Render user bubble
                let parsed = markdown_to_pango(&text);
                ChatPage::render_ui_bubble(&chat_box, "user", &parsed, &text, None, true);

                // Spawn AI interaction
                let chat_box = chat_box.clone();
                let status_label = status_label.clone();
                let status_spinner = status_spinner.clone();
                let status_overlay_box = status_overlay_box.clone();
                let scrolled = scrolled.clone();
                let send_button = send_button.clone();
                let entry = entry.clone();
                let state = state.clone();
                let storage = storage.clone();
                let cancel_event = cancel_event.clone();
                let is_generating = is_generating.clone();

                glib::spawn_future_local(async move {
                    let result = ChatPage::run_ai_async(
                        &text,
                        &state,
                        &storage,
                        &chat_box,
                        &status_label,
                        &status_spinner,
                        &status_overlay_box,
                        &scrolled,
                        &cancel_event,
                    )
                    .await;

                    // Update history from state
                    if let Ok(ref final_text) = result {
                        let state = state.lock().unwrap();
                        let chat_id = state.chat_data["id"].as_str().unwrap_or("");
                        storage.add_message(chat_id, "assistant", final_text, None);
                    }

                    // Re-enable UI
                    status_spinner.stop();
                    status_overlay_box.set_visible(false);
                    send_button.set_icon_name("mail-send-symbolic");

                    let lang = LanguageManager::instance();
                    let lang = lang.lock().unwrap();
                    send_button.set_tooltip_text(Some(&lang.get("chat.send_tooltip")));
                    drop(lang);

                    send_button.set_sensitive(true);
                    entry.set_sensitive(true);
                    entry.grab_focus();

                    is_generating.store(false, Ordering::SeqCst);
                });
            }) as std::rc::Rc<dyn Fn()>
        };

        // Connect callbacks
        let on_send2 = std::rc::Rc::clone(&on_send);
        entry.connect_activate(move |_| on_send2());
        send_button.connect_clicked(move |_| on_send());

        // Subscribe to status updates
        let chat_id = state.lock().unwrap().chat_data["id"]
            .as_str()
            .unwrap_or("")
            .to_string();
        let status_label = status_label.clone();
        let status_spinner = status_spinner.clone();
        let status_overlay_box = status_overlay_box.clone();
        StatusManager::global().register_callback(
            move |project_id: String, message: String| {
                if project_id == chat_id {
                    status_label.set_text(&message);
                    status_spinner.start();
                    status_overlay_box.set_visible(true);
                }
            },
        );

        // Load history on idle (unless lazy loading)
        if !lazy_loading {
            let chat_box = chat_box.clone();
            let state = state.clone();
            let markdown_cache = markdown_cache.clone();
            glib::idle_add_once(move || {
                ChatPage::load_history_into_ui(&state, &chat_box, &markdown_cache);
            });
        }

        page
    }

    fn load_history_into_ui(
        state: &Arc<Mutex<PageState>>,
        chat_box: &gtk4::Box,
        markdown_cache: &Arc<Mutex<HashMap<String, String>>>,
    ) {
        let state = state.lock().unwrap();
        let total = state.history.len();
        let start = if total > 100 { total - 100 } else { 0 };

        for i in start..total {
            let msg = &state.history[i];
            let role = msg["role"].as_str().unwrap_or("user");
            let content = msg["content"].as_str().unwrap_or("");

            if let Some(meta) = msg.get("metadata") {
                if meta.get("hidden").and_then(|v| v.as_bool()).unwrap_or(false) {
                    continue;
                }
            }

            let mut cache = markdown_cache.lock().unwrap();
            if !cache.contains_key(content) {
                let parsed = markdown_to_pango(content);
                cache.insert(content.to_string(), parsed);
            }
            let parsed = cache.get(content).cloned().unwrap_or_default();
            drop(cache);

            let meta = msg.get("metadata").cloned();
            Self::render_ui_bubble(chat_box, role, &parsed, content, meta.as_ref(), false);

            if let Some(ref meta) = meta {
                if let Some(sources) = meta.get("sources").and_then(|s| s.as_array()) {
                    Self::render_ui_sources(chat_box, sources);
                }
                if let Some(artifacts) = meta.get("artifacts").and_then(|a| a.as_array()) {
                    Self::render_ui_artifacts(chat_box, artifacts);
                }
            }
        }
        drop(state);

        // Scroll to bottom
        if let Some(adj) = chat_box.parent().and_then(|p| {
            p.downcast::<gtk4::ScrolledWindow>().ok()
        }).and_then(|sw| sw.vadjustment()) {
            let upper = adj.upper();
            let page_size = adj.page_size();
            adj.set_value(upper - page_size);
        }
    }

    fn render_ui_bubble(
        chat_box: &gtk4::Box,
        role: &str,
        parsed_text: &str,
        _original_text: &str,
        _metadata: Option<&serde_json::Value>,
        _scroll: bool,
    ) {
        let msg_row = gtk4::Box::new(gtk4::Orientation::Horizontal, 0);
        msg_row.add_css_class("message-row");
        msg_row.set_halign(if role == "user" {
            gtk4::Align::End
        } else {
            gtk4::Align::Start
        });

        let bubble = gtk4::Box::new(gtk4::Orientation::Vertical, 0);
        bubble.add_css_class("message-bubble");
        bubble.add_css_class(if role == "user" {
            "user-message"
        } else {
            "ai-message"
        });

        let label = gtk4::Label::new(None);
        label.set_use_markup(true);
        label.set_markup(parsed_text);
        label.set_wrap(true);
        label.set_max_width_chars(50);
        label.set_xalign(0.0);
        label.set_selectable(true);
        bubble.append(&label);

        msg_row.append(&bubble);
        chat_box.append(&msg_row);
    }

    pub fn add_message(&self, role: &str, content: &str, meta: Option<serde_json::Value>, save: bool) {
        let mut content = content.to_string();
        if content.contains("<tool_call>") {
            if let Some(idx) = content.find("<tool_call>") {
                content = content[..idx].trim().to_string();
            }
        }

        let mut state = self.state.lock().unwrap();

        let mut msg = serde_json::json!({"role": role, "content": content});
        if let Some(ref m) = meta {
            msg["metadata"] = m.clone();
        }
        state.history.push(msg.clone());

        if save {
            if let Some(history) = state
                .chat_data
                .get_mut("history")
                .and_then(|h| h.as_array_mut())
            {
                history.push(msg);
            }
        }

        // Auto-title from first user message
        if role == "user" {
            let current_title = state.chat_data["title"].as_str().unwrap_or("");
            let lang = LanguageManager::instance();
            let lang = lang.lock().unwrap();
            let new_chat_str = lang.get("window.new_chat");
            if current_title.is_empty()
                || current_title == "New Chat"
                || current_title == "New chat"
                || current_title == new_chat_str
            {
                let new_title = if content.len() > 30 {
                    format!("{}...", &content[..30])
                } else {
                    content.clone()
                };
                state.chat_data["title"] = serde_json::Value::String(new_title);
            }
        }

        drop(state);

        if save {
            self.save_chat_data();
        }

        let parsed = markdown_to_pango(&content);
        Self::render_ui_bubble(&self.chat_box, role, &parsed, &content, meta.as_ref(), true);
    }

    pub fn add_user_message(&self, text: &str) {
        self.add_message("user", text, None, true);
    }

    pub fn show_status(&self, message: &str) {
        self.status_label.set_text(message);
        self.status_spinner.start();
        self.status_overlay_box.set_visible(true);
    }

    pub fn hide_status(&self) {
        self.status_spinner.stop();
        self.status_overlay_box.set_visible(false);
    }

    pub fn add_sources(&self, sources: &[serde_json::Value]) {
        Self::render_ui_sources(&self.chat_box, sources);
    }

    fn render_ui_sources(chat_box: &gtk4::Box, sources: &[serde_json::Value]) {
        let main_box = gtk4::Box::new(gtk4::Orientation::Vertical, 6);
        main_box.set_margin_top(12);
        main_box.set_margin_bottom(12);
        main_box.set_hexpand(true);
        main_box.add_css_class("sources-container");

        let lang = LanguageManager::instance();
        let lang = lang.lock().unwrap();
        let header = gtk4::Label::new(Some(&lang.get("chat.sources_header")));
        header.add_css_class("dim-label");
        header.set_halign(gtk4::Align::Start);
        header.set_margin_start(4);
        main_box.append(&header);

        let listbox = gtk4::ListBox::new();
        listbox.set_selection_mode(gtk4::SelectionMode::None);
        listbox.add_css_class("sources-listbox");

        for source in sources {
            let card = SourceCard::new(
                source.get("title").and_then(|v| v.as_str()).unwrap_or("Untitled"),
                source.get("url").and_then(|v| v.as_str()).unwrap_or(""),
                source.get("snippet").and_then(|v| v.as_str()).unwrap_or(""),
                source.get("image_url").and_then(|v| v.as_str()),
                source.get("favicon_url").and_then(|v| v.as_str()),
            );
            listbox.append(&card.widget);
        }

        main_box.append(&listbox);

        let msg_row = gtk4::Box::new(gtk4::Orientation::Horizontal, 0);
        msg_row.set_halign(gtk4::Align::Fill);
        msg_row.set_margin_start(40);
        msg_row.set_margin_end(40);
        msg_row.append(&main_box);
        chat_box.append(&msg_row);
    }

    pub fn add_artifacts(&self, artifacts: &[serde_json::Value]) {
        Self::render_ui_artifacts(&self.chat_box, artifacts);
    }

    fn render_ui_artifacts(chat_box: &gtk4::Box, artifacts: &[serde_json::Value]) {
        let plan_artifact = artifacts
            .iter()
            .find(|a| a.get("type").and_then(|v| v.as_str()) == Some("implementation_plan"));

        if let Some(plan) = plan_artifact {
            let card = PlanConfirmationCard::new(plan, Box::new(|| {}));
            let msg_row = gtk4::Box::new(gtk4::Orientation::Horizontal, 0);
            msg_row.set_halign(gtk4::Align::Start);
            msg_row.set_margin_start(40);
            msg_row.set_margin_top(16);
            msg_row.append(&card.widget);
            chat_box.append(&msg_row);

            let remaining: Vec<&serde_json::Value> = artifacts
                .iter()
                .filter(|a| a.get("type").and_then(|v| v.as_str()) != Some("implementation_plan"))
                .collect();
            if remaining.is_empty() {
                return;
            }
            Self::render_artifact_list(chat_box, &remaining);
            return;
        }

        let refs: Vec<&serde_json::Value> = artifacts.iter().collect();
        Self::render_artifact_list(chat_box, &refs);
    }

    fn render_artifact_list(chat_box: &gtk4::Box, artifacts: &[&serde_json::Value]) {
        let artifacts_box = gtk4::Box::new(gtk4::Orientation::Vertical, 6);
        artifacts_box.set_margin_top(12);
        artifacts_box.set_margin_bottom(12);

        for art in artifacts {
            let card = ArtifactCard::new(
                art.get("filename")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Unknown"),
                art.get("path").and_then(|v| v.as_str()).unwrap_or(""),
                art.get("language").and_then(|v| v.as_str()).unwrap_or(""),
            );
            artifacts_box.append(&card.widget);
        }

        let msg_row = gtk4::Box::new(gtk4::Orientation::Horizontal, 0);
        msg_row.set_halign(gtk4::Align::Start);
        msg_row.set_margin_start(40);
        msg_row.set_margin_top(16);
        msg_row.append(&artifacts_box);
        chat_box.append(&msg_row);
    }

    async fn run_ai_async(
        user_text: &str,
        state: &Arc<Mutex<PageState>>,
        storage: &ChatStorage,
        chat_box: &gtk4::Box,
        status_label: &gtk4::Label,
        status_spinner: &gtk4::Spinner,
        status_overlay_box: &gtk4::Box,
        scrolled: &gtk4::ScrolledWindow,
        cancel_event: &Arc<AtomicBool>,
    ) -> Result<String, String> {
        let client = AIClient::new();
        let tm = ToolManager::instance();
        let tools_def = {
            let tm = tm.lock().unwrap();
            tm.get_ollama_tools_definitions()
        };

        // Build system prompt
        let (system_prompt, messages) = {
            let state = state.lock().unwrap();
            let prompt_mgr = PromptManager::instance();
            let prompt_mgr = prompt_mgr.lock().unwrap();
            let system_prompt = prompt_mgr.get("system_prompt_base");

            let mut msgs: Vec<serde_json::Value> = Vec::new();
            msgs.push(serde_json::json!({"role": "system", "content": system_prompt}));
            msgs.extend_from_slice(&state.history);
            msgs.push(serde_json::json!({"role": "user", "content": user_text}));

            (system_prompt, msgs)
        };

        let mut messages = messages;
        let mut visible_text_buffer = String::new();
        let mut all_sources: Vec<serde_json::Value> = Vec::new();
        let mut all_artifacts: Vec<serde_json::Value> = Vec::new();

        let mut turn = 0;

        while turn < MAX_TURNS {
            if cancel_event.load(Ordering::SeqCst) {
                visible_text_buffer.push_str(" [stopped by user]");
                break;
            }
            turn += 1;

            // Show spinner
            glib::MainContext::default().invoke({
                let status_label = status_label.clone();
                let status_spinner = status_spinner.clone();
                let status_overlay_box = status_overlay_box.clone();
                move || {
                    status_label.set_text("");
                    status_spinner.start();
                    status_overlay_box.set_visible(true);
                    glib::ControlFlow::Break
                }
            });

            let response = client
                .generate_response(&messages, Some(&tools_def))
                .await;

            let content = response["message"]["content"]
                .as_str()
                .unwrap_or("")
                .to_string();

            if content.is_empty() {
                break;
            }

            let (clean_content, parsed_calls) =
                Self::parse_tool_calls(&content);

            visible_text_buffer.push_str(&clean_content);

            // Update UI with current text
            if !visible_text_buffer.is_empty() {
                let display = visible_text_buffer.clone();
                let parsed = markdown_to_pango(&display);
                let chat_box = chat_box.clone();
                let scrolled = scrolled.clone();
                let status_overlay_box = status_overlay_box.clone();

                glib::MainContext::default().invoke(move || {
                    status_overlay_box.set_visible(false);

                    let last_child = chat_box.last_child();
                    if let Some(last) = last_child {
                        let first = last.first_child();
                        if let Some(bubble) = first {
                            if bubble.has_css_class("message-bubble") {
                                while let Some(child) = bubble.first_child() {
                                    bubble.remove(&child);
                                }
                                let label = gtk4::Label::new(None);
                                label.set_use_markup(true);
                                label.set_markup(&parsed);
                                label.set_wrap(true);
                                label.set_max_width_chars(50);
                                label.set_xalign(0.0);
                                label.set_selectable(true);
                                bubble.append(&label);
                            }
                        }
                    }

                    if let Some(adj) = scrolled.vadjustment() {
                        let upper = adj.upper();
                        let page_size = adj.page_size();
                        adj.set_value(upper - page_size);
                    }

                    glib::ControlFlow::Break
                });
            }

            let mut pending_tool_calls: Vec<serde_json::Value> = Vec::new();
            let tool_calls = response["message"]["tool_calls"].clone();
            if let Some(arr) = tool_calls.as_array() {
                pending_tool_calls.extend(arr.clone());
            }

            for call in &parsed_calls {
                pending_tool_calls.push(call.clone());
            }

            if pending_tool_calls.is_empty() {
                if visible_text_buffer.contains("[PLAN]") {
                    if let Some(caps) = Regex::new(r"(?s)\[PLAN\](.*?)(?:\[/PLAN\]|$)")
                        .unwrap()
                        .captures(&visible_text_buffer)
                    {
                        let _plan_content = caps.get(1).map(|m| m.as_str().trim()).unwrap_or("");
                    }
                }
                break;
            }

            // Show "Generating..." while executing tools
            glib::MainContext::default().invoke({
                let status_label = status_label.clone();
                let status_overlay_box = status_overlay_box.clone();
                move || {
                    status_label.set_text("Generating...");
                    status_overlay_box.set_visible(true);
                    glib::ControlFlow::Break
                }
            });

            let assistant_msg = serde_json::json!({
                "role": "assistant",
                "content": clean_content,
                "tool_calls": pending_tool_calls,
            });
            messages.push(assistant_msg.clone());

            {
                let mut state = state.lock().unwrap();
                state.history.push(serde_json::json!({
                    "role": "assistant",
                    "content": clean_content,
                }));

                let chat_id = state.chat_data["id"].as_str().unwrap_or("").to_string();
                drop(state);
                storage.add_message(&chat_id, "assistant", &clean_content, None);
            }

            let tm = tm.lock().unwrap();
            for tool_call in &pending_tool_calls {
                let fname = tool_call["function"]["name"]
                    .as_str()
                    .unwrap_or("");
                let args = tool_call["function"]["arguments"].clone();

                let result = tm.execute_tool(fname, &args, None);

                match result {
                    Ok(result_val) => {
                        let result_str = result_val.to_string();

                        if let Ok(re) = Regex::new(r"(?s)\[SOURCES\](.*?)\[/SOURCES\]") {
                            for caps in re.captures_iter(&result_str) {
                                if let Some(json_str) = caps.get(1) {
                                    if let Ok(sources) = serde_json::from_str::<
                                        Vec<serde_json::Value>,
                                    >(json_str.as_str().trim())
                                    {
                                        all_sources.extend(sources.clone());
                                        let chat_box = chat_box.clone();
                                        glib::MainContext::default().invoke(move || {
                                            Self::render_ui_sources(&chat_box, &sources);
                                            glib::ControlFlow::Break
                                        });
                                    }
                                }
                            }
                        }

                        if let Ok(re) = Regex::new(r"(?s)\[ARTIFACT\](.*?)\[/ARTIFACT\]") {
                            for caps in re.captures_iter(&result_str) {
                                if let Some(json_str) = caps.get(1) {
                                    if let Ok(artifact) =
                                        serde_json::from_str::<serde_json::Value>(
                                            json_str.as_str().trim(),
                                        )
                                    {
                                        all_artifacts.push(artifact);
                                    }
                                }
                            }
                        }

                        messages.push(serde_json::json!({
                            "role": "tool",
                            "content": result_str,
                            "name": fname,
                        }));
                    }
                    Err(e) => {
                        messages.push(serde_json::json!({
                            "role": "tool",
                            "content": format!("Error: {e}"),
                            "name": fname,
                        }));
                    }
                }
            }
            drop(tm);

            if all_artifacts.iter().any(|a| {
                a.get("type").and_then(|v| v.as_str())
                    == Some("implementation_plan")
            }) {
                break;
            }
        }

        // Update state with final content
        let final_text = visible_text_buffer.trim().to_string();
        {
            let mut state = state.lock().unwrap();
            let mut meta = serde_json::json!({});
            if !all_sources.is_empty() {
                meta["sources"] = serde_json::Value::Array(all_sources.clone());
            }
            if !all_artifacts.is_empty() {
                meta["artifacts"] = serde_json::Value::Array(all_artifacts.clone());
            }

            state.history.push(serde_json::json!({
                "role": "assistant",
                "content": final_text.clone(),
                "metadata": meta,
            }));
        }

        // Schedule rich content upgrade
        if !final_text.is_empty() {
            let display = final_text.clone();
            let chat_box = chat_box.clone();
            glib::timeout_add_local(std::time::Duration::from_millis(200), move || {
                if let Some(last) = chat_box.last_child() {
                    if let Some(bubble) = last.first_child() {
                        if bubble.has_css_class("message-bubble") {
                            while let Some(child) = bubble.first_child() {
                                bubble.remove(&child);
                            }
                            bubble.add_css_class("rich-content");

                            let segments = parse_markdown_segments(&display);
                            for seg in segments {
                                match seg.seg_type {
                                    SegmentType::Code => {
                                        let lang = seg.lang.as_deref().unwrap_or("text");
                                        let block = CodeBlock::new(lang, &seg.content);
                                        bubble.append(&block.widget);
                                    }
                                    SegmentType::Table => {
                                        let table = TableBlock::new(&seg.content);
                                        bubble.append(&table.widget);
                                    }
                                    SegmentType::WallpaperGrid => {
                                        if let Ok(images) =
                                            serde_json::from_str::<serde_json::Value>(
                                                &seg.content,
                                            )
                                        {
                                            let grid = WallpaperGrid::new(images, None);
                                            bubble.append(&grid.widget);
                                        }
                                    }
                                    SegmentType::Image => {
                                        let img_box = gtk4::Box::new(
                                            gtk4::Orientation::Vertical,
                                            6,
                                        );
                                        img_box.set_margin_top(10);
                                        img_box.set_margin_bottom(10);
                                        img_box.set_size_request(300, -1);
                                        let picture = gtk4::Picture::new();
                                        picture.set_content_fit(gtk4::ContentFit::Cover);
                                        picture.set_can_shrink(true);
                                        img_box.append(&picture);
                                        if let Some(ref alt) = seg.alt {
                                            let caption = gtk4::Label::new(Some(alt));
                                            caption.add_css_class("dim-label");
                                            img_box.append(&caption);
                                        }
                                        bubble.append(&img_box);
                                    }
                                    SegmentType::Text => {
                                        if seg.content.trim().is_empty() {
                                            continue;
                                        }
                                        let label = gtk4::Label::new(None);
                                        label.set_use_markup(true);
                                        label.set_markup(&markdown_to_pango(
                                            &seg.content,
                                        ));
                                        label.set_wrap(true);
                                        label.set_max_width_chars(50);
                                        label.set_xalign(0.0);
                                        label.set_selectable(true);
                                        bubble.append(&label);
                                    }
                                }
                            }
                        }
                    }
                }
                glib::ControlFlow::Break
            });
        }

        // Render sources and artifacts in UI
        if !all_sources.is_empty() {
            let chat_box = chat_box.clone();
            let sources = all_sources.clone();
            glib::MainContext::default().invoke(move || {
                Self::render_ui_sources(&chat_box, &sources);
                glib::ControlFlow::Break
            });
        }

        if !all_artifacts.is_empty() {
            let chat_box = chat_box.clone();
            let artifacts = all_artifacts.clone();
            glib::MainContext::default().invoke(move || {
                Self::render_ui_artifacts(&chat_box, &artifacts);
                glib::ControlFlow::Break
            });
        }

        Ok(final_text)
    }

    fn parse_tool_calls(content: &str) -> (String, Vec<serde_json::Value>) {
        static TOOL_CALL_RE: std::sync::Lazy<Regex> = std::sync::Lazy::new(|| {
            Regex::new(r"(?s)<tool_call>\s*(.*?)\s*</tool_call>").unwrap()
        });

        let mut parsed_calls: Vec<serde_json::Value> = Vec::new();
        let clean_content = TOOL_CALL_RE
            .replace_all(content, |caps: &regex::Captures| {
                let inner = caps.get(1).map(|m| m.as_str()).unwrap_or("");
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(inner) {
                    parsed_calls.push(val);
                } else if let Some(name_cap) = Regex::new(r#""name"\s*:\s*"([^"]+)""#).unwrap().captures(inner) {
                    let name = name_cap[1].to_string();
                    if let Some(args_cap) = Regex::new(r#""arguments"\s*:\s*(\{[^}]+\})"#).unwrap().captures(inner) {
                        if let Ok(args) = serde_json::from_str::<serde_json::Value>(&args_cap[1]) {
                            parsed_calls.push(serde_json::json!({
                                "function": {
                                    "name": name,
                                    "arguments": args,
                                }
                            }));
                        }
                    }
                }
                ""
            })
            .to_string();

        (clean_content, parsed_calls)
    }

    fn save_chat_data(&self) {
        let state = self.state.lock().unwrap();
        let mut data = state.chat_data.clone();
        data["history"] = serde_json::Value::Array(state.history.clone());
        self.storage.save_chat(&data);
    }
}
