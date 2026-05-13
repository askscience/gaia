use crate::tools::base::Tool;
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};

pub struct GnomeDocumentTool;

impl Tool for GnomeDocumentTool {
    fn name(&self) -> &'static str {
        "gnome_document"
    }

    fn description(&self) -> &'static str {
        "Find and read local documents (PDF, TXT). Supports searching by filename and extracting text."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["find", "read"],
                    "description": "Action: 'find' files by name or 'read' a file's content."
                },
                "filepath": {
                    "type": "string",
                    "description": "The file path or name to find/read."
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to search in (default: home directory)."
                }
            },
            "required": ["action", "filepath"]
        })
    }

    fn execute(
        &self,
        args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let action = args["action"].as_str().ok_or("Missing 'action' argument")?;
        let filepath = args["filepath"]
            .as_str()
            .ok_or("Missing 'filepath' argument")?;

        match action {
            "find" => self.find_files(filepath, args, status_callback),
            "read" => self.read_file(filepath, args, status_callback),
            _ => Err(format!("Unknown action: {}", action)),
        }
    }
}

impl GnomeDocumentTool {
    fn find_files(
        &self,
        filename: &str,
        args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let search_dir = args["directory"]
            .as_str()
            .map(PathBuf::from)
            .unwrap_or_else(|| dirs::home_dir().unwrap_or_else(|| PathBuf::from("/")));

        if !search_dir.exists() {
            return Err(format!(
                "Directory '{}' does not exist.",
                search_dir.display()
            ));
        }

        if let Some(ref cb) = status_callback {
            cb(&format!("Searching for '{}'...", filename));
        }

        let mut results = Vec::new();
        let max_depth = 3;
        let max_results = 10;

        find_recursive(
            &search_dir,
            filename,
            0,
            max_depth,
            &mut results,
            max_results,
        );

        if results.is_empty() {
            return Err(format!("No files matching '{}' found.", filename));
        }

        Ok(serde_json::json!({
            "found": results,
            "count": results.len(),
            "directory": search_dir.to_string_lossy()
        }))
    }

    fn read_file(
        &self,
        filepath: &str,
        _args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let path = Path::new(filepath);

        if let Some(ref cb) = status_callback {
            cb(&format!("Reading {}...", filepath));
        }

        if !path.exists() {
            return Err(format!("File '{}' does not exist.", filepath));
        }

        let extension = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();

        match extension.as_str() {
            "txt" | "md" | "csv" | "json" | "xml" | "html" | "py" | "rs" | "js" | "css" => {
                let content =
                    fs::read_to_string(path).map_err(|e| format!("Failed to read file: {}", e))?;
                Ok(serde_json::json!({
                    "filepath": filepath,
                    "content": content,
                    "type": "text"
                }))
            }
            "pdf" => self.read_pdf(path),
            _ => Err(format!(
                "Unsupported file type '{}'. Supported: pdf, txt, md, and code files.",
                extension
            )),
        }
    }

    fn read_pdf(&self, path: &Path) -> Result<Value, String> {
        let doc = lopdf::Document::load(path).map_err(|e| format!("Failed to load PDF: {}", e))?;

        let page_count = doc.get_pages().len();
        let mut full_text = String::new();

        for page_num in 1..=page_count {
            let text = doc.extract_text(&[page_num as u32]);
            if let Ok(t) = text {
                full_text.push_str(&t);
                full_text.push('\n');
            }
        }

        Ok(serde_json::json!({
            "filepath": path.to_string_lossy(),
            "content": full_text,
            "pages": page_count,
            "type": "pdf"
        }))
    }
}

fn find_recursive(
    dir: &Path,
    pattern: &str,
    depth: usize,
    max_depth: usize,
    results: &mut Vec<String>,
    max_results: usize,
) {
    if depth > max_depth || results.len() >= max_results {
        return;
    }

    let pattern_lower = pattern.to_lowercase();

    if let Ok(entries) = fs::read_dir(dir) {
        let mut paths: Vec<_> = entries.filter_map(|e| e.ok()).collect();
        paths.sort_by_key(|e| e.file_name());

        for entry in paths {
            let path = entry.path();
            let name = entry.file_name().to_string_lossy().to_lowercase();

            if results.len() >= max_results {
                break;
            }

            if name.contains(&pattern_lower) && path.is_file() {
                results.push(path.to_string_lossy().to_string());
            }

            if path.is_dir()
                && !path
                    .file_name()
                    .map(|n| n.to_string_lossy().starts_with('.'))
                    .unwrap_or(false)
            {
                find_recursive(&path, pattern, depth + 1, max_depth, results, max_results);
            }
        }
    }
}
