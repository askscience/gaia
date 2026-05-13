use crate::tools::base::Tool;
use serde_json::Value;
use std::process::Command;

pub struct GnomeThemeTool;

impl Tool for GnomeThemeTool {
    fn name(&self) -> &'static str {
        "gnome_theme"
    }

    fn description(&self) -> &'static str {
        "Switch the system theme between light and dark mode."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["light", "dark"],
                    "description": "The theme mode to switch to."
                }
            },
            "required": ["mode"]
        })
    }

    fn execute(
        &self,
        args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let mode = args["mode"].as_str().ok_or("Missing 'mode' argument")?;

        let value = match mode.to_lowercase().as_str() {
            "dark" => "prefer-dark",
            "light" => "prefer-light",
            _ => return Err(format!("Invalid mode '{}'. Use 'light' or 'dark'.", mode)),
        };

        if let Some(ref cb) = status_callback {
            cb(&format!("Switching to {} theme...", mode));
        }

        let output = Command::new("gsettings")
            .args(["set", "org.gnome.desktop.interface", "color-scheme", value])
            .output()
            .map_err(|e| format!("Failed to run gsettings: {}", e))?;

        if !output.status.success() {
            return Err(format!(
                "Failed to set theme: {}",
                String::from_utf8_lossy(&output.stderr)
            ));
        }

        Ok(serde_json::json!({
            "success": true,
            "mode": mode
        }))
    }
}
