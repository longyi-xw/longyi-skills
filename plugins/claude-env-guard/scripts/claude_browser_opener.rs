#![windows_subsystem = "windows"]

use std::env;
use std::fs;
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::{Command, Stdio};

const DETACHED_PROCESS: u32 = 0x0000_0008;
const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;

fn main() {
    let url = match env::args_os().nth(1).and_then(|s| s.into_string().ok()) {
        Some(u) => u,
        None => std::process::exit(1),
    };

    let lower = url.to_ascii_lowercase();
    if !(lower.starts_with("https://") || lower.starts_with("http://")) {
        std::process::exit(1);
    }

    let default_chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe".to_string();
    let chrome = env::var("CLAUDE_GUARD_CHROME")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or(default_chrome);

    if !Path::new(&chrome).exists() {
        std::process::exit(1);
    }

    let default_profile = env::var("USERPROFILE")
        .map(|h| format!(r"{h}\.claude-chrome-profile"))
        .unwrap_or_else(|_| r"C:\Users\Public\.claude-chrome-profile".to_string());
    let profile_dir = env::var("CLAUDE_GUARD_PROFILE")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or(default_profile);

    let proxy = env::var("CLAUDE_GUARD_PROXY")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or_else(|| "http://127.0.0.1:7897".to_string());

    if fs::create_dir_all(&profile_dir).is_err() {
        std::process::exit(1);
    }

    let child = Command::new(&chrome)
        .arg(format!("--user-data-dir={profile_dir}"))
        .arg(format!("--proxy-server={proxy}"))
        .arg("--lang=en-US")
        .arg("--force-webrtc-ip-handling-policy=disable_non_proxied_udp")
        .arg("--enforce-webrtc-ip-permission-check")
        .arg("--no-first-run")
        .arg(&url)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .creation_flags(DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
        .spawn();

    match child {
        Ok(_) => std::process::exit(0),
        Err(_) => std::process::exit(1),
    }
}
