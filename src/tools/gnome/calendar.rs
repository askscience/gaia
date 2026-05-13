use crate::tools::base::Tool;
use serde_json::Value;

pub struct CalendarAddEventTool;

impl Tool for CalendarAddEventTool {
    fn name(&self) -> &'static str {
        "calendar_add_event"
    }

    fn description(&self) -> &'static str {
        "Add a calendar event (not yet implemented via GDBus)."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "The title of the event."
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format."
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in ISO 8601 format."
                },
                "calendar_name": {
                    "type": "string",
                    "description": "Name of the calendar."
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the event."
                }
            },
            "required": ["summary", "start_time", "end_time"]
        })
    }

    fn execute(
        &self,
        _args: &Value,
        _status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        Err("calendar_add_event: GDBus integration not yet implemented.".to_string())
    }
}

pub struct CalendarListEventsTool;

impl Tool for CalendarListEventsTool {
    fn name(&self) -> &'static str {
        "calendar_list_events"
    }

    fn description(&self) -> &'static str {
        "List calendar events for a date range (not yet implemented via GDBus)."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in ISO 8601 format."
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in ISO 8601 format."
                },
                "calendar_name": {
                    "type": "string",
                    "description": "Name of the calendar to query."
                }
            },
            "required": []
        })
    }

    fn execute(
        &self,
        _args: &Value,
        _status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        Err("calendar_list_events: GDBus integration not yet implemented.".to_string())
    }
}

pub struct CalendarRemoveEventTool;

impl Tool for CalendarRemoveEventTool {
    fn name(&self) -> &'static str {
        "calendar_remove_event"
    }

    fn description(&self) -> &'static str {
        "Remove a calendar event by UUID (not yet implemented via GDBus)."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "event_uid": {
                    "type": "string",
                    "description": "The UUID of the event to remove."
                },
                "calendar_name": {
                    "type": "string",
                    "description": "Name of the calendar."
                }
            },
            "required": ["event_uid"]
        })
    }

    fn execute(
        &self,
        _args: &Value,
        _status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        Err("calendar_remove_event: GDBus integration not yet implemented.".to_string())
    }
}

pub struct CalendarListCalendarsTool;

impl Tool for CalendarListCalendarsTool {
    fn name(&self) -> &'static str {
        "calendar_list_sources"
    }

    fn description(&self) -> &'static str {
        "List available calendars (not yet implemented via GDBus)."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {},
            "required": []
        })
    }

    fn execute(
        &self,
        _args: &Value,
        _status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        Err("calendar_list_sources: GDBus integration not yet implemented.".to_string())
    }
}

pub struct CalendarCreateCalendarTool;

impl Tool for CalendarCreateCalendarTool {
    fn name(&self) -> &'static str {
        "calendar_create"
    }

    fn description(&self) -> &'static str {
        "Create a new calendar (not yet implemented via GDBus)."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Display name for the new calendar."
                },
                "color": {
                    "type": "string",
                    "description": "Color in hex format (e.g. '#ff0000')."
                }
            },
            "required": ["name"]
        })
    }

    fn execute(
        &self,
        _args: &Value,
        _status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        Err("calendar_create: GDBus integration not yet implemented.".to_string())
    }
}
