use std::sync::{Arc, Mutex};
use tokio::sync::broadcast;

pub struct StatusManager {
    sender: broadcast::Sender<(String, String)>,
    callbacks: Arc<Mutex<Vec<Box<dyn Fn(String, String) + Send>>>>,
}

impl StatusManager {
    pub fn global() -> &'static StatusManager {
        static INSTANCE: once_cell::sync::Lazy<StatusManager> =
            once_cell::sync::Lazy::new(|| StatusManager::new());
        &INSTANCE
    }

    pub fn new() -> Self {
        let (sender, _) = broadcast::channel(256);
        StatusManager {
            sender,
            callbacks: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn emit_status(&self, project_id: &str, message: &str) {
        let payload = (project_id.to_string(), message.to_string());

        let _ = self.sender.send(payload.clone());

        let cbs = self.callbacks.lock().unwrap();
        for cb in cbs.iter() {
            cb(payload.0.clone(), payload.1.clone());
        }
    }

    pub fn subscribe(&self) -> broadcast::Receiver<(String, String)> {
        self.sender.subscribe()
    }

    pub fn register_callback<F>(&self, callback: F)
    where
        F: Fn(String, String) + Send + 'static,
    {
        self.callbacks.lock().unwrap().push(Box::new(callback));
    }

    pub fn callback_handle(&self) -> Arc<Mutex<Vec<Box<dyn Fn(String, String) + Send>>>> {
        self.callbacks.clone()
    }
}
