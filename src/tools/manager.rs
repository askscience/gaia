use crate::config::ConfigManager;
use crate::tools::base::Tool;
use crate::tools::current_time::CurrentTimeTool;
use crate::tools::file_editor::FileEditorTool;
use crate::tools::file_list::FileListTool;
use crate::tools::file_reader::FileReaderTool;
use crate::tools::gnome::audio::GnomeAudioControlTool;
use crate::tools::gnome::background::{GnomeSearchBackgroundTool, GnomeSetBackgroundTool};
use crate::tools::gnome::calendar::{
    CalendarAddEventTool, CalendarCreateCalendarTool, CalendarListCalendarsTool,
    CalendarListEventsTool, CalendarRemoveEventTool,
};
use crate::tools::gnome::document::GnomeDocumentTool;
use crate::tools::gnome::opener::GnomeOpenerTool;
use crate::tools::gnome::radio::GnomeRadioTool;
use crate::tools::gnome::theme::GnomeThemeTool;
use crate::tools::web_search::WebSearchTool;
use once_cell::sync::Lazy;
use serde_json::Value;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

pub struct ToolManager {
    tools: HashMap<String, Box<dyn Tool>>,
}

impl ToolManager {
    fn new() -> Self {
        let mut manager = ToolManager {
            tools: HashMap::new(),
        };
        manager.register("web_search", WebSearchTool);
        manager.register("file_reader", FileReaderTool);
        manager.register("file_editor", FileEditorTool);
        manager.register("file_list", FileListTool);
        manager.register("current_time", CurrentTimeTool);
        manager.register("gnome_search_background", GnomeSearchBackgroundTool);
        manager.register("gnome_set_background", GnomeSetBackgroundTool);
        manager.register("gnome_theme", GnomeThemeTool);
        manager.register("gnome_opener", GnomeOpenerTool);
        manager.register("gnome_audio_control", GnomeAudioControlTool);
        manager.register("gnome_radio", GnomeRadioTool);
        manager.register("gnome_document", GnomeDocumentTool);
        manager.register("calendar_add_event", CalendarAddEventTool);
        manager.register("calendar_list_events", CalendarListEventsTool);
        manager.register("calendar_remove_event", CalendarRemoveEventTool);
        manager.register("calendar_list_sources", CalendarListCalendarsTool);
        manager.register("calendar_create", CalendarCreateCalendarTool);
        manager
    }

    fn register(&mut self, name: &str, tool: impl Tool + 'static) {
        self.tools.insert(name.to_string(), Box::new(tool));
    }

    pub fn instance() -> Arc<Mutex<ToolManager>> {
        TOOL_MANAGER.clone()
    }

    pub fn get_ollama_tools_definitions(&self) -> Vec<Value> {
        let config = ConfigManager::global();
        let enabled_tools = config
            .get_json("enabled_tools")
            .unwrap_or(serde_json::json!({}));

        self.tools
            .iter()
            .filter(|(name, _)| {
                enabled_tools
                    .get(name.as_str())
                    .and_then(|v| v.as_bool())
                    .unwrap_or(true)
            })
            .map(|(_, tool)| tool.to_ollama_format())
            .collect()
    }

    pub fn execute_tool(
        &self,
        tool_name: &str,
        args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let config = ConfigManager::global();
        let enabled_tools = config
            .get_json("enabled_tools")
            .unwrap_or(serde_json::json!({}));

        let enabled = enabled_tools
            .get(tool_name)
            .and_then(|v| v.as_bool())
            .unwrap_or(true);

        if !enabled {
            return Err(format!("Tool '{}' is disabled in settings.", tool_name));
        }

        match self.tools.get(tool_name) {
            Some(tool) => tool.execute(args, status_callback),
            None => Err(format!("Tool '{}' not found.", tool_name)),
        }
    }
}

static TOOL_MANAGER: Lazy<Arc<Mutex<ToolManager>>> =
    Lazy::new(|| Arc::new(Mutex::new(ToolManager::new())));
