use crate::config::get_artifacts_dir;
use crate::tools::base::Tool;
use serde_json::Value;
use std::fs;

pub struct FileEditorTool;

impl Tool for FileEditorTool {
    fn name(&self) -> &'static str {
        "file_editor"
    }

    fn description(&self) -> &'static str {
        "Search and replace text in a file within the project's artifact directory."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "The relative path of the file to edit."
                },
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project (chat) where the file is located."
                },
                "search": {
                    "type": "string",
                    "description": "The exact text to find in the file."
                },
                "replace": {
                    "type": "string",
                    "description": "The text to replace the found text with."
                }
            },
            "required": ["filepath", "project_id", "search", "replace"]
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
        let search = args["search"].as_str().ok_or("Missing 'search' argument")?;
        let replace = args["replace"]
            .as_str()
            .ok_or("Missing 'replace' argument")?;

        let artifacts_dir = get_artifacts_dir();
        let full_path = artifacts_dir.join(project_id).join(filepath);

        if let Some(ref cb) = status_callback {
            cb(&format!("Editing {}...", filepath));
        }

        let content = fs::read_to_string(&full_path).map_err(|e| {
            format!(
                "Failed to read '{}' in project '{}': {}",
                filepath, project_id, e
            )
        })?;

        if !content.contains(search) {
            let (flex_content, flex_count) = flexible_replace(&content, search, replace);
            if flex_count > 0 {
                fs::write(&full_path, &flex_content)
                    .map_err(|e| format!("Failed to write '{}': {}", filepath, e))?;
                return Ok(serde_json::json!({
                    "success": true,
                    "filepath": filepath,
                    "replacements": flex_count,
                    "flexible": true
                }));
            }
            return Err(format!("Search text not found in '{}'.", filepath));
        }

        let count = content.matches(search).count();
        let new_content = content.replace(search, replace);

        fs::write(&full_path, &new_content)
            .map_err(|e| format!("Failed to write '{}': {}", filepath, e))?;

        Ok(serde_json::json!({
            "success": true,
            "filepath": filepath,
            "replacements": count
        }))
    }
}

fn flexible_replace(content: &str, search: &str, replace: &str) -> (String, usize) {
    let search_lines: Vec<&str> = search
        .lines()
        .map(|l| l.trim())
        .filter(|l| !l.is_empty())
        .collect();

    if search_lines.is_empty() {
        return (content.to_string(), 0);
    }

    let content_lines: Vec<&str> = content.lines().collect();
    let mut result = Vec::new();
    let mut i = 0;
    let mut count = 0;

    while i < content_lines.len() {
        if i + search_lines.len() <= content_lines.len() {
            let mut matches = true;
            for j in 0..search_lines.len() {
                if content_lines[i + j].trim() != search_lines[j] {
                    matches = false;
                    break;
                }
            }
            if matches {
                result.push(replace.to_string());
                i += search_lines.len();
                count += 1;
                continue;
            }
        }
        result.push(content_lines[i].to_string());
        i += 1;
    }

    (result.join("\n"), count)
}
