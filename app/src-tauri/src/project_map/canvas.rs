//! Merges the file index into a JSON Canvas document (https://jsoncanvas.org) without disturbing
//! what people made. Rules:
//! - Nodes and fields are kept as they are; only `file` (on rename) and the position of cards the
//!   app placed and nobody moved are ever changed.
//! - Generated edges have ids starting `g-` and are rebuilt every pass. Every other edge is the
//!   user's and is kept unless one of its ends no longer exists.
//! - Generated groups have ids starting `grp-`. Their size follows their cards.

use super::links::Kind;
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

pub const UNCONNECTED: &str = "Unconnected / To review";
const NODE_W: i64 = 280;
const NODE_H: i64 = 60;
const CELL_W: i64 = 300;
const CELL_H: i64 = 80;
const COLS: i64 = 4;
const PAD: i64 = 30;
const TOP: i64 = 50;
const GAP: i64 = 120;

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Edge {
    pub from: String,
    pub to: String,
    pub kind: Kind,
    pub label: String,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct FileMeta {
    pub group: String,
    /// Where the app last placed the card. If the card is still there, nobody moved it.
    pub auto: Option<(i64, i64)>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct Layout {
    pub files: BTreeMap<String, FileMeta>,
    pub groups: BTreeMap<String, (i64, i64)>,
}

fn short_hash(s: &str) -> String {
    super::index::hex(&Sha256::digest(s.as_bytes())[..6])
}

pub fn group_id(name: &str) -> String {
    format!("grp-{}", short_hash(name))
}

/// Folder group: first two path segments for deep files, else the first; root files share one.
pub fn folder_group(file: &str) -> String {
    let parts: Vec<&str> = file.split('/').collect();
    match parts.len() {
        1 => "(project root)".into(),
        2 => parts[0].into(),
        _ => format!("{}/{}", parts[0], parts[1]),
    }
}

fn num(v: &Value, k: &str) -> i64 {
    v.get(k)
        .and_then(Value::as_f64)
        .map(|f| f as i64)
        .unwrap_or(0)
}

fn rect(v: &Value) -> (i64, i64, i64, i64) {
    (
        num(v, "x"),
        num(v, "y"),
        num(v, "width").max(1),
        num(v, "height").max(1),
    )
}

fn overlaps(a: (i64, i64, i64, i64), b: (i64, i64, i64, i64)) -> bool {
    a.0 < b.0 + b.2 && b.0 < a.0 + a.2 && a.1 < b.1 + b.3 && b.1 < a.1 + a.3
}

fn inside(p: (i64, i64), r: (i64, i64, i64, i64)) -> bool {
    p.0 >= r.0 && p.0 <= r.0 + r.2 && p.1 >= r.1 && p.1 <= r.1 + r.3
}

fn is_type(v: &Value, t: &str) -> bool {
    v.get("type").and_then(Value::as_str) == Some(t)
}

fn file_of(v: &Value) -> Option<&str> {
    if is_type(v, "file") {
        v.get("file").and_then(Value::as_str)
    } else {
        None
    }
}

struct Placer<'a> {
    layout: &'a mut Layout,
    occupied: Vec<(i64, i64, i64, i64)>,
    old_groups: HashMap<String, (i64, i64, i64, i64)>,
}

impl Placer<'_> {
    fn origin(&mut self, group: &str) -> (i64, i64) {
        if let Some(o) = self.layout.groups.get(group) {
            return *o;
        }
        let right = self
            .occupied
            .iter()
            .chain(self.old_groups.values())
            .map(|r| r.0 + r.2)
            .chain(
                self.layout
                    .groups
                    .values()
                    .map(|o| o.0 + COLS * CELL_W + 2 * PAD),
            )
            .max();
        let o = (right.map(|r| r + GAP).unwrap_or(0), 0);
        self.layout.groups.insert(group.to_string(), o);
        o
    }

    fn place(&mut self, group: &str) -> (i64, i64) {
        let (ox, oy) = self.origin(group);
        for i in 0.. {
            let p = (
                ox + PAD + (i % COLS) * CELL_W,
                oy + TOP + (i / COLS) * CELL_H,
            );
            let r = (p.0, p.1, NODE_W, NODE_H);
            if !self.occupied.iter().any(|o| overlaps(*o, r)) {
                self.occupied.push(r);
                return p;
            }
        }
        unreachable!()
    }
}

/// Returns the merged document. `renames` are (old, new) pairs found by the indexer.
pub fn merge(
    canvas: &Value,
    files: &BTreeSet<String>,
    edges: &[Edge],
    renames: &[(String, String)],
    layout: &mut Layout,
) -> Value {
    let mut doc: Map<String, Value> = canvas.as_object().cloned().unwrap_or_default();
    let mut nodes: Vec<Value> = doc
        .get("nodes")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let mut user_edges: Vec<Value> = doc
        .get("edges")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();

    // Renames keep the card (and its position) and move its layout entry.
    for (old, new) in renames {
        for n in nodes.iter_mut().filter(|n| file_of(n) == Some(old)) {
            n["file"] = json!(new);
        }
        if let Some(m) = layout.files.remove(old) {
            layout.files.insert(new.clone(), m);
        }
    }

    // Deleted files lose their cards. Text, link and group nodes are never touched here.
    nodes.retain(|n| file_of(n).is_none_or(|f| files.contains(f)));
    layout.files.retain(|f, _| files.contains(f));

    let old_groups: HashMap<String, (i64, i64, i64, i64)> = nodes
        .iter()
        .filter(|n| is_type(n, "group"))
        .filter_map(|n| Some((n.get("id")?.as_str()?.to_string(), rect(n))))
        .collect();
    let occupied = nodes
        .iter()
        .filter(|n| !is_type(n, "group"))
        .map(rect)
        .collect();
    let mut placer = Placer {
        layout,
        occupied,
        old_groups,
    };

    let connected: HashSet<&str> = edges
        .iter()
        .flat_map(|e| [e.from.as_str(), e.to.as_str()])
        .collect();
    let want_group = |f: &str| {
        if connected.contains(f) {
            folder_group(f)
        } else {
            UNCONNECTED.to_string()
        }
    };

    let mut node_of: HashMap<String, usize> = HashMap::new();
    for (i, n) in nodes.iter().enumerate() {
        if let Some(f) = file_of(n) {
            node_of.entry(f.to_string()).or_insert(i);
        }
    }

    for f in files {
        let group = want_group(f);
        match node_of.get(f).copied() {
            None => {
                let (x, y) = placer.place(&group);
                let mut id = format!("f-{}", short_hash(f));
                while nodes
                    .iter()
                    .any(|n| n.get("id").and_then(Value::as_str) == Some(id.as_str()))
                {
                    id = format!("f-{}", short_hash(&(id.clone() + "+")));
                }
                node_of.insert(f.clone(), nodes.len());
                nodes.push(json!({"id": id, "type": "file", "file": f, "x": x, "y": y, "width": NODE_W, "height": NODE_H}));
                placer.layout.files.insert(
                    f.clone(),
                    FileMeta {
                        group,
                        auto: Some((x, y)),
                    },
                );
            }
            Some(i) => {
                let pos = (num(&nodes[i], "x"), num(&nodes[i], "y"));
                let meta = placer
                    .layout
                    .files
                    .entry(f.clone())
                    .or_insert_with(|| FileMeta {
                        group: group.clone(),
                        auto: None,
                    });
                // Only cards the app placed and nobody moved follow their group.
                if meta.group != group && meta.auto == Some(pos) {
                    placer.occupied.retain(|r| (r.0, r.1) != pos);
                    let (x, y) = placer.place(&group);
                    nodes[i]["x"] = json!(x);
                    nodes[i]["y"] = json!(y);
                    let meta = placer.layout.files.get_mut(f).unwrap();
                    meta.group = group;
                    meta.auto = Some((x, y));
                }
            }
        }
    }
    let layout = placer.layout;
    let old_groups = placer.old_groups;

    // Groups: size follows members (still at their auto spot, or inside the group's old frame).
    let mut members: BTreeMap<String, Vec<(i64, i64, i64, i64)>> = BTreeMap::new();
    for (f, m) in &layout.files {
        let Some(&i) = node_of.get(f) else { continue };
        let r = rect(&nodes[i]);
        let gid = group_id(&m.group);
        let centre = (r.0 + r.2 / 2, r.1 + r.3 / 2);
        if m.auto == Some((r.0, r.1)) || old_groups.get(&gid).is_some_and(|g| inside(centre, *g)) {
            members.entry(m.group.clone()).or_default().push(r);
        }
    }
    layout.groups.retain(|g, _| members.contains_key(g));
    let wanted: HashMap<String, &str> = members.keys().map(|g| (group_id(g), g.as_str())).collect();
    nodes.retain(|n| {
        let id = n.get("id").and_then(Value::as_str).unwrap_or("");
        !id.starts_with("grp-") || wanted.contains_key(id)
    });
    let mut groups_out: Vec<Value> = Vec::new();
    for (name, rs) in &members {
        let (ox, oy) = layout
            .groups
            .get(name)
            .copied()
            .unwrap_or((rs[0].0 - PAD, rs[0].1 - TOP));
        let x = rs.iter().map(|r| r.0 - PAD).chain([ox]).min().unwrap();
        let y = rs.iter().map(|r| r.1 - TOP).chain([oy]).min().unwrap();
        let right = rs
            .iter()
            .map(|r| r.0 + r.2 + PAD)
            .max()
            .unwrap()
            .max(ox + COLS * CELL_W + PAD);
        let bottom = rs.iter().map(|r| r.1 + r.3 + PAD).max().unwrap();
        let id = group_id(name);
        let mut g = nodes
            .iter()
            .position(|n| n.get("id").and_then(Value::as_str) == Some(id.as_str()))
            .map(|i| nodes.remove(i))
            .unwrap_or_else(|| json!({"id": id, "type": "group", "label": name}));
        g["x"] = json!(x);
        g["y"] = json!(y);
        g["width"] = json!(right - x);
        g["height"] = json!(bottom - y);
        groups_out.push(g);
    }
    // Groups first so they render beneath cards, user groups keep their place in the order.
    let mut ordered: Vec<Value> = nodes
        .iter()
        .filter(|n| is_type(n, "group"))
        .cloned()
        .collect();
    ordered.extend(groups_out);
    ordered.extend(nodes.into_iter().filter(|n| !is_type(n, "group")));

    let ids: HashSet<String> = ordered
        .iter()
        .filter_map(|n| n.get("id").and_then(Value::as_str).map(String::from))
        .collect();
    user_edges.retain(|e| {
        let id = e.get("id").and_then(Value::as_str).unwrap_or("");
        let end = |k: &str| {
            e.get(k)
                .and_then(Value::as_str)
                .is_some_and(|n| ids.contains(n))
        };
        !id.starts_with("g-") && end("fromNode") && end("toNode")
    });

    let id_for: HashMap<&str, &str> = ordered
        .iter()
        .filter_map(|n| Some((file_of(n)?, n.get("id")?.as_str()?)))
        .collect::<Vec<_>>()
        .into_iter()
        .rev() // first card for a file wins
        .collect();
    let mut gen: Vec<Value> = Vec::new();
    let mut seen = HashSet::new();
    let mut sorted = edges.to_vec();
    sorted.sort();
    for e in sorted {
        let (Some(a), Some(b)) = (id_for.get(e.from.as_str()), id_for.get(e.to.as_str())) else {
            continue;
        };
        let (k, color) = match e.kind {
            Kind::Explicit => ("e", "4"),
            Kind::Dependency => ("d", "5"),
            Kind::Inferred => ("i", "3"),
        };
        let id = format!("g-{k}-{}", short_hash(&format!("{a}|{b}|{}", e.label)));
        if seen.insert(id.clone()) {
            let label = if e.kind == Kind::Inferred {
                format!("{} (inferred)", e.label)
            } else {
                e.label.clone()
            };
            gen.push(json!({"id": id, "fromNode": a, "toNode": b, "label": label, "color": color}));
        }
    }
    user_edges.extend(gen);

    doc.insert("nodes".into(), Value::Array(ordered));
    doc.insert("edges".into(), Value::Array(user_edges));
    Value::Object(doc)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn files(f: &[&str]) -> BTreeSet<String> {
        f.iter().map(|s| s.to_string()).collect()
    }
    fn edge(a: &str, b: &str) -> Edge {
        Edge {
            from: a.into(),
            to: b.into(),
            kind: Kind::Explicit,
            label: "links to".into(),
        }
    }
    fn node<'a>(doc: &'a Value, file: &str) -> &'a Value {
        doc["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .find(|n| file_of(n) == Some(file))
            .unwrap()
    }
    fn count(doc: &Value, k: &str) -> usize {
        doc[k].as_array().unwrap().len()
    }

    #[test]
    fn new_files_get_cards_and_unconnected_group() {
        let mut l = Layout::default();
        let d = merge(
            &json!({}),
            &files(&["a.md", "n/b.md", "n/c.md"]),
            &[edge("n/b.md", "n/c.md")],
            &[],
            &mut l,
        );
        assert_eq!(l.files["a.md"].group, UNCONNECTED);
        assert_eq!(l.files["n/b.md"].group, "n");
        let groups: Vec<&str> = d["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|n| is_type(n, "group"))
            .map(|n| n["label"].as_str().unwrap())
            .collect();
        assert!(groups.contains(&UNCONNECTED) && groups.contains(&"n"));
        assert_eq!(count(&d, "edges"), 1);
        assert_eq!(d["edges"][0]["label"], "links to");
    }

    #[test]
    fn manual_positions_user_edges_and_unknown_fields_survive() {
        let mut l = Layout::default();
        let mut d = merge(&json!({}), &files(&["a.md", "b.md"]), &[], &[], &mut l);
        let a = d["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .position(|n| file_of(n) == Some("a.md"))
            .unwrap();
        d["nodes"][a]["x"] = json!(5000);
        d["nodes"][a]["color"] = json!("2");
        d["nodes"][a]["customField"] = json!({"keep": true});
        d["somethingTopLevel"] = json!(1);
        let (ia, ib) = (
            node(&d, "a.md")["id"].clone(),
            node(&d, "b.md")["id"].clone(),
        );
        d["edges"]
            .as_array_mut()
            .unwrap()
            .push(json!({"id": "my-arrow", "fromNode": ia, "toNode": ib, "label": "why"}));
        d["nodes"].as_array_mut().unwrap().push(json!({"id": "t1", "type": "text", "text": "my note", "x": 0, "y": -500, "width": 100, "height": 50}));

        let d2 = merge(
            &d,
            &files(&["a.md", "b.md", "c.md"]),
            &[edge("a.md", "b.md")],
            &[],
            &mut l,
        );
        let a2 = node(&d2, "a.md");
        assert_eq!(a2["x"], 5000);
        assert_eq!(a2["color"], "2");
        assert_eq!(a2["customField"]["keep"], true);
        assert_eq!(d2["somethingTopLevel"], 1);
        let edges = d2["edges"].as_array().unwrap();
        assert!(edges.iter().any(|e| e["id"] == "my-arrow"));
        assert!(edges
            .iter()
            .any(|e| e["id"].as_str().unwrap().starts_with("g-e-")));
        assert!(d2["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .any(|n| n["id"] == "t1"));
        // a.md was moved by hand, so gaining a link must not move it.
        assert_eq!(l.files["a.md"].group, UNCONNECTED);
    }

    #[test]
    fn unmoved_card_follows_group_when_it_gains_a_link() {
        let mut l = Layout::default();
        let d = merge(&json!({}), &files(&["n/a.md", "n/b.md"]), &[], &[], &mut l);
        let before = node(&d, "n/a.md")["x"].clone();
        let d2 = merge(
            &d,
            &files(&["n/a.md", "n/b.md"]),
            &[edge("n/a.md", "n/b.md")],
            &[],
            &mut l,
        );
        assert_eq!(l.files["n/a.md"].group, "n");
        assert_ne!(node(&d2, "n/a.md")["x"], before);
    }

    #[test]
    fn rename_keeps_card_and_delete_leaves_nothing_stale() {
        let mut l = Layout::default();
        let mut d = merge(
            &json!({}),
            &files(&["a.md", "b.md"]),
            &[edge("a.md", "b.md")],
            &[],
            &mut l,
        );
        let a = d["nodes"]
            .as_array()
            .unwrap()
            .iter()
            .position(|n| file_of(n) == Some("a.md"))
            .unwrap();
        d["nodes"][a]["x"] = json!(777);
        let id_a = d["nodes"][a]["id"].clone();
        let id_b = node(&d, "b.md")["id"].clone();
        d["edges"]
            .as_array_mut()
            .unwrap()
            .push(json!({"id": "u", "fromNode": id_b, "toNode": id_a}));

        let d2 = merge(
            &d,
            &files(&["z.md", "b.md"]),
            &[edge("z.md", "b.md")],
            &[("a.md".into(), "z.md".into())],
            &mut l,
        );
        assert_eq!(node(&d2, "z.md")["x"], 777);
        assert_eq!(node(&d2, "z.md")["id"], id_a);
        assert!(l.files.contains_key("z.md") && !l.files.contains_key("a.md"));

        let d3 = merge(&d2, &files(&["b.md"]), &[], &[], &mut l);
        assert_eq!(
            d3["nodes"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|n| file_of(n).is_some())
                .count(),
            1
        );
        assert_eq!(
            count(&d3, "edges"),
            0,
            "edges to the deleted card must go, user ones too"
        );
    }

    #[test]
    fn merge_is_idempotent() {
        let mut l = Layout::default();
        let f = files(&["a.md", "x/b.rs", "x/c.rs"]);
        let e = [Edge {
            from: "x/b.rs".into(),
            to: "x/c.rs".into(),
            kind: Kind::Dependency,
            label: "imports".into(),
        }];
        let d1 = merge(&json!({}), &f, &e, &[], &mut l);
        let d2 = merge(&d1, &f, &e, &[], &mut l);
        assert_eq!(d1, d2);
    }
}
