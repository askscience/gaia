use crate::tools::base::Tool;
use reqwest::blocking::Client;
use scraper::{Html, Selector};
use serde_json::Value;
use std::time::Duration;

pub struct WebSearchTool;

impl Tool for WebSearchTool {
    fn name(&self) -> &'static str {
        "web_search"
    }

    fn description(&self) -> &'static str {
        "Search the web via DuckDuckGo and optionally scrape content from result URLs. Returns structured results with AI context and sources."
    }

    fn parameters(&self) -> Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (default: 3)."
                },
                "scrape_url": {
                    "type": "string",
                    "description": "Optional: fetch and extract text from a specific URL."
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
        if let Some(scrape_url) = args["scrape_url"].as_str() {
            return self.scrape_content(scrape_url, status_callback);
        }

        let query = args["query"].as_str().ok_or("Missing 'query' argument")?;
        let max_results = args["max_results"].as_u64().unwrap_or(3) as usize;

        if let Some(ref cb) = status_callback {
            cb(&format!("Searching for '{}'...", query));
        }

        let results = self.search(query, max_results)?;

        if results.is_empty() {
            return Ok(serde_json::json!({
                "error": "No results found.",
                "sources": []
            }));
        }

        let mut sources = Vec::new();
        let mut ai_context = String::new();

        for res in &results {
            let title = res.title.as_deref().unwrap_or("Untitled");
            let url = res.url.as_deref().unwrap_or("");
            let snippet = res.snippet.as_deref().unwrap_or("");

            let domain = url::Url::parse(url)
                .ok()
                .and_then(|u| u.domain().map(|d| d.to_string()))
                .unwrap_or_default();

            sources.push(serde_json::json!({
                "title": title,
                "url": url,
                "domain": domain,
                "snippet": snippet
            }));

            ai_context.push_str(&format!("\n## {}\n", title));

            let scraped = self.fetch_page_text(url);
            if !scraped.is_empty() {
                ai_context.push_str(&scraped);
            } else {
                ai_context.push_str(snippet);
            }
            ai_context.push_str("\n---\n");
        }

        Ok(serde_json::json!({
            "AI_CONTEXT": ai_context,
            "SOURCES": sources
        }))
    }
}

struct SearchResult {
    title: Option<String>,
    url: Option<String>,
    snippet: Option<String>,
}

impl WebSearchTool {
    fn build_client() -> Result<Client, String> {
        Client::builder()
            .timeout(Duration::from_secs(15))
            .user_agent(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 \
                 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            .build()
            .map_err(|e| format!("Failed to create HTTP client: {}", e))
    }

    fn search(&self, query: &str, max_results: usize) -> Result<Vec<SearchResult>, String> {
        let client = Self::build_client()?;
        let url = format!("https://html.duckduckgo.com/html/?q={}", urlencode(query));

        let resp = client
            .get(&url)
            .send()
            .map_err(|e| format!("Search request failed: {}", e))?;

        let html = resp
            .text()
            .map_err(|e| format!("Failed to read response: {}", e))?;

        self.parse_results(&html, max_results)
    }

    fn parse_results(&self, html: &str, max_results: usize) -> Result<Vec<SearchResult>, String> {
        let document = Html::parse_document(html);
        let result_sel =
            Selector::parse(".result").map_err(|e| format!("CSS parse error: {}", e))?;
        let title_sel =
            Selector::parse(".result__title").map_err(|e| format!("CSS parse error: {}", e))?;
        let snippet_sel =
            Selector::parse(".result__snippet").map_err(|e| format!("CSS parse error: {}", e))?;
        let url_sel =
            Selector::parse(".result__url").map_err(|e| format!("CSS parse error: {}", e))?;

        let mut results = Vec::new();

        for element in document.select(&result_sel).take(max_results) {
            let title = element
                .select(&title_sel)
                .next()
                .map(|el| el.text().collect::<Vec<_>>().join(" ").trim().to_string());

            let snippet = element
                .select(&snippet_sel)
                .next()
                .map(|el| el.text().collect::<Vec<_>>().join(" ").trim().to_string());

            let mut url = element
                .select(&url_sel)
                .next()
                .map(|el| el.text().collect::<Vec<_>>().join("").trim().to_string());

            if let Some(ref raw_url) = url {
                if !raw_url.starts_with("http") {
                    url = Some(format!("https://{}", raw_url.trim_start_matches('/')));
                }
            }

            results.push(SearchResult {
                title,
                snippet,
                url,
            });
        }

        Ok(results)
    }

    fn scrape_content(
        &self,
        url: &str,
        status_callback: Option<Box<dyn Fn(&str) + Send>>,
    ) -> Result<Value, String> {
        if let Some(ref cb) = status_callback {
            cb(&format!("Fetching content from {}...", url));
        }

        let text = self.fetch_page_text(url);

        Ok(serde_json::json!({
            "url": url,
            "content": text
        }))
    }

    fn fetch_page_text(&self, url: &str) -> String {
        let client = match Client::builder()
            .timeout(Duration::from_secs(15))
            .user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
            .build()
        {
            Ok(c) => c,
            Err(_) => return String::new(),
        };

        let resp = match client.get(url).send() {
            Ok(r) => r,
            Err(_) => return String::new(),
        };

        let html = match resp.text() {
            Ok(t) => t,
            Err(_) => return String::new(),
        };

        let document = Html::parse_document(&html);

        let body_sel = match Selector::parse("body") {
            Ok(s) => s,
            Err(_) => return String::new(),
        };

        if let Some(body) = document.select(&body_sel).next() {
            let text: String = body.text().collect::<Vec<_>>().join(" ");
            let trimmed = text.trim().to_string();
            if trimmed.chars().count() > 5000 {
                trimmed.chars().take(5000).collect()
            } else {
                trimmed
            }
        } else {
            String::new()
        }
    }
}

fn urlencode(s: &str) -> String {
    let mut result = String::with_capacity(s.len() * 3);
    for byte in s.bytes() {
        match byte {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                result.push(byte as char);
            }
            b' ' => result.push('+'),
            _ => {
                result.push_str(&format!("%{:02X}", byte));
            }
        }
    }
    result
}
