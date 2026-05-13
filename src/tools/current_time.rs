use crate::config::get_artifacts_dir;
use crate::tools::base::Tool;
use chrono::Local;
use serde_json::Value;

pub struct CurrentTimeTool;

impl Tool for CurrentTimeTool {
    fn name(&self) -> &'static str {
        "current_time"
    }

    fn description(&self) -> &'static str {
        "Get the current system time in ISO 8601 format."
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
        let now = Local::now();
        Ok(serde_json::json!({
            "datetime": now.to_rfc3339(),
            "timezone": now.format("%:z").to_string()
        }))
    }
}
