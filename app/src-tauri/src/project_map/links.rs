//! Deterministic reference extraction. Only references that resolve to an indexed file become
//! connections; nothing is guessed from names alone.

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::sync::LazyLock;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum Kind {
    /// Wikilinks, embeds and Markdown links written by a person.
    Explicit,
    /// Code/config references the toolchain itself resolves (imports, `mod`, `include_str!`).
    Dependency,
    /// A path mentioned in backticks in prose. Real file, but not a hard link.
    Inferred,
}

/// A reference as written in a file, before resolution.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct RawRef {
    pub target: String,
    pub kind: Kind,
    pub label: String,
    /// How to resolve `target`.
    pub style: Style,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Style {
    /// Obsidian wikilink: exact path, path + ".md", or unique file name.
    Wiki,
    /// Relative to the referring file's folder.
    Relative,
    /// Relative to the referring file's folder, trying code extensions.
    Module,
    /// Rust `mod name;`.
    RustMod,
    /// Relative to the project root.
    Root,
}

macro_rules! re {
    ($name:ident, $pat:expr) => {
        static $name: LazyLock<Regex> = LazyLock::new(|| Regex::new($pat).unwrap());
    };
}

re!(
    WIKI,
    r"(!?)\[\[([^\]\|#\^]+)(?:[#\^][^\]\|]*)?(?:\|[^\]]*)?\]\]"
);
re!(MDLINK, r#"(!?)\[[^\]]*\]\(<?([^)\s>]+)>?(?:\s+"[^"]*")?\)"#);
re!(BACKTICK, r"`([A-Za-z0-9_.\-/ ]+\.[A-Za-z0-9]{1,8})`");
re!(
    JS_FROM,
    r#"(?:import|export)\s[^'";]*?from\s*['"](\.{1,2}/[^'"]+)['"]"#
);
re!(
    JS_BARE,
    r#"(?:import|require)\s*\(?\s*['"](\.{1,2}/[^'"]+)['"]"#
);
re!(
    RS_MOD,
    r"(?m)^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+([a-z_][a-z0-9_]*)\s*;"
);
re!(RS_INCLUDE, r#"include_(?:str|bytes)!\(\s*"([^"]+)"\s*\)"#);
re!(HTML_SRC, r#"(?:src|href)\s*=\s*["']([^"'#?]+)["']"#);
re!(CSS_IMPORT, r#"@import\s+(?:url\()?\s*['"]([^'"]+)['"]"#);

fn is_url(s: &str) -> bool {
    s.contains("://") || s.starts_with("mailto:") || s.starts_with('#') || s.starts_with("data:")
}

fn push(out: &mut Vec<RawRef>, target: &str, kind: Kind, label: &str, style: Style) {
    let t = target.trim();
    if !t.is_empty() && !is_url(t) {
        out.push(RawRef {
            target: t.to_string(),
            kind,
            label: label.to_string(),
            style,
        });
    }
}

/// Extracts references from a text file. `ext` is lowercase without the dot.
pub fn extract(ext: &str, content: &str) -> Vec<RawRef> {
    let mut out = Vec::new();
    match ext {
        "md" | "markdown" | "canvas" => {
            for c in WIKI.captures_iter(content) {
                let label = if &c[1] == "!" { "embeds" } else { "links to" };
                push(&mut out, &c[2], Kind::Explicit, label, Style::Wiki);
            }
            for c in MDLINK.captures_iter(content) {
                let label = if &c[1] == "!" { "embeds" } else { "links to" };
                let target = percent_decode(&c[2]);
                push(&mut out, &target, Kind::Explicit, label, Style::Relative);
            }
            for c in BACKTICK.captures_iter(content) {
                push(&mut out, &c[1], Kind::Inferred, "mentions", Style::Root);
                push(&mut out, &c[1], Kind::Inferred, "mentions", Style::Relative);
            }
        }
        "js" | "jsx" | "ts" | "tsx" | "mjs" | "cjs" => {
            for c in JS_FROM
                .captures_iter(content)
                .chain(JS_BARE.captures_iter(content))
            {
                push(&mut out, &c[1], Kind::Dependency, "imports", Style::Module);
            }
        }
        "rs" => {
            for c in RS_MOD.captures_iter(content) {
                push(
                    &mut out,
                    &c[1],
                    Kind::Dependency,
                    "declares module",
                    Style::RustMod,
                );
            }
            for c in RS_INCLUDE.captures_iter(content) {
                push(
                    &mut out,
                    &c[1],
                    Kind::Dependency,
                    "includes",
                    Style::Relative,
                );
            }
        }
        "html" | "htm" => {
            for c in HTML_SRC.captures_iter(content) {
                let t = c[1].trim_start_matches('/');
                push(&mut out, t, Kind::Dependency, "loads", Style::Relative);
            }
        }
        "css" => {
            for c in CSS_IMPORT.captures_iter(content) {
                push(
                    &mut out,
                    &c[1],
                    Kind::Dependency,
                    "imports",
                    Style::Relative,
                );
            }
        }
        _ => {}
    }
    let mut seen = HashSet::new();
    out.retain(|r| seen.insert(r.clone()));
    out
}

fn percent_decode(s: &str) -> String {
    let b = s.as_bytes();
    let mut out = Vec::with_capacity(b.len());
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'%' && i + 2 < b.len() {
            if let Some(v) = s
                .get(i + 1..i + 3)
                .and_then(|h| u8::from_str_radix(h, 16).ok())
            {
                out.push(v);
                i += 3;
                continue;
            }
        }
        out.push(b[i]);
        i += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

/// Joins `rel` onto `dir` and normalises `.`/`..`. None if it escapes the root.
pub fn join_rel(dir: &str, rel: &str) -> Option<String> {
    let mut parts: Vec<&str> = if dir.is_empty() {
        vec![]
    } else {
        dir.split('/').collect()
    };
    for seg in rel.split('/') {
        match seg {
            "" | "." => {}
            ".." => {
                parts.pop()?;
            }
            s => parts.push(s),
        }
    }
    Some(parts.join("/"))
}

pub fn parent(path: &str) -> &str {
    path.rfind('/').map(|i| &path[..i]).unwrap_or("")
}

/// Lookup tables for resolution, built once per index pass.
pub struct Resolver<'a> {
    files: &'a HashSet<String>,
    by_name: HashMap<String, Vec<&'a str>>,
}

impl<'a> Resolver<'a> {
    pub fn new(files: &'a HashSet<String>) -> Self {
        let mut by_name: HashMap<String, Vec<&str>> = HashMap::new();
        for f in files {
            let name = f.rsplit('/').next().unwrap_or(f);
            by_name.entry(name.to_lowercase()).or_default().push(f);
            if let Some(stem) = name.strip_suffix(".md") {
                by_name.entry(stem.to_lowercase()).or_default().push(f);
            }
        }
        Resolver { files, by_name }
    }

    fn exists(&self, p: &str) -> Option<String> {
        self.files.contains(p).then(|| p.to_string())
    }

    pub fn resolve(&self, from: &str, r: &RawRef) -> Option<String> {
        let dir = parent(from);
        let found = match r.style {
            Style::Wiki => {
                let t = r.target.trim_start_matches('/');
                self.exists(t)
                    .or_else(|| self.exists(&format!("{t}.md")))
                    .or_else(|| {
                        let name = t.rsplit('/').next()?.to_lowercase();
                        match self.by_name.get(&name).map(|v| v.as_slice()) {
                            Some([only]) => Some(only.to_string()),
                            _ => None,
                        }
                    })
            }
            Style::Relative => join_rel(dir, &r.target).and_then(|p| self.exists(&p)),
            Style::Root => join_rel("", &r.target).and_then(|p| self.exists(&p)),
            Style::Module => {
                let base = join_rel(dir, &r.target)?;
                [
                    "",
                    ".ts",
                    ".tsx",
                    ".js",
                    ".jsx",
                    ".mjs",
                    ".json",
                    ".css",
                    "/index.ts",
                    "/index.tsx",
                    "/index.js",
                ]
                .iter()
                .find_map(|ext| self.exists(&format!("{base}{ext}")))
            }
            Style::RustMod => {
                let name = from.rsplit('/').next().unwrap_or(from);
                let mod_dir = if matches!(name, "main.rs" | "lib.rs" | "mod.rs") {
                    dir.to_string()
                } else {
                    join_rel(dir, name.trim_end_matches(".rs"))?
                };
                let base = join_rel(&mod_dir, &r.target)?;
                self.exists(&format!("{base}.rs"))
                    .or_else(|| self.exists(&format!("{base}/mod.rs")))
            }
        };
        found.filter(|t| t != from)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn set(files: &[&str]) -> HashSet<String> {
        files.iter().map(|s| s.to_string()).collect()
    }

    fn resolved(
        from: &str,
        ext: &str,
        content: &str,
        files: &HashSet<String>,
    ) -> Vec<(String, Kind, String)> {
        let r = Resolver::new(files);
        let mut v: Vec<_> = extract(ext, content)
            .iter()
            .filter_map(|x| r.resolve(from, x).map(|t| (t, x.kind, x.label.clone())))
            .collect();
        v.sort_by(|a, b| a.0.cmp(&b.0));
        v.dedup();
        v
    }

    #[test]
    fn markdown_links_embeds_and_mentions() {
        let files = set(&[
            "notes/a.md",
            "notes/b.md",
            "img/chart.png",
            "research/registry.md",
            "docs/x.md",
        ]);
        let md = "See [[b]] and ![[chart.png]] and [x](../docs/x.md) and `research/registry.md`. \
                  [web](https://example.com) [[missing]]";
        let got = resolved("notes/a.md", "md", md, &files);
        assert_eq!(
            got,
            vec![
                ("docs/x.md".into(), Kind::Explicit, "links to".into()),
                ("img/chart.png".into(), Kind::Explicit, "embeds".into()),
                ("notes/b.md".into(), Kind::Explicit, "links to".into()),
                (
                    "research/registry.md".into(),
                    Kind::Inferred,
                    "mentions".into()
                ),
            ]
        );
    }

    #[test]
    fn ambiguous_wikilink_is_not_guessed() {
        let files = set(&["a/note.md", "b/note.md", "c/me.md"]);
        assert!(resolved("c/me.md", "md", "[[note]]", &files).is_empty());
        assert_eq!(resolved("c/me.md", "md", "[[a/note]]", &files).len(), 1);
    }

    #[test]
    fn code_references() {
        let files = set(&[
            "app/src/App.tsx",
            "app/src/desktop.tsx",
            "app/src/styles.css",
            "app/index.html",
            "app/src/main.tsx",
        ]);
        let tsx = "import { x } from \"./desktop\";\nimport \"./styles.css\";\nimport React from 'react';";
        let got = resolved("app/src/App.tsx", "tsx", tsx, &files);
        assert_eq!(got.len(), 2);
        assert!(got.iter().all(|g| g.1 == Kind::Dependency));
        let html = r#"<script type="module" src="/src/main.tsx"></script>"#;
        assert_eq!(
            resolved("app/index.html", "html", html, &files)[0].0,
            "app/src/main.tsx"
        );
    }

    #[test]
    fn rust_modules_and_includes() {
        let files = set(&[
            "s/src/main.rs",
            "s/src/db.rs",
            "s/src/pm/mod.rs",
            "s/src/pm/links.rs",
            "s/Cargo.toml",
        ]);
        let main = "mod db;\npub mod pm;\nconst C: &str = include_str!(\"../Cargo.toml\");";
        let got: Vec<String> = resolved("s/src/main.rs", "rs", main, &files)
            .into_iter()
            .map(|g| g.0)
            .collect();
        assert_eq!(got, vec!["s/Cargo.toml", "s/src/db.rs", "s/src/pm/mod.rs"]);
        let got = resolved("s/src/pm/mod.rs", "rs", "mod links;", &files);
        assert_eq!(got[0].0, "s/src/pm/links.rs");
    }

    #[test]
    fn paths_cannot_escape_root() {
        assert_eq!(join_rel("a", "../../x"), None);
        assert_eq!(join_rel("a/b", "../c/./d.md").as_deref(), Some("a/c/d.md"));
    }
}
