use crate::config::get_artifacts_dir;
use crate::tools::base::Tool;
use serde_json::Value;
use std::path::Path;
use walkdir::WalkDir;

pub struct FileListTool;

impl Tool for FileListTool {
    fn name(&self) -> &'static str {
        "file_list"
    }

    fn description(&self) -> &'static str {
        "List all files in the current project's artifact directory."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project (chat) to list files from."
                },
                "path": {
                    "type": "string",
                    "description": "Optional subdirectory within the project's artifacts."
                }
            },
            "required": ["project_id"]
        })
    }

    fn execute(
        &self,
        args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let project_id = args["project_id"]
            .as_str()
            .ok_or("Missing 'project_id' argument")?;
        let subpath = args["path"].as_str().unwrap_or("");

        let artifacts_dir = get_artifacts_dir();
        let base_path = artifacts_dir.join(project_id).join(subpath);

        if !base_path.exists() {
            return Err(format!("Project directory '{}' not found.", project_id));
        }

        if let Some(ref cb) = status_callback {
            cb("Listing files...");
        }

        let mut files = Vec::new();

        for entry in WalkDir::new(&base_path)
            .sort_by_file_name()
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();
            if path.is_file() {
                let rel_path = path
                    .strip_prefix(&artifacts_dir)
                    .unwrap_or(path)
                    .display()
                    .to_string();
                let size = std::fs::metadata(path).map(|m| m.len()).unwrap_or(0);
                files.push(serde_json::json!({
                    "path": rel_path,
                    "size": size
                }));
            }
        }

        Ok(serde_json::json!({
            "project_id": project_id,
            "files": files,
            "count": files.len()
        }))
    }
}
