use crate::tools::base::Tool;
use serde_json::Value;
use std::process::Command;

pub struct GnomeOpenerTool;

impl Tool for GnomeOpenerTool {
    fn name(&self) -> &'static str {
        "gnome_opener"
    }

    fn description(&self) -> &'static str {
        "Open a file, URL, or launch a system application."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path, URL, or application name to open."
                }
            },
            "required": ["path"]
        })
    }

    fn execute(
        &self,
        args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let path = args["path"].as_str().ok_or("Missing 'path' argument")?;

        if let Some(ref cb) = status_callback {
            cb(&format!("Opening {}...", path));
        }

        let _child = Command::new("xdg-open")
            .arg(path)
            .spawn()
            .map_err(|e| format!("Failed to run xdg-open: {}", e))?;

        Ok(serde_json::json!({
            "success": true,
            "path": path
        }))
    }
}
