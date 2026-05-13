use crate::config::ConfigManager;

pub fn apply_proxy_settings() {
    let config = ConfigManager::global();

    let enabled = config.get_bool("proxy_enabled", false);
    let proxy_url = config.get("proxy_url");

    if enabled && !proxy_url.is_empty() {
        let proxy_url = fix_proxy_url(&proxy_url);

        unsafe {
            std::env::set_var("HTTP_PROXY", &proxy_url);
            std::env::set_var("HTTPS_PROXY", &proxy_url);
            std::env::set_var("ALL_PROXY", &proxy_url);
            std::env::set_var("http_proxy", &proxy_url);
            std::env::set_var("https_proxy", &proxy_url);
            std::env::set_var("all_proxy", &proxy_url);
        }
    } else {
        unsafe {
            std::env::remove_var("HTTP_PROXY");
            std::env::remove_var("HTTPS_PROXY");
            std::env::remove_var("ALL_PROXY");
            std::env::remove_var("http_proxy");
            std::env::remove_var("https_proxy");
            std::env::remove_var("all_proxy");
        }
    }
}

fn fix_proxy_url(url: &str) -> String {
    if url.starts_with("localhost:9050") || url.starts_with("127.0.0.1:9050") || url == "9050" {
        return format!("socks5://{}", url);
    }

    if !url.contains("://") {
        return format!("http://{}", url);
    }

    url.to_string()
}
