//! Walks the project folder and decides what belongs on the map. Respects `.gitignore` and an
//! optional `.tradergomapignore` (same syntax). Secrets, dependencies, build output and the
//! map's own files are always excluded, whatever the ignore files say.

use super::links::{self, RawRef};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::path::Path;
use std::time::UNIX_EPOCH;

pub const MAP_FILE: &str = "Project Map.canvas";
pub const CUSTOM_IGNORE: &str = ".tradergomapignore";
const MAX_PARSE_BYTES: u64 = 512 * 1024;

/// Folder names never walked into.
const EXCLUDED_DIRS: &[&str] = &[
    ".git",
    "node_modules",
    "target",
    "dist",
    "gen",
    ".obsidian",
    ".trash",
    "__pycache__",
    ".venv",
    "venv",
    ".cache",
    ".next",
    ".turbo",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
];

const TEXT_EXT: &[&str] = &[
    "md", "markdown", "txt", "rs", "ts", "tsx", "js", "jsx", "mjs", "cjs", "json", "toml", "yml",
    "yaml", "html", "htm", "css", "py", "sh", "csv", "canvas", "base", "svg", "xml", "ini", "cfg",
    "lock",
];

/// True for files that may hold credentials. Never indexed, previewed or exported.
pub fn is_secret_name(name: &str) -> bool {
    let n = name.to_lowercase();
    n == ".env"
        || n.starts_with(".env.")
        || n.ends_with(".pem")
        || n.ends_with(".key")
        || n.ends_with(".p12")
        || n.ends_with(".pfx")
        || n.ends_with(".keystore")
        || n.ends_with(".jks")
        || n.starts_with("id_rsa")
        || n.starts_with("id_ed25519")
        || n.starts_with("credentials")
        || n.starts_with("secrets")
        || n == ".npmrc"
        || n == ".netrc"
}

/// The map file, its temp files and saved copies are generated output.
pub fn is_generated_name(name: &str) -> bool {
    (name.starts_with("Project Map") && name.ends_with(".canvas")) || name.contains(".canvas.tmp-")
}

pub fn is_excluded_dir(name: &str) -> bool {
    EXCLUDED_DIRS.contains(&name)
}

/// Quick path check used to drop watcher events without walking.
pub fn is_excluded_rel(rel: &str) -> bool {
    let mut parts = rel.split('/').peekable();
    while let Some(p) = parts.next() {
        if parts.peek().is_none() {
            return is_secret_name(p) || is_generated_name(p);
        }
        if is_excluded_dir(p) {
            return true;
        }
    }
    false
}

pub fn is_text(rel: &str) -> bool {
    ext_of(rel).is_some_and(|e| TEXT_EXT.contains(&e.as_str()))
}

pub fn ext_of(rel: &str) -> Option<String> {
    let name = rel.rsplit('/').next()?;
    let (_, ext) = name.rsplit_once('.')?;
    Some(ext.to_lowercase())
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Entry {
    pub size: u64,
    pub mtime_ms: u128,
    pub hash: String,
    pub refs: Vec<RawRef>,
}

/// Walks `root`. Files unchanged since `cache` (same size and mtime) are not re-read.
pub fn scan(
    root: &Path,
    cache: &BTreeMap<String, Entry>,
) -> std::io::Result<BTreeMap<String, Entry>> {
    if !root.is_dir() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "project folder is not available",
        ));
    }
    let walker = ignore::WalkBuilder::new(root)
        .hidden(false)
        .git_ignore(true)
        .git_global(false)
        .git_exclude(false)
        .require_git(false)
        .parents(false)
        .add_custom_ignore_filename(CUSTOM_IGNORE)
        .filter_entry(|e| {
            let name = e.file_name().to_string_lossy();
            if e.file_type().is_some_and(|t| t.is_dir()) {
                !is_excluded_dir(&name)
            } else {
                !is_secret_name(&name) && !is_generated_name(&name)
            }
        })
        .build();

    let mut out = BTreeMap::new();
    for item in walker {
        let Ok(entry) = item else { continue };
        if !entry.file_type().is_some_and(|t| t.is_file()) {
            continue;
        }
        let path = entry.path();
        let Ok(rel) = path.strip_prefix(root) else {
            continue;
        };
        let rel = rel.to_string_lossy().replace('\\', "/");
        let Ok(meta) = entry.metadata() else { continue };
        let mtime_ms = meta
            .modified()
            .ok()
            .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
            .map(|d| d.as_millis())
            .unwrap_or(0);
        if let Some(old) = cache.get(&rel) {
            if old.size == meta.len() && old.mtime_ms == mtime_ms {
                out.insert(rel, old.clone());
                continue;
            }
        }
        let Ok(bytes) = std::fs::read(path) else {
            continue;
        };
        let hash = hex(&Sha256::digest(&bytes)[..12]);
        let refs = if is_text(&rel) && meta.len() <= MAX_PARSE_BYTES {
            match std::str::from_utf8(&bytes) {
                Ok(text) => links::extract(&ext_of(&rel).unwrap_or_default(), text),
                Err(_) => Vec::new(),
            }
        } else {
            Vec::new()
        };
        out.insert(
            rel,
            Entry {
                size: meta.len(),
                mtime_ms,
                hash,
                refs,
            },
        );
    }
    Ok(out)
}

pub fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

/// Hides values that look like credentials before text leaves the backend.
pub fn redact(text: &str) -> String {
    use regex::Regex;
    use std::sync::LazyLock;
    static PEM: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")
            .unwrap()
    });
    static ASSIGN: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r#"(?i)\b([a-z0-9_\-]*(?:api[_-]?key|secret|token|password|passwd|private[_-]?key)[a-z0-9_\-]*)(["']?\s*[:=]\s*["']?)([^\s"',;]{4,})"#).unwrap()
    });
    static TOKENS: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9\-_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b").unwrap()
    });
    let t = PEM.replace_all(text, "[private key redacted]");
    let t = ASSIGN.replace_all(&t, "$1$2••••");
    TOKENS.replace_all(&t, "••••").into_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exclusions() {
        for p in [
            ".env",
            "app/.env.local",
            "keys/updater.key",
            "a/node_modules/x.js",
            "app/src-tauri/target/x",
            ".git/HEAD",
            "research/.obsidian/app.json",
            "Project Map.canvas",
            "Project Map (copy 1).canvas",
            "x.canvas.tmp-12",
        ] {
            assert!(is_excluded_rel(p), "{p} should be excluded");
        }
        for p in [
            "CLAUDE.md",
            "app/src/App.tsx",
            "research/TraderGO/note.md",
            "other.canvas",
        ] {
            assert!(!is_excluded_rel(p), "{p} should be included");
        }
    }

    #[test]
    fn scan_respects_ignores_and_skips_secrets() {
        let dir = tempfile::tempdir().unwrap();
        let r = dir.path();
        std::fs::create_dir_all(r.join("notes")).unwrap();
        std::fs::create_dir_all(r.join("node_modules/pkg")).unwrap();
        std::fs::write(r.join("notes/a.md"), "[[b]]").unwrap();
        std::fs::write(r.join("notes/b.md"), "hi").unwrap();
        std::fs::write(r.join(".env"), "API_KEY=supersecret").unwrap();
        std::fs::write(r.join("node_modules/pkg/i.js"), "").unwrap();
        std::fs::write(r.join("ignored.log"), "").unwrap();
        std::fs::write(r.join(".gitignore"), "*.log\n").unwrap();
        std::fs::write(r.join(CUSTOM_IGNORE), "notes/b.md\n").unwrap();
        std::fs::write(r.join(MAP_FILE), "{}").unwrap();
        let idx = scan(r, &BTreeMap::new()).unwrap();
        let keys: Vec<&str> = idx.keys().map(|s| s.as_str()).collect();
        assert_eq!(keys, vec![".gitignore", CUSTOM_IGNORE, "notes/a.md"]);
        assert_eq!(idx["notes/a.md"].refs.len(), 1);
    }

    #[test]
    fn unchanged_files_come_from_cache() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("a.md"), "x").unwrap();
        let first = scan(dir.path(), &BTreeMap::new()).unwrap();
        let mut cache = first.clone();
        cache.get_mut("a.md").unwrap().hash = "from-cache".into();
        let second = scan(dir.path(), &cache).unwrap();
        assert_eq!(second["a.md"].hash, "from-cache");
    }

    #[test]
    fn secrets_are_redacted() {
        let t = "API_KEY=abcd1234efgh\npassword: \"hunter22\"\ntoken ghp_abcdefghijklmnopqrstuvwxyz123456\n\
                 -----BEGIN PRIVATE KEY-----\nMIIE\n-----END PRIVATE KEY-----\nnormal text";
        let r = redact(t);
        for leaked in ["abcd1234efgh", "hunter22", "ghp_abcdef", "MIIE"] {
            assert!(!r.contains(leaked), "{leaked} leaked: {r}");
        }
        assert!(r.contains("normal text") && r.contains("API_KEY"));
    }
}
