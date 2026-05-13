use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::thread;

use tokio::sync::mpsc;

use crate::voice::installer::VoiceInstaller;
use crate::voice::stt::VoskListener;
use crate::voice::tts::PiperTTS;

#[derive(Debug)]
enum VoiceCommand {
    Speak(String),
    Stop,
    StartListening,
    StopListening,
}

pub struct VoiceManager {
    active: Arc<Mutex<bool>>,
    interaction_active: Arc<Mutex<bool>>,
    conversation_deadline: Arc<Mutex<f64>>,
    model_path: Arc<Mutex<Option<String>>>,
    listener: Arc<Mutex<VoskListener>>,
    tts: Arc<Mutex<PiperTTS>>,
    command_tx: mpsc::UnboundedSender<VoiceCommand>,
}

impl VoiceManager {
    pub fn new() -> Self {
        let (command_tx, mut command_rx) = mpsc::unbounded_channel();

        let active = Arc::new(Mutex::new(false));
        let interaction_active = Arc::new(Mutex::new(false));
        let conversation_deadline = Arc::new(Mutex::new(0.0f64));

        let model_path = Arc::new(Mutex::new(None));
        let listener = Arc::new(Mutex::new(VoskListener::new()));
        let tts = Arc::new(Mutex::new(PiperTTS::new()));

        let home = dirs::home_dir().unwrap_or_default();
        let gaia_voice = home.join(".gaia/voice");

        if let Some(path) = discover_vosk_model(&gaia_voice) {
            *model_path.lock().unwrap() = Some(path);
        }

        let piper_bin = gaia_voice.join("piper/piper/piper");
        if piper_bin.exists() {
            tts.lock().unwrap().set_executable_path(&piper_bin);
        }

        {
            let listener = listener.clone();
            let active = active.clone();
            let interaction_active = interaction_active.clone();
            let conversation_deadline = conversation_deadline.clone();
            let command_tx = command_tx.clone();
            let tts = tts.clone();

            thread::spawn(move || {
                while let Some(cmd) = command_rx.blocking_recv() {
                    match cmd {
                        VoiceCommand::StartListening => {
                            if *active.lock().unwrap() {
                                continue;
                            }
                            *active.lock().unwrap() = true;
                            let listener = listener.clone();
                            let active = active.clone();
                            let interaction_active = interaction_active.clone();
                            let conversation_deadline = conversation_deadline.clone();
                            let command_tx = command_tx.clone();
                            thread::spawn(move || {
                                listener
                                    .lock()
                                    .unwrap()
                                    .listen_loop(move |text, _is_final| {
                                        if !*active.lock().unwrap() {
                                            return;
                                        }
                                        let deadline = *conversation_deadline.lock().unwrap();
                                        let now = current_time_secs();
                                        if now < deadline {
                                            let _ = command_tx.send(VoiceCommand::Speak(text));
                                        } else if check_wake_word_static(&text) {
                                            let _ = command_tx.send(VoiceCommand::Speak(text));
                                        }
                                    });
                            });
                        }
                        VoiceCommand::StopListening => {
                            *active.lock().unwrap() = false;
                            *interaction_active.lock().unwrap() = false;
                            listener.lock().unwrap().stop();
                        }
                        VoiceCommand::Speak(text) => {
                            if *interaction_active.lock().unwrap() {
                                continue;
                            }
                            *interaction_active.lock().unwrap() = true;

                            println!("[Voice] Processing: {}", text);

                            let response = format!("You said: {}", text);
                            listener.lock().unwrap().pause();
                            tts.lock().unwrap().speak(&response);
                            listener.lock().unwrap().resume();

                            *conversation_deadline.lock().unwrap() = current_time_secs() + 10.0;
                            *interaction_active.lock().unwrap() = false;
                        }
                        VoiceCommand::Stop => {
                            *active.lock().unwrap() = false;
                            listener.lock().unwrap().stop();
                        }
                    }
                }
            });
        }

        VoiceManager {
            active,
            interaction_active,
            conversation_deadline,
            model_path,
            listener,
            tts,
            command_tx,
        }
    }

    pub fn start_listening(&self) {
        let _ = self.command_tx.send(VoiceCommand::StartListening);
    }

    pub fn stop_listening(&self) {
        let _ = self.command_tx.send(VoiceCommand::StopListening);
    }

    pub fn speak(&self, text: &str) {
        let _ = self.command_tx.send(VoiceCommand::Speak(text.to_string()));
    }

    pub fn check_wake_word(&self, text: &str) -> bool {
        check_wake_word_static(text)
    }

    pub fn is_installed(&self) -> bool {
        let installer = VoiceInstaller::new();
        installer.is_installed()
    }

    pub fn get_voice_for_language(&self, lang_code: &str) -> String {
        let lang_code = if lang_code == "auto" { "en" } else { lang_code };
        let prefix = match lang_code {
            "en" => "en_",
            "fr" => "fr_",
            "de" => "de_",
            "es" => "es_",
            "it" => "it_",
            _ => "en_",
        };

        let home = dirs::home_dir().unwrap_or_default();
        let piper_dir = home.join(".gaia/voice/piper");

        if piper_dir.exists() {
            if let Ok(entries) = fs::read_dir(&piper_dir) {
                let mut models: Vec<String> = entries
                    .filter_map(|e| e.ok())
                    .filter_map(|e| {
                        let name = e.file_name().to_string_lossy().to_string();
                        if name.ends_with(".onnx") && name.starts_with(prefix) {
                            Some(name.trim_end_matches(".onnx").to_string())
                        } else {
                            None
                        }
                    })
                    .collect();
                models.sort();
                if let Some(model) = models.into_iter().next() {
                    return model;
                }
            }
        }

        format!("{}US-lessac-medium", prefix)
    }
}

fn check_wake_word_static(text: &str) -> bool {
    let text_lower = text.to_lowercase();
    let wake_words = [
        "hey", "hi", "hello", "ehi", "ei", "ciao", "bonjour", "salut", "hé", "hallo", "he", "hola",
        "oye",
    ];

    if text_lower.contains("hey gaia") || text_lower.contains("hey guys") {
        return true;
    }

    for w in &wake_words {
        if text_lower.starts_with(w) {
            return true;
        }
    }

    false
}

fn discover_vosk_model(gaia_voice: &PathBuf) -> Option<String> {
    let vosk_dir = gaia_voice.join("vosk");
    if !vosk_dir.exists() {
        return None;
    }

    if let Ok(entries) = fs::read_dir(&vosk_dir) {
        for entry in entries.flatten() {
            if entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                let name = entry.file_name().to_string_lossy().to_string();
                if name.contains("model") {
                    return Some(entry.path().to_string_lossy().to_string());
                }
            }
        }
    }

    None
}

fn current_time_secs() -> f64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64()
}

impl Default for VoiceManager {
    fn default() -> Self {
        Self::new()
    }
}
