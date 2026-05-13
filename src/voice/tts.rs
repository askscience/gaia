use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

pub struct PiperTTS {
    executable: PathBuf,
}

impl PiperTTS {
    pub fn new() -> Self {
        PiperTTS {
            executable: PathBuf::from("piper"),
        }
    }

    pub fn set_executable_path(&mut self, path: &Path) {
        if path.exists() {
            self.executable = path.to_path_buf();
        }
    }

    pub fn speak(&self, text: &str) {
        if text.is_empty() {
            return;
        }

        let model = self.resolve_model();
        let Some(model_path) = model else {
            println!("[PiperTTS] Error: No voice model found.");
            return;
        };

        if !Path::new(&model_path).exists() {
            println!("[PiperTTS] Error: Model file not found: {}", model_path);
            return;
        }

        println!("[PiperTTS] Speaking: '{}' using model {}", text, model_path);

        #[cfg(target_os = "macos")]
        {
            let temp_file = std::env::temp_dir().join("gaia_tts.wav");
            let result = Command::new(&self.executable)
                .arg("--model")
                .arg(&model_path)
                .arg("--output_file")
                .arg(&temp_file)
                .stdin(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .and_then(|mut child| {
                    if let Some(ref mut stdin) = child.stdin {
                        let _ = stdin.write_all(text.as_bytes());
                    }
                    child.wait()
                });

            match result {
                Ok(status) if status.success() => {
                    let _ = Command::new("afplay").arg(&temp_file).status();
                }
                Ok(_) => {
                    println!("[PiperTTS] Piper returned error.");
                }
                Err(e) => {
                    println!("[PiperTTS] Failed to run piper: {}", e);
                }
            }
        }

        #[cfg(not(target_os = "macos"))]
        {
            let piper_result = Command::new(&self.executable)
                .arg("--model")
                .arg(&model_path)
                .arg("--output_raw")
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn();

            match piper_result {
                Ok(mut piper) => {
                    if let Some(ref mut stdin) = piper.stdin {
                        let _ = stdin.write_all(text.as_bytes());
                    }

                    let aplay_result = Command::new("aplay")
                        .arg("-r")
                        .arg("22050")
                        .arg("-f")
                        .arg("S16_LE")
                        .arg("-t")
                        .arg("raw")
                        .arg("-")
                        .stdin(
                            piper
                                .stdout
                                .take()
                                .unwrap_or_else(|| std::process::Stdio::inherit()),
                        )
                        .stderr(Stdio::piped())
                        .spawn();

                    match aplay_result {
                        Ok(mut aplay) => {
                            let _ = aplay.wait();
                        }
                        Err(_) => {
                            let _ = piper.wait_with_output();
                            println!(
                                "[PiperTTS] aplay not found. You may need to install alsa-utils."
                            );
                        }
                    }
                }
                Err(e) => {
                    println!("[PiperTTS] piper not found: {}", e);
                }
            }
        }
    }

    pub fn speak_with_model(&self, text: &str, model: &str) {
        let model_path = self.resolve_model_path(model);
        if let Some(path) = model_path {
            if Path::new(&path).exists() {
                let exe = self.executable.clone();
                let path_clone = path.clone();
                let text = text.to_string();

                #[cfg(target_os = "macos")]
                {
                    let temp_file = std::env::temp_dir().join("gaia_tts.wav");
                    let _ = Command::new(&exe)
                        .arg("--model")
                        .arg(&path_clone)
                        .arg("--output_file")
                        .arg(&temp_file)
                        .stdin(Stdio::piped())
                        .spawn()
                        .and_then(|mut child| {
                            if let Some(ref mut stdin) = child.stdin {
                                let _ = stdin.write_all(text.as_bytes());
                            }
                            child.wait()
                        });
                    let _ = Command::new("afplay").arg(&temp_file).status();
                }

                #[cfg(not(target_os = "macos"))]
                {
                    let _ = Command::new(&exe)
                        .arg("--model")
                        .arg(&path_clone)
                        .arg("--output_raw")
                        .stdin(Stdio::piped())
                        .stdout(Stdio::piped())
                        .spawn()
                        .and_then(|mut child| {
                            if let Some(ref mut stdin) = child.stdin {
                                let _ = stdin.write_all(text.as_bytes());
                            }
                            let _ = child.wait();
                            Ok(())
                        });
                }
            }
        }
    }

    pub fn stop(&self) {}

    fn resolve_model(&self) -> Option<String> {
        let home = dirs::home_dir()?;
        let piper_dir = home.join(".gaia/voice/piper");

        let model = "en_US-lessac-medium";
        let possible = piper_dir.join(format!("{}.onnx", model));
        if possible.exists() {
            return Some(possible.to_string_lossy().to_string());
        }

        if let Ok(entries) = fs::read_dir(&piper_dir) {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                if name.ends_with(".onnx") {
                    return Some(entry.path().to_string_lossy().to_string());
                }
            }
        }

        None
    }

    fn resolve_model_path(&self, model: &str) -> Option<String> {
        let path = PathBuf::from(model);
        if path.exists() {
            return Some(path.to_string_lossy().to_string());
        }

        let home = dirs::home_dir()?;
        let piper_dir = home.join(".gaia/voice/piper");
        let possible = piper_dir.join(format!("{}.onnx", model));
        if possible.exists() {
            return Some(possible.to_string_lossy().to_string());
        }

        None
    }
}

impl Default for PiperTTS {
    fn default() -> Self {
        Self::new()
    }
}
