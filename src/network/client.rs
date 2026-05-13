use once_cell::sync::Lazy;
use reqwest::Client;
use std::sync::Arc;

static HTTP_CLIENT: Lazy<Arc<Client>> = Lazy::new(|| {
    Arc::new(
        Client::builder()
            .timeout(std::time::Duration::from_secs(1200))
            .user_agent("Gaia/0.5.0")
            .build()
            .expect("Failed to create HTTP client"),
    )
});

pub fn get_http_client() -> Arc<Client> {
    HTTP_CLIENT.clone()
}
