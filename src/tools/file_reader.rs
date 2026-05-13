use crate::config::get_artifacts_dir;
use crate::tools::base::Tool;
use serde_json::Value;
use std::fs;

pub struct FileReaderTool;

impl Tool for FileReaderTool {
    fn name(&self) -> &'static str {
        "file_reader"
    }

    fn description(&self) -> &'static str {
        "Read a file from the current project's artifact directory."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "The relative path of the file to read."
                },
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project (chat) where the file is located."
                }
            },
            "required": ["filepath", "project_id"]
        })
    }

    fn execute(
        &self,
        args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let filepath = args["filepath"]
            .as_str()
            .ok_or("Missing 'filepath' argument")?;
        let project_id = args["project_id"]
            .as_str()
            .ok_or("Missing 'project_id' argument")?;

        let artifacts_dir = get_artifacts_dir();
        let full_path = artifacts_dir.join(project_id).join(filepath);

        if let Some(ref cb) = status_callback {
            cb(&format!("Reading {}...", filepath));
        }

        match fs::read_to_string(&full_path) {
            Ok(content) => {
                let truncated: String = if content.chars().count() > 5000 {
                    content.chars().take(5000).collect()
                } else {
                    content.clone()
                };
                Ok(serde_json::json!({
                    "filepath": filepath,
                    "content": truncated,
                    "truncated": content.len() > 5000,
                    "size": content.len()
                }))
            }
            Err(e) => Err(format!(
                "Failed to read '{}' in project '{}': {}",
                filepath, project_id, e
            )),
        }
    }
}
