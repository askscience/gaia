use serde_json::Value;
use std::rc::Rc;

use gtk4::prelude::*;

use crate::chat::ChatStorage;

pub struct ChatPage {
    pub widget: gtk4::Box,
    pub chat_data: Value,
    pub history: Vec<Value>,
    pub lazy_loading: bool,
    pub _storage: Rc<ChatStorage>,
}

impl ChatPage {
    pub fn new(chat_data: &Value, storage: Rc<ChatStorage>, lazy_loading: bool) -> Self {
        let widget = gtk4::Box::new(gtk4::Orientation::Vertical, 0);
        let history = chat_data
            .get("history")
            .and_then(|h| h.as_array())
            .cloned()
            .unwrap_or_default();

        ChatPage {
            widget,
            chat_data: chat_data.clone(),
            history,
            lazy_loading,
            _storage: storage,
        }
    }

    pub fn restore_artifacts(
        &self,
        _artifacts_panel: &crate::ui::artifacts_panel::ArtifactsPanel,
    ) {
    }

    pub fn _load_history_batch(&self) -> gtk4::glib::ControlFlow {
        gtk4::glib::ControlFlow::Break
    }
}
