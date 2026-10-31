//! One project folder: index it, merge into `Project Map.canvas`, save edits safely.
//! Pure file logic with no Tauri types, so it can be tested directly.

use super::canvas::{self, Edge, Layout};
use super::index::{self, Entry, MAP_FILE};
use super::links::Resolver;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

const PREVIEW_BYTES: usize = 64 * 1024;

#[derive(Debug, Default, Serialize, Deserialize)]
struct Persisted {
    root: String,
    index: BTreeMap<String, Entry>,
    layout: Layout,
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct Summary {
    pub files: usize,
    pub edges: usize,
    pub unconnected: usize,
    pub renamed: usize,
    pub written: bool,
    /// Files modified in the last moments; the caller re-checks them shortly.
    pub settling: bool,
}

#[derive(Debug, Serialize)]
pub struct LinkInfo {
    pub path: String,
    pub kind: super::links::Kind,
    pub label: String,
    pub outgoing: bool,
}

#[derive(Debug, Serialize)]
pub struct Preview {
    pub path: String,
    pub size: u64,
    pub text: Option<String>,
    pub truncated: bool,
    pub links: Vec<LinkInfo>,
}

#[derive(Debug, thiserror::Error)]
pub enum MapError {
    #[error("{0}")]
    Msg(String),
    #[error("Kartan har ändrats utanför Trader_go (t.ex. i Obsidian) sedan den lästes in.")]
    Conflict,
}

impl From<std::io::Error> for MapError {
    fn from(e: std::io::Error) -> Self {
        MapError::Msg(e.to_string())
    }
}

pub fn sha(bytes: &[u8]) -> String {
    index::hex(&Sha256::digest(bytes))
}

/// Write to a temp file in the same folder, flush, then rename over the target.
pub fn atomic_write(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    use std::io::Write;
    let name = path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("map.canvas");
    let tmp = path.with_file_name(format!("{name}.tmp-{}", std::process::id()));
    {
        let mut f = std::fs::File::create(&tmp)?;
        f.write_all(bytes)?;
        f.sync_all()?;
    }
    std::fs::rename(&tmp, path).inspect_err(|_| {
        let _ = std::fs::remove_file(&tmp);
    })
}

pub fn to_bytes(doc: &Value) -> Vec<u8> {
    let mut b = serde_json::to_vec_pretty(doc).unwrap_or_default();
    b.push(b'\n');
    b
}

pub struct Engine {
    root: PathBuf,
    meta_path: PathBuf,
    state: Persisted,
    last_written: Option<String>,
}

impl Engine {
    /// `meta_dir` holds the app's own index (never inside the project).
    pub fn open(root: &Path, meta_dir: &Path) -> Self {
        let key = sha(root.to_string_lossy().as_bytes());
        let meta_path = meta_dir.join(format!("project-map-{}.json", &key[..16]));
        let state = std::fs::read(&meta_path)
            .ok()
            .and_then(|b| serde_json::from_slice::<Persisted>(&b).ok())
            .filter(|p| p.root == root.to_string_lossy())
            .unwrap_or_else(|| Persisted {
                root: root.to_string_lossy().into(),
                ..Default::default()
            });
        Engine {
            root: root.to_path_buf(),
            meta_path,
            state,
            last_written: None,
        }
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn canvas_path(&self) -> PathBuf {
        self.root.join(MAP_FILE)
    }

    /// True if the map file on disk is what this app last wrote.
    pub fn is_own_write(&self) -> bool {
        let disk = std::fs::read(self.canvas_path()).ok().map(|b| sha(&b));
        disk.is_some() && disk == self.last_written
    }

    fn read_canvas(&self) -> Result<(Value, Option<String>), MapError> {
        match std::fs::read(self.canvas_path()) {
            Ok(bytes) => {
                let v: Value = serde_json::from_slice(&bytes).map_err(|e| {
                    MapError::Msg(format!(
                        "{MAP_FILE} är inte giltig JSON ({e}). Den skrivs inte över; rätta eller ta bort filen."
                    ))
                })?;
                Ok((v, Some(sha(&bytes))))
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok((serde_json::json!({}), None)),
            Err(e) => Err(e.into()),
        }
    }

    fn edges(index: &BTreeMap<String, Entry>) -> Vec<Edge> {
        let files: HashSet<String> = index.keys().cloned().collect();
        let r = Resolver::new(&files);
        let mut out = BTreeSet::new();
        for (from, e) in index {
            for raw in &e.refs {
                if let Some(to) = r.resolve(from, raw) {
                    out.insert(Edge {
                        from: from.clone(),
                        to,
                        kind: raw.kind,
                        label: raw.label.clone(),
                    });
                }
            }
        }
        // A file both linked and mentioned keeps only the strongest connection.
        let strongest: HashMap<(String, String), super::links::Kind> =
            out.iter().fold(HashMap::new(), |mut m, e| {
                let k = m.entry((e.from.clone(), e.to.clone())).or_insert(e.kind);
                *k = (*k).min(e.kind);
                m
            });
        out.into_iter()
            .filter(|e| strongest[&(e.from.clone(), e.to.clone())] == e.kind)
            .collect()
    }

    /// Full pass: scan, detect renames, rebuild connections, merge, write if anything changed.
    pub fn reconcile(&mut self, hints: &[(String, String)]) -> Result<Summary, MapError> {
        let new_index = index::scan(&self.root, &self.state.index).map_err(|_| {
            MapError::Msg("Projektmappen är inte tillgänglig just nu. Försöker igen.".into())
        })?;

        let removed: Vec<&String> = self
            .state
            .index
            .keys()
            .filter(|k| !new_index.contains_key(*k))
            .collect();
        let added: Vec<&String> = new_index
            .keys()
            .filter(|k| !self.state.index.contains_key(*k))
            .collect();
        let mut renames: Vec<(String, String)> = Vec::new();
        for (a, b) in hints {
            if removed.contains(&a) && added.contains(&b) {
                renames.push((a.clone(), b.clone()));
            }
        }
        let by_hash = |m: &BTreeMap<String, Entry>, keys: &[&String]| {
            let mut h: HashMap<String, Vec<String>> = HashMap::new();
            for k in keys {
                h.entry(m[*k].hash.clone()).or_default().push((*k).clone());
            }
            h
        };
        let old_h = by_hash(&self.state.index, &removed);
        let new_h = by_hash(&new_index, &added);
        for (hash, olds) in &old_h {
            if let (Some(news), [old]) = (new_h.get(hash), olds.as_slice()) {
                if let [new] = news.as_slice() {
                    if !renames.iter().any(|(a, b)| a == old || b == new) {
                        renames.push((old.clone(), new.clone()));
                    }
                }
            }
        }

        let edges = Self::edges(&new_index);
        let files: BTreeSet<String> = new_index.keys().cloned().collect();
        let mut written = false;
        for _attempt in 0..3 {
            let (disk, disk_hash) = self.read_canvas()?;
            let mut layout = self.state.layout.clone();
            let merged = canvas::merge(&disk, &files, &edges, &renames, &mut layout);
            if merged != disk || disk_hash.is_none() {
                let bytes = to_bytes(&merged);
                // Someone changed the file while we merged: start over from their version.
                let now = std::fs::read(self.canvas_path()).ok().map(|b| sha(&b));
                if now != disk_hash {
                    continue;
                }
                atomic_write(&self.canvas_path(), &bytes)?;
                self.last_written = Some(sha(&bytes));
                written = true;
            } else if self.last_written.is_none() {
                self.last_written = disk_hash;
            }
            self.state.layout = layout;
            break;
        }

        let now_ms = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_millis())
            .unwrap_or(0);
        let settling = new_index
            .values()
            .any(|e| now_ms.saturating_sub(e.mtime_ms) < 1500);
        let connected: HashSet<&str> = edges
            .iter()
            .flat_map(|e| [e.from.as_str(), e.to.as_str()])
            .collect();
        let summary = Summary {
            files: files.len(),
            edges: edges.len(),
            unconnected: files
                .iter()
                .filter(|f| !connected.contains(f.as_str()))
                .count(),
            renamed: renames.len(),
            written,
            settling,
        };
        self.state.index = new_index;
        self.persist();
        Ok(summary)
    }

    fn persist(&self) {
        if let Some(dir) = self.meta_path.parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        if let Ok(b) = serde_json::to_vec(&self.state) {
            let _ = atomic_write(&self.meta_path, &b);
        }
    }

    pub fn load(&mut self) -> Result<(Value, String), MapError> {
        let (doc, hash) = self.read_canvas()?;
        Ok((doc, hash.unwrap_or_default()))
    }

    /// Saves an edit from the UI only if the file is unchanged since the UI loaded it.
    pub fn save(&mut self, doc: &Value, base_hash: &str) -> Result<String, MapError> {
        validate_canvas(doc)?;
        let disk = std::fs::read(self.canvas_path())
            .ok()
            .map(|b| sha(&b))
            .unwrap_or_default();
        if disk != base_hash {
            return Err(MapError::Conflict);
        }
        let bytes = to_bytes(doc);
        atomic_write(&self.canvas_path(), &bytes)?;
        let h = sha(&bytes);
        self.last_written = Some(h.clone());
        Ok(h)
    }

    /// Writes `doc` next to the map as a timestamped copy and returns its name.
    pub fn save_copy(&self, doc: &Value) -> Result<String, MapError> {
        validate_canvas(doc)?;
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        let name = format!("Project Map (copy {stamp}).canvas");
        atomic_write(&self.root.join(&name), &to_bytes(doc))?;
        Ok(name)
    }

    /// Resolves a map path to an indexed file inside the root. Nothing else can be read.
    pub fn resolve_file(&self, rel: &str) -> Result<PathBuf, MapError> {
        let denied = || MapError::Msg("Filen finns inte i projektkartan.".into());
        if !self.state.index.contains_key(rel) || rel.split('/').any(|p| p == "..") {
            return Err(denied());
        }
        let root = self.root.canonicalize()?;
        let full = root.join(rel).canonicalize().map_err(|_| denied())?;
        if !full.starts_with(&root) {
            return Err(denied());
        }
        Ok(full)
    }

    pub fn preview(&self, rel: &str) -> Result<Preview, MapError> {
        let full = self.resolve_file(rel)?;
        let size = std::fs::metadata(&full)?.len();
        let (text, truncated) = if index::is_text(rel) {
            let bytes = std::fs::read(&full)?;
            let cut = bytes.len().min(PREVIEW_BYTES);
            match std::str::from_utf8(&bytes[..cut]) {
                Ok(t) => (Some(index::redact(t)), bytes.len() > cut),
                Err(e) => (
                    Some(index::redact(&String::from_utf8_lossy(
                        &bytes[..e.valid_up_to()],
                    ))),
                    true,
                ),
            }
        } else {
            (None, false)
        };
        let edges = Self::edges(&self.state.index);
        let links = edges
            .into_iter()
            .filter_map(|e| {
                if e.from == rel {
                    Some(LinkInfo {
                        path: e.to,
                        kind: e.kind,
                        label: e.label,
                        outgoing: true,
                    })
                } else if e.to == rel {
                    Some(LinkInfo {
                        path: e.from,
                        kind: e.kind,
                        label: e.label,
                        outgoing: false,
                    })
                } else {
                    None
                }
            })
            .collect();
        Ok(Preview {
            path: rel.to_string(),
            size,
            text,
            truncated,
            links,
        })
    }
}

/// Minimal JSON Canvas shape check before anything is written.
pub fn validate_canvas(doc: &Value) -> Result<(), MapError> {
    let bad = |m: &str| Err(MapError::Msg(format!("Ogiltig canvas: {m}")));
    let Some(obj) = doc.as_object() else {
        return bad("inte ett objekt");
    };
    let nodes = obj
        .get("nodes")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let mut ids = HashSet::new();
    for n in &nodes {
        let Some(id) = n.get("id").and_then(Value::as_str) else {
            return bad("nod saknar id");
        };
        if !ids.insert(id.to_string()) {
            return bad(&format!("dubblett-id {id}"));
        }
        if n.get("type").and_then(Value::as_str).is_none() {
            return bad(&format!("nod {id} saknar type"));
        }
    }
    for e in obj
        .get("edges")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
    {
        for k in ["fromNode", "toNode"] {
            if !e
                .get(k)
                .and_then(Value::as_str)
                .is_some_and(|n| ids.contains(n))
            {
                return bad("en pil pekar på en nod som inte finns");
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::fs;

    struct Fx {
        _dir: tempfile::TempDir,
        root: PathBuf,
        meta: PathBuf,
    }
    fn fx() -> Fx {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path().join("proj");
        let meta = dir.path().join("meta");
        fs::create_dir_all(root.join("notes")).unwrap();
        Fx {
            root,
            meta,
            _dir: dir,
        }
    }
    fn files_on_map(e: &mut Engine) -> Vec<String> {
        let (doc, _) = e.load().unwrap();
        let mut v: Vec<String> = doc["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|n| n.get("file").and_then(Value::as_str).map(String::from))
            .collect();
        v.sort();
        v
    }
    fn gen_edges(e: &mut Engine) -> usize {
        let (doc, _) = e.load().unwrap();
        doc["edges"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|x| x["id"].as_str().unwrap().starts_with("g-"))
            .count()
    }

    #[test]
    fn add_edit_rename_delete_cycle() {
        let f = fx();
        fs::write(f.root.join("notes/a.md"), "start").unwrap();
        let mut e = Engine::open(&f.root, &f.meta);
        assert!(e.reconcile(&[]).unwrap().written);
        assert_eq!(files_on_map(&mut e), vec!["notes/a.md"]);

        fs::write(f.root.join("notes/b.md"), "new file").unwrap();
        e.reconcile(&[]).unwrap();
        assert_eq!(files_on_map(&mut e), vec!["notes/a.md", "notes/b.md"]);
        assert_eq!(gen_edges(&mut e), 0);

        fs::write(f.root.join("notes/a.md"), "now links [[b]]").unwrap();
        e.reconcile(&[]).unwrap();
        assert_eq!(gen_edges(&mut e), 1);

        fs::rename(f.root.join("notes/b.md"), f.root.join("notes/c.md")).unwrap();
        let s = e.reconcile(&[]).unwrap();
        assert_eq!(s.renamed, 1);
        assert_eq!(files_on_map(&mut e), vec!["notes/a.md", "notes/c.md"]);
        assert_eq!(
            gen_edges(&mut e),
            0,
            "[[b]] no longer resolves after the rename"
        );

        fs::remove_file(f.root.join("notes/c.md")).unwrap();
        e.reconcile(&[]).unwrap();
        assert_eq!(files_on_map(&mut e), vec!["notes/a.md"]);
    }

    #[test]
    fn startup_reconcile_catches_changes_made_while_closed() {
        let f = fx();
        fs::write(f.root.join("notes/a.md"), "a").unwrap();
        Engine::open(&f.root, &f.meta).reconcile(&[]).unwrap();
        // App closed; files change.
        fs::write(f.root.join("notes/offline.md"), "[[a]]").unwrap();
        fs::remove_file(f.root.join("notes/a.md")).unwrap();
        fs::write(f.root.join("notes/a2.md"), "x").unwrap();
        let mut e = Engine::open(&f.root, &f.meta);
        e.reconcile(&[]).unwrap();
        assert_eq!(
            files_on_map(&mut e),
            vec!["notes/a2.md", "notes/offline.md"]
        );
    }

    #[test]
    fn second_pass_writes_nothing() {
        let f = fx();
        fs::write(f.root.join("notes/a.md"), "[[b]]").unwrap();
        fs::write(f.root.join("notes/b.md"), "b").unwrap();
        let mut e = Engine::open(&f.root, &f.meta);
        assert!(e.reconcile(&[]).unwrap().written);
        assert!(
            !e.reconcile(&[]).unwrap().written,
            "no change must mean no write (no watcher loop)"
        );
        assert!(e.is_own_write());
    }

    #[test]
    fn manual_layout_and_arrows_survive_refresh() {
        let f = fx();
        fs::write(f.root.join("notes/a.md"), "a").unwrap();
        fs::write(f.root.join("notes/b.md"), "b").unwrap();
        let mut e = Engine::open(&f.root, &f.meta);
        e.reconcile(&[]).unwrap();
        let (mut doc, h) = e.load().unwrap();
        let nodes = doc["nodes"].as_array_mut().unwrap();
        let ids: Vec<String> = nodes
            .iter()
            .filter(|n| n["type"] == "file")
            .map(|n| n["id"].as_str().unwrap().to_string())
            .collect();
        for n in nodes.iter_mut().filter(|n| n["type"] == "file") {
            n["x"] = json!(-900);
        }
        doc["edges"].as_array_mut().unwrap().push(
            json!({"id": "mine", "fromNode": ids[0], "toNode": ids[1], "label": "same idea"}),
        );
        e.save(&doc, &h).unwrap();

        fs::write(f.root.join("notes/c.md"), "[[a]]").unwrap();
        e.reconcile(&[]).unwrap();
        let (doc, _) = e.load().unwrap();
        let xs: Vec<i64> = doc["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|n| n["type"] == "file" && n["file"] != "notes/c.md")
            .map(|n| n["x"].as_i64().unwrap())
            .collect();
        assert_eq!(xs, vec![-900, -900]);
        assert!(doc["edges"]
            .as_array()
            .unwrap()
            .iter()
            .any(|x| x["id"] == "mine"));
    }

    #[test]
    fn external_edit_is_not_silently_overwritten() {
        let f = fx();
        fs::write(f.root.join("notes/a.md"), "a").unwrap();
        let mut e = Engine::open(&f.root, &f.meta);
        e.reconcile(&[]).unwrap();
        let (mut doc, h) = e.load().unwrap();

        // Obsidian adds a text card meanwhile.
        let mut theirs = doc.clone();
        theirs["nodes"].as_array_mut().unwrap().push(json!({"id": "obs", "type": "text", "text": "from Obsidian", "x": 0, "y": 0, "width": 10, "height": 10}));
        fs::write(e.canvas_path(), to_bytes(&theirs)).unwrap();
        assert!(!e.is_own_write());

        doc["nodes"][0]["x"] = json!(123);
        assert!(matches!(e.save(&doc, &h), Err(MapError::Conflict)));
        let copy = e.save_copy(&doc).unwrap();
        assert!(f.root.join(&copy).exists());
        // The external card is still there, and a reconcile keeps it.
        e.reconcile(&[]).unwrap();
        let (now, _) = e.load().unwrap();
        assert!(now["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .any(|n| n["id"] == "obs"));
        assert!(
            !files_on_map(&mut e).iter().any(|p| p.contains("copy")),
            "copies are not indexed"
        );
    }

    #[test]
    fn invalid_canvas_on_disk_is_left_alone() {
        let f = fx();
        fs::write(f.root.join(MAP_FILE), "{ not json").unwrap();
        let mut e = Engine::open(&f.root, &f.meta);
        assert!(e.reconcile(&[]).is_err());
        assert_eq!(
            fs::read_to_string(f.root.join(MAP_FILE)).unwrap(),
            "{ not json"
        );
    }

    #[test]
    fn preview_is_confined_and_redacted() {
        let f = fx();
        fs::write(
            f.root.join("notes/a.md"),
            "token: ghp_abcdefghijklmnopqrstuvwxyz0123",
        )
        .unwrap();
        fs::write(f.root.join(".env"), "API_KEY=topsecret").unwrap();
        fs::write(f.root.parent().unwrap().join("outside.md"), "outside").unwrap();
        let mut e = Engine::open(&f.root, &f.meta);
        e.reconcile(&[]).unwrap();
        let p = e.preview("notes/a.md").unwrap();
        assert!(!p.text.unwrap().contains("ghp_abc"));
        for bad in [
            ".env",
            "../outside.md",
            "/etc/passwd",
            "notes/../../outside.md",
        ] {
            assert!(e.preview(bad).is_err(), "{bad} must be refused");
        }
        let map = fs::read_to_string(e.canvas_path()).unwrap();
        assert!(!map.contains(".env") && !map.contains("topsecret"));
    }

    #[test]
    fn exported_canvas_is_valid_and_references_resolve() {
        let f = fx();
        fs::write(f.root.join("notes/a.md"), "[[b]] ![[pic.png]]").unwrap();
        fs::write(f.root.join("notes/b.md"), "b").unwrap();
        fs::write(
            f.root.join("notes/pic.png"),
            [0x89, 0x50, 0x4e, 0x47, 0, 1, 2],
        )
        .unwrap();
        let mut e = Engine::open(&f.root, &f.meta);
        e.reconcile(&[]).unwrap();
        let (doc, _) = e.load().unwrap();
        validate_canvas(&doc).unwrap();
        for n in doc["nodes"].as_array().unwrap() {
            if let Some(file) = n.get("file").and_then(Value::as_str) {
                assert!(f.root.join(file).exists(), "{file} does not resolve");
            }
        }
        assert_eq!(gen_edges(&mut e), 2);
        assert!(
            e.preview("notes/pic.png").unwrap().text.is_none(),
            "binary files are not parsed"
        );
    }
}
