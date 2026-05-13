use crate::tools::base::Tool;
use reqwest::blocking::Client;
use serde_json::Value;
use std::process::Command;
use std::time::Duration;

fn command_exists(cmd: &str) -> bool {
    Command::new("which")
        .arg(cmd)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

pub struct GnomeRadioTool;

impl Tool for GnomeRadioTool {
    fn name(&self) -> &'static str {
        "gnome_radio"
    }

    fn description(&self) -> &'static str {
        "Search for internet radio stations via radio-browser.info and optionally play a stream."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "play"],
                    "description": "Action: 'search' for stations or 'play' a stream URL."
                },
                "query": {
                    "type": "string",
                    "description": "Search query (genre, name, country) for 'search'."
                },
                "url": {
                    "type": "string",
                    "description": "Stream URL to play for 'play' action."
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

        match action {
            "search" => {
                let query = args["query"].as_str().ok_or("Missing 'query' for search")?;
                self.search_stations(query, status_callback)
            }
            "play" => {
                let url = args["url"].as_str().ok_or("Missing 'url' for play")?;
                self.play_station(url, status_callback)
            }
            _ => Err(format!("Unknown action: {}", action)),
        }
    }
}

impl GnomeRadioTool {
    fn search_stations(
        &self,
        query: &str,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        if let Some(ref cb) = status_callback {
            cb(&format!("Searching radio stations for '{}'...", query));
        }

        let client = Client::builder()
            .timeout(Duration::from_secs(10))
            .build()
            .map_err(|e| format!("HTTP client error: {}", e))?;

        let base_url = "https://de1.api.radio-browser.info";

        let resp = client
            .get(format!("{}/json/stations/search", base_url))
            .query(&[
                ("name", query),
                ("limit", "8"),
                ("hidebroken", "true"),
                ("order", "clickcount"),
                ("reverse", "true"),
            ])
            .send()
            .map_err(|e| format!("Radio search failed: {}", e))?;

        let mut data: Value = resp
            .json()
            .map_err(|e| format!("Failed to parse response: {}", e))?;

        if data.as_array().map(|a| a.is_empty()).unwrap_or(true) {
            let resp2 = client
                .get(format!("{}/json/stations/search", base_url))
                .query(&[
                    ("tag", query),
                    ("limit", "8"),
                    ("hidebroken", "true"),
                    ("order", "clickcount"),
                    ("reverse", "true"),
                ])
                .send()
                .map_err(|e| format!("Radio tag search failed: {}", e))?;

            data = resp2
                .json()
                .map_err(|e| format!("Failed to parse response: {}", e))?;
        }

        let stations: Vec<Value> = data
            .as_array()
            .unwrap_or(&vec![])
            .iter()
            .map(|st| {
                serde_json::json!({
                    "name": st["name"].as_str().unwrap_or("Unknown"),
                    "url": st["url_resolved"].as_str().unwrap_or(""),
                    "bitrate": st["bitrate"].as_u64().unwrap_or(0),
                    "country": st["country"].as_str().unwrap_or(""),
                    "tags": st["tags"].as_str().unwrap_or("")
                })
            })
            .collect();

        if stations.is_empty() {
            return Err(format!("No stations found for '{}'.", query));
        }

        Ok(serde_json::json!({
            "stations": stations,
            "count": stations.len()
        }))
    }

    fn play_station(
        &self,
        url: &str,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        if let Some(ref cb) = status_callback {
            cb(&format!("Playing {}...", url));
        }

        let players = ["totem", "rhythmbox-client", "vlc", "mpv"];

        for player in &players {
            if command_exists(player) {
                let mut cmd = if *player == "rhythmbox-client" {
                    let mut c = Command::new("rhythmbox-client");
                    c.arg(format!("--play-uri={}", url));
                    c
                } else {
                    let mut c = Command::new(player);
                    c.arg(url);
                    c
                };

                let _ = cmd
                    .stdout(std::process::Stdio::null())
                    .stderr(std::process::Stdio::null())
                    .spawn();

                return Ok(serde_json::json!({
                    "success": true,
                    "player": player,
                    "url": url
                }));
            }
        }

        Ok(serde_json::json!({
            "success": false,
            "url": url,
            "message": "No media player found. Stream URL returned for manual playback."
        }))
    }
}
