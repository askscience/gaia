use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{Mutex, OwnedSemaphorePermit, Semaphore};

use crate::concurrency::limits::get_limit_for_provider;

pub struct ConcurrencyManager {
    semaphores: HashMap<String, Arc<Semaphore>>,
}

impl ConcurrencyManager {
    pub fn global() -> &'static Arc<Mutex<ConcurrencyManager>> {
        static INSTANCE: once_cell::sync::Lazy<Arc<Mutex<ConcurrencyManager>>> =
            once_cell::sync::Lazy::new(|| Arc::new(Mutex::new(ConcurrencyManager::new())));
        &INSTANCE
    }

    pub fn new() -> Self {
        ConcurrencyManager {
            semaphores: HashMap::new(),
        }
    }

    pub async fn acquire(&mut self, provider: &str) -> OwnedSemaphorePermit {
        let limit = get_limit_for_provider(provider);
        let sem = self
            .semaphores
            .entry(provider.to_string())
            .or_insert_with(|| Arc::new(Semaphore::new(limit)))
            .clone();
        sem.acquire_owned().await.unwrap()
    }
}
