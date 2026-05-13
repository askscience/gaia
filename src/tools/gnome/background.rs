use crate::config::ConfigManager;
use crate::tools::base::Tool;
use reqwest::blocking::Client;
use serde_json::Value;
use std::path::PathBuf;
use std::process::Command;
use std::time::Duration;

pub struct GnomeSearchBackgroundTool;

impl Tool for GnomeSearchBackgroundTool {
    fn name(&self) -> &'static str {
        "gnome_search_background"
    }

    fn description(&self) -> &'static str {
        "Search for high-quality wallpapers from Unsplash or Pexels."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for wallpapers (e.g., 'nature', 'city', 'mountains')."
                }
            },
            "required": ["query"]
        })
    }

    fn execute(
        &self,
        args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let query = args["query"].as_str().ok_or("Missing 'query' argument")?;

        if let Some(ref cb) = status_callback {
            cb(&format!("Searching wallpapers for '{}'...", query));
        }

        let config = ConfigManager::global();
        let unsplash_key = config.get("unsplash_access_key").trim().to_string();
        let pexels_key = config.get("pexels_api_key").trim().to_string();

        let mut all_images = Vec::new();

        if !unsplash_key.is_empty() {
            if let Ok(images) = search_unsplash(query, &unsplash_key) {
                all_images.extend(images);
            }
        }

        if !pexels_key.is_empty() {
            if let Ok(images) = search_pexels(query, &pexels_key) {
                all_images.extend(images);
            }
        }

        if all_images.is_empty() {
            return Err("No wallpaper sources configured. Set 'unsplash_access_key' or 'pexels_api_key' in ~/.gaia/config.json.".to_string());
        }

        let images: Vec<_> = all_images.into_iter().take(4).collect();

        Ok(serde_json::json!({
            "images": images,
            "count": images.len()
        }))
    }
}

fn search_unsplash(query: &str, access_key: &str) -> Result<Vec<Value>, String> {
    let client = Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("HTTP client error: {}", e))?;

    let resp = client
        .get("https://api.unsplash.com/search/photos")
        .query(&[
            ("query", query),
            ("per_page", "4"),
            ("orientation", "landscape"),
        ])
        .header("Authorization", format!("Client-ID {}", access_key))
        .send()
        .map_err(|e| format!("Unsplash request failed: {}", e))?;

    let data: Value = resp
        .json()
        .map_err(|e| format!("Unsplash response error: {}", e))?;

    let mut results = Vec::new();
    if let Some(items) = data["results"].as_array() {
        for item in items {
            if let (Some(url), Some(name), Some(user_url)) = (
                item["urls"]["regular"].as_str(),
                item["user"]["name"].as_str(),
                item["user"]["links"]["html"].as_str(),
            ) {
                results.push(serde_json::json!({
                    "description": item["alt_description"].as_str().unwrap_or("Wallpaper"),
                    "url": url,
                    "attribution_name": name,
                    "attribution_url": user_url,
                    "source": "unsplash"
                }));
            }
        }
    }
    Ok(results)
}

fn search_pexels(query: &str, api_key: &str) -> Result<Vec<Value>, String> {
    let client = Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("HTTP client error: {}", e))?;

    let resp = client
        .get("https://api.pexels.com/v1/search")
        .query(&[
            ("query", query),
            ("per_page", "4"),
            ("orientation", "landscape"),
        ])
        .header("Authorization", api_key)
        .send()
        .map_err(|e| format!("Pexels request failed: {}", e))?;

    let data: Value = resp
        .json()
        .map_err(|e| format!("Pexels response error: {}", e))?;

    let mut results = Vec::new();
    if let Some(items) = data["photos"].as_array() {
        for item in items {
            if let (Some(url), Some(name), Some(user_url)) = (
                item["src"]["large"].as_str(),
                item["photographer"].as_str(),
                item["photographer_url"].as_str(),
            ) {
                results.push(serde_json::json!({
                    "description": item["alt"].as_str().unwrap_or("Wallpaper"),
                    "url": url,
                    "attribution_name": name,
                    "attribution_url": user_url,
                    "source": "pexels"
                }));
            }
        }
    }
    Ok(results)
}

pub struct GnomeSetBackgroundTool;

impl Tool for GnomeSetBackgroundTool {
    fn name(&self) -> &'static str {
        "gnome_set_background"
    }

    fn description(&self) -> &'static str {
        "Set the desktop wallpaper from an image URL."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the image to set as wallpaper."
                }
            },
            "required": ["url"]
        })
    }

    fn execute(
        &self,
        args: &Value,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        let url = args["url"].as_str().ok_or("Missing 'url' argument")?;

        if let Some(ref cb) = status_callback {
            cb("Downloading wallpaper...");
        }

        let client = Client::builder()
            .timeout(Duration::from_secs(30))
            .user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
            .build()
            .map_err(|e| format!("HTTP client error: {}", e))?;

        let resp = client
            .get(url)
            .send()
            .map_err(|e| format!("Download failed: {}", e))?;

        let status = resp.status();
        if !status.is_success() {
            return Err(format!("Failed to download image: HTTP {}", status));
        }

        let bytes = resp
            .bytes()
            .map_err(|e| format!("Failed to read response: {}", e))?;

        let filename = url
            .split('/')
            .last()
            .and_then(|f| f.split('?').next())
            .unwrap_or("wallpaper.jpg");

        let filename = if filename.contains('.') {
            filename.to_string()
        } else {
            format!("{}.jpg", filename)
        };

        let cache_dir = dirs::cache_dir()
            .unwrap_or_else(|| PathBuf::from("/tmp"))
            .join("gaia/wallpapers");

        std::fs::create_dir_all(&cache_dir)
            .map_err(|e| format!("Failed to create cache dir: {}", e))?;

        let local_path = cache_dir.join(&filename);

        std::fs::write(&local_path, &bytes)
            .map_err(|e| format!("Failed to save wallpaper: {}", e))?;

        if let Some(ref cb) = status_callback {
            cb("Applying wallpaper...");
        }

        let uri = format!("file://{}", local_path.display());

        let output = Command::new("gsettings")
            .args(["set", "org.gnome.desktop.background", "picture-uri", &uri])
            .output()
            .map_err(|e| format!("Failed to run gsettings: {}", e))?;

        if !output.status.success() {
            return Err(format!(
                "gsettings failed: {}",
                String::from_utf8_lossy(&output.stderr)
            ));
        }

        let _ = Command::new("gsettings")
            .args([
                "set",
                "org.gnome.desktop.background",
                "picture-uri-dark",
                &uri,
            ])
            .output();

        Ok(serde_json::json!({
            "success": true,
            "message": "Wallpaper set successfully."
        }))
    }
}
