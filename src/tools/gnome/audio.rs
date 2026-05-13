use crate::tools::base::Tool;
use serde_json::Value;
use std::process::Command;

pub struct GnomeAudioControlTool;

impl Tool for GnomeAudioControlTool {
    fn name(&self) -> &'static str {
        "gnome_audio_control"
    }

    fn description(&self) -> &'static str {
        "Control system audio volume: get, set, mute, or unmute."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get", "set", "mute", "unmute"],
                    "description": "The audio action to perform."
                },
                "volume": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Volume level (0-100) for the 'set' action."
                }
            },
            "required": ["action"]
        })
    }

    fn execute(
        &self,
        args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let action = args["action"].as_str().ok_or("Missing 'action' argument")?;

        if let Some(ref cb) = status_callback {
            cb(&format!("Audio: {}...", action));
        }

        match action {
            "get" => self.get_volume(),
            "set" => {
                let volume = args["volume"]
                    .as_u64()
                    .ok_or("Missing 'volume' argument for 'set' action")?;
                self.set_volume(volume as u32)
            }
            "mute" => self.set_mute(true),
            "unmute" => self.set_mute(false),
            _ => Err(format!("Unknown action: {}", action)),
        }
    }
}

impl GnomeAudioControlTool {
    fn run_pactl(args: &[&str]) -> Result<String, String> {
        Command::new("pactl")
            .args(args)
            .output()
            .map(|out| String::from_utf8_lossy(&out.stdout).to_string())
            .map_err(|e| format!("Failed to run pactl: {}", e))
    }

    fn get_volume(&self) -> Result<Value, String> {
        let output = Self::run_pactl(&["get-sink-volume", "@DEFAULT_SINK@"])?;

        let percent = output
            .split('%')
            .next()
            .and_then(|before| before.rsplit(' ').next())
            .and_then(|s| s.parse::<u32>().ok())
            .unwrap_or(0);

        Ok(serde_json::json!({
            "volume": percent
        }))
    }

    fn set_volume(&self, level: u32) -> Result<Value, String> {
        let volume_str = format!("{}%", level);
        Self::run_pactl(&["set-sink-volume", "@DEFAULT_SINK@", &volume_str])?;

        Ok(serde_json::json!({
            "success": true,
            "volume": level
        }))
    }

    fn set_mute(&self, mute: bool) -> Result<Value, String> {
        let value = if mute { "1" } else { "0" };
        Self::run_pactl(&["set-sink-mute", "@DEFAULT_SINK@", value])?;

        Ok(serde_json::json!({
            "success": true,
            "muted": mute
        }))
    }
}
