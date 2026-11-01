//! Prestandamätningar för indexeringen. Körs bara på begäran:
//!   cargo test --release perf_ -- --ignored --nocapture --test-threads=1
//! Skriver aldrig i projektet: kartan och indexet hamnar i en tillfällig mapp.

use super::engine::Engine;
use std::path::{Path, PathBuf};
use std::time::Instant;

fn ms(t: Instant) -> f64 {
    t.elapsed().as_secs_f64() * 1000.0
}

/// Kall start, varm genomgång utan ändringar, och genomgång efter en ändrad fil.
fn measure(name: &str, root: &Path, touch: &Path) {
    let meta = tempfile::tempdir().unwrap();
    let t = Instant::now();
    let mut e = Engine::open(root, meta.path());
    let s = e.reconcile(&[]).unwrap();
    let cold = ms(t);
    let t = Instant::now();
    let s2 = e.reconcile(&[]).unwrap();
    let warm = ms(t);
    let original = std::fs::read(touch).ok();
    let t = Instant::now();
    if original.is_some() {
        // Bara i syntetiska strukturer: det riktiga projektet ändras aldrig (se perf_real_project).
        std::fs::write(touch, b"changed [[n1]]\n").unwrap();
    }
    let s3 = e.reconcile(&[]).unwrap();
    let one = ms(t);
    let canvas = std::fs::metadata(e.canvas_path()).map(|m| m.len()).unwrap_or(0);
    println!(
        "PERF {name}: filer={} kopplingar={} kall={cold:.0}ms varm={warm:.0}ms (skrev={}) en_ändrad_fil={one:.0}ms (skrev={}) canvas={}kB",
        s.files, s.edges, s2.written, s3.written, canvas / 1024
    );
}

fn synthetic(dir: &Path, files: usize) -> PathBuf {
    let root = dir.join("synthetic");
    for i in 0..files {
        let folder = root.join(format!("area{}/sub{}", i % 40, i % 7));
        std::fs::create_dir_all(&folder).unwrap();
        let body = if i % 3 == 0 {
            format!("# note {i}\nSee [[n{}]] and `area{}/sub{}/n{}.md`.\n", (i + 1) % files, (i + 5) % 40, (i + 5) % 7, (i + 5) % files)
        } else {
            format!("export const v{i} = {i};\n")
        };
        let ext = if i % 3 == 0 { "md" } else { "ts" };
        std::fs::write(folder.join(format!("n{i}.{ext}")), body).unwrap();
    }
    root
}

#[test]
#[ignore]
fn perf_real_project() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..").canonicalize().unwrap();
    // `touch` pekar på en fil som inte finns, så det riktiga projektet läses men ändras aldrig.
    measure("riktiga projektet", &root, &root.join("does-not-exist-perf"));
}

/// Antal filer styrs med PERF_FILES (standard 20 000).
#[test]
#[ignore]
fn perf_synthetic() {
    let n: usize = std::env::var("PERF_FILES").ok().and_then(|v| v.parse().ok()).unwrap_or(20_000);
    let dir = tempfile::tempdir().unwrap();
    let root = synthetic(dir.path(), n);
    measure(&format!("syntetisk {n} filer"), &root, &root.join("area3/sub3/n3.md"));
}
