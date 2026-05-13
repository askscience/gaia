use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

pub struct VoskListener {
    model_path: Option<String>,
    running: Arc<AtomicBool>,
    paused: Arc<AtomicBool>,
    model_loaded: bool,
}

impl VoskListener {
    pub fn new() -> Self {
        VoskListener {
            model_path: None,
            running: Arc::new(AtomicBool::new(false)),
            paused: Arc::new(AtomicBool::new(false)),
            model_loaded: false,
        }
    }

    pub fn set_model_path(&mut self, path: &str) -> bool {
        let p = PathBuf::from(path);
        if !p.exists() {
            println!("Vosk model path not found: {}", path);
            return false;
        }
        self.model_path = Some(path.to_string());
        self.model_loaded = true;
        true
    }

    pub fn model(&self) -> bool {
        self.model_loaded
    }

    pub fn listen_loop<F>(&mut self, on_result: F)
    where
        F: Fn(String, bool) + Send + 'static,
    {
        if self.model_path.is_none() {
            println!("No Vosk model loaded.");
            return;
        }

        self.running.store(true, Ordering::SeqCst);
        self.paused.store(false, Ordering::SeqCst);

        let running = self.running.clone();
        let paused = self.paused.clone();

        thread::spawn(move || {
            println!("[VoskListener] Starting speech recognition simulation...");
            println!("[VoskListener] Note: Full speech recognition requires Vosk C library.");

            while running.load(Ordering::SeqCst) {
                if paused.load(Ordering::SeqCst) {
                    thread::sleep(Duration::from_millis(100));
                    continue;
                }

                thread::sleep(Duration::from_secs(1));
            }

            println!("[VoskListener] Stopped.");
        });
    }

    pub fn listen_loop_callback<F>(&mut self, callback: F)
    where
        F: Fn(String) + Send + 'static,
    {
        self.listen_loop(move |text, is_final| {
            if is_final {
                callback(text);
            }
        });
    }

    pub fn start<F>(&self, _callback: F)
    where
        F: Fn(String) + Send + 'static,
    {
        self.running.store(true, Ordering::SeqCst);
    }

    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
    }

    pub fn pause(&self) {
        self.paused.store(true, Ordering::SeqCst);
    }

    pub fn resume(&self) {
        self.paused.store(false, Ordering::SeqCst);
    }

    pub fn is_listening(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }

    pub fn recognize_file(&self, _audio_path: &str) -> Option<String> {
        let model_path = self.model_path.as_ref()?;
        let output = Command::new("vosk-cli")
            .arg("--model")
            .arg(model_path)
            .arg("--input")
            .arg(_audio_path)
            .output()
            .ok()?;

        if output.status.success() {
            let text = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !text.is_empty() {
                return Some(text);
            }
        }
        None
    }
}

impl Default for VoskListener {
    fn default() -> Self {
        Self::new()
    }
}
