use std::fs;
use std::path::{Path, PathBuf};

pub struct VoiceInstaller {
    base_dir: PathBuf,
    vosk_dir: PathBuf,
    piper_dir: PathBuf,
}

impl VoiceInstaller {
    pub fn new() -> Self {
        let home = dirs::home_dir().unwrap_or_default();
        let base_dir = home.join(".gaia/voice");
        let vosk_dir = base_dir.join("vosk");
        let piper_dir = base_dir.join("piper");

        VoiceInstaller {
            base_dir,
            vosk_dir,
            piper_dir,
        }
    }

    pub fn install_piper(&self) -> Result<(), String> {
        let _ = fs::create_dir_all(&self.piper_dir);

        let piper_bin = self.piper_dir.join("piper/piper");
        if piper_bin.exists() {
            println!(
                "[VoiceInstaller] Piper already installed at {:?}",
                piper_bin
            );
        } else {
            println!(
                "[VoiceInstaller] Piper binary not found. Download it from: \
                 https://github.com/rhasspy/piper/releases"
            );
            println!("[VoiceInstaller] Expected location: {:?}", piper_bin);
        }

        let en_model = self.piper_dir.join("en_US-lessac-medium.onnx");
        if !en_model.exists() {
            println!(
                "[VoiceInstaller] Voice model not found: {:?}. \
                 Download from https://huggingface.co/rhasspy/piper-voices",
                en_model
            );
        }

        Ok(())
    }

    pub fn install_vosk(&self, lang: &str) -> Result<(), String> {
        let _ = fs::create_dir_all(&self.vosk_dir);

        let vosk_urls: Vec<(&str, &str)> = vec![
            (
                "en",
                "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
            ),
            (
                "fr",
                "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip",
            ),
            (
                "de",
                "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip",
            ),
            (
                "es",
                "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
            ),
            (
                "it",
                "https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip",
            ),
        ];

        if let Ok(entries) = fs::read_dir(&self.vosk_dir) {
            for entry in entries.flatten() {
                if entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                    let name = entry.file_name().to_string_lossy().to_string();
                    if name.contains("model") && name.contains(&format!("-{}", lang)) {
                        println!(
                            "[VoiceInstaller] Vosk model for {} already installed: {}",
                            lang, name
                        );
                        return Ok(());
                    }
                }
            }
        }

        for (code, url) in &vosk_urls {
            if *code == lang {
                println!(
                    "[VoiceInstaller] To install Vosk model for {}, download from: {}",
                    lang, url
                );
                println!("[VoiceInstaller] Extract the zip to: {:?}", self.vosk_dir);
            }
        }

        Ok(())
    }

    pub fn is_installed(&self) -> bool {
        let piper_bin = self.piper_dir.join("piper/piper");
        if !piper_bin.exists() {
            return false;
        }

        if self.vosk_dir.exists() {
            if let Ok(entries) = fs::read_dir(&self.vosk_dir) {
                for entry in entries.flatten() {
                    if entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                        let name = entry.file_name().to_string_lossy().to_string();
                        if name.contains("model") {
                            return true;
                        }
                    }
                }
            }
        }

        false
    }

    pub fn check_status(&self) -> VoiceInstallStatus {
        let piper_bin = self.piper_dir.join("piper/piper");
        let has_piper = piper_bin.exists();

        let mut vosk_models: Vec<String> = Vec::new();
        if self.vosk_dir.exists() {
            if let Ok(entries) = fs::read_dir(&self.vosk_dir) {
                for entry in entries.flatten() {
                    if entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                        let name = entry.file_name().to_string_lossy().to_string();
                        if name.contains("model") {
                            vosk_models.push(name);
                        }
                    }
                }
            }
        }

        let mut piper_voices: Vec<String> = Vec::new();
        if self.piper_dir.exists() {
            if let Ok(entries) = fs::read_dir(&self.piper_dir) {
                for entry in entries.flatten() {
                    if entry.file_type().map(|t| t.is_file()).unwrap_or(false) {
                        let name = entry.file_name().to_string_lossy().to_string();
                        if name.ends_with(".onnx") {
                            piper_voices.push(name.trim_end_matches(".onnx").to_string());
                        }
                    }
                }
            }
        }

        VoiceInstallStatus {
            piper_bin: has_piper,
            vosk_models,
            piper_voices,
        }
    }
}

#[derive(Debug)]
pub struct VoiceInstallStatus {
    pub piper_bin: bool,
    pub vosk_models: Vec<String>,
    pub piper_voices: Vec<String>,
}

impl Default for VoiceInstaller {
    fn default() -> Self {
        Self::new()
    }
}
