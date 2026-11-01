//! Finds Obsidian and its vaults from Obsidian's own config. Read-only; nothing is changed.

use std::path::{Path, PathBuf};

fn config_file() -> Option<PathBuf> {
    if cfg!(target_os = "macos") {
        Some(
            PathBuf::from(std::env::var_os("HOME")?)
                .join("Library/Application Support/obsidian/obsidian.json"),
        )
    } else if cfg!(windows) {
        Some(PathBuf::from(std::env::var_os("APPDATA")?).join("obsidian/obsidian.json"))
    } else {
        Some(PathBuf::from(std::env::var_os("HOME")?).join(".config/obsidian/obsidian.json"))
    }
}

pub fn installed() -> bool {
    if cfg!(target_os = "macos") {
        let home = std::env::var_os("HOME")
            .map(PathBuf::from)
            .unwrap_or_default();
        Path::new("/Applications/Obsidian.app").exists()
            || home.join("Applications/Obsidian.app").exists()
    } else if cfg!(windows) {
        std::env::var_os("LOCALAPPDATA")
            .map(PathBuf::from)
            .is_some_and(|d| {
                d.join("Programs/Obsidian/Obsidian.exe").exists()
                    || d.join("Obsidian/Obsidian.exe").exists()
            })
    } else {
        config_file().is_some_and(|c| c.exists())
    }
}

pub fn vaults() -> Vec<PathBuf> {
    let Some(text) = config_file().and_then(|f| std::fs::read_to_string(f).ok()) else {
        return vec![];
    };
    let Ok(v) = serde_json::from_str::<serde_json::Value>(&text) else {
        return vec![];
    };
    v.get("vaults")
        .and_then(|x| x.as_object())
        .map(|m| {
            m.values()
                .filter_map(|x| x.get("path")?.as_str().map(PathBuf::from))
                .collect()
        })
        .unwrap_or_default()
}

/// The registered vault that contains `path`, if any.
pub fn vault_for(path: &Path) -> Option<PathBuf> {
    vaults()
        .into_iter()
        .filter(|v| path.starts_with(v))
        .max_by_key(|v| v.components().count())
}

pub fn open_url(path: &Path) -> String {
    let mut out = String::from("obsidian://open?path=");
    for b in path.to_string_lossy().bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' | b'/' => {
                out.push(b as char)
            }
            _ => out.push_str(&format!("%{b:02X}")),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    #[test]
    fn url_is_encoded() {
        let u = super::open_url(std::path::Path::new("/a b/Project Map.canvas"));
        assert_eq!(u, "obsidian://open?path=/a%20b/Project%20Map.canvas");
    }
}
