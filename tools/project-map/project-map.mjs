#!/usr/bin/env node
// TraderGO project map.
//
// Indexes the repo and the Obsidian vault and writes JSON Canvas files that show how files
// connect. Deterministic and local: no network, no LLM, no dependencies beyond Node >= 20 and
// (optionally) git. It reads project files and writes only to `output_dir` and `state_dir`.
//
// Usage: node tools/project-map/project-map.mjs <command>
//   refresh                 one full reconcile (default)
//   rebuild [--reset-layout] drop the parse cache (and, with the flag, all saved positions)
//   watch [--poll SECONDS]  reconcile at startup, then on every file change
//   start | stop | status   run the watcher in the background
//   check                   validate the generated canvases
//   install-agent | uninstall-agent   macOS LaunchAgent (starts the watcher at login)

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync, spawn } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const TOOL_DIR = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = fileURLToPath(import.meta.url);
const AGENT_LABEL = 'com.tradergo.project-map';
const UNCONNECTED = 'Unconnected / To review';
const ELSEWHERE = 'Connected elsewhere';

const DEFAULT_PARSERS = {
  '.md': 'md', '.markdown': 'md', '.canvas': 'canvas',
  '.js': 'js', '.mjs': 'js', '.cjs': 'js', '.jsx': 'js', '.ts': 'js', '.tsx': 'js', '.mts': 'js',
  '.cts': 'js', '.vue': 'js', '.svelte': 'js',
  '.css': 'css', '.scss': 'css', '.less': 'css', '.html': 'html', '.htm': 'html',
  '.rs': 'rs', '.py': 'py',
  '.json': 'config', '.jsonc': 'config', '.toml': 'config', '.yaml': 'config', '.yml': 'config',
  '.ini': 'config', '.cfg': 'config', '.conf': 'config', '.plist': 'config', '.xml': 'config',
  '.sh': 'config', '.bash': 'config', '.zsh': 'config', '.ps1': 'config', '.base': 'config',
};

// Kind of reference -> [category, edge label]. Category 0 = explicit link,
// 1 = verified dependency, 2 = inferred relationship.
const KINDS = {
  wikilink: [0, 'links'], embed: [0, 'embeds'], mdlink: [0, 'links'], mdembed: [0, 'embeds'],
  canvas: [0, 'on canvas'],
  import: [1, 'imports'], css: [1, 'imports'], html: [1, 'loads'], mod: [1, 'mod'],
  include: [1, 'includes'], py: [1, 'imports'], config: [1, 'config ref'],
  mention: [2, '≈ mentions'], alias: [2, '≈ names'],
};
const CAT_NAMES = ['explicit', 'verified', 'inferred'];
const CAT_COLORS = ['6', '4', undefined];
const JS_EXTS = ['', '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.mts', '.cts', '.json', '.css', '.vue', '.svelte'];

// ---------------------------------------------------------------- helpers

const posix = (p) => p.split(path.sep).join('/');
const sha1 = (s) => crypto.createHash('sha1').update(s).digest('hex');
const nid = (key) => sha1(key).slice(0, 16);
const log = (...a) => console.log(new Date().toISOString(), ...a);
const sleepSync = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

function readJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return fallback; }
}

function alive(pid) {
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}

// Write via a temp file in the same folder and rename, so readers never see half a file.
// Returns false when the content is unchanged and nothing was written.
function atomicWrite(file, content) {
  try { if (fs.readFileSync(file, 'utf8') === content) return false; } catch { /* new file */ }
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = path.join(path.dirname(file), `.${path.basename(file)}.${process.pid}.tmp`);
  const fd = fs.openSync(tmp, 'w');
  try { fs.writeFileSync(fd, content); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
  fs.renameSync(tmp, file);
  return true;
}

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { args._.push(a); continue; }
    const next = argv[i + 1];
    if (next !== undefined && !next.startsWith('--')) { args[a.slice(2)] = next; i++; }
    else args[a.slice(2)] = true;
  }
  return args;
}

// ---------------------------------------------------------------- patterns

// Glob to RegExp: `**` crosses folders, `*` and `?` stay inside one. With `capture`, every
// single `*` becomes a capture group (used for alias names).
function globToRegex(glob, capture = false) {
  let re = '';
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*' && glob[i + 1] === '*') {
      if ((i === 0 || glob[i - 1] === '/') && glob[i + 2] === '/') { re += '(?:.*/)?'; i += 2; }
      else { re += '.*'; i += 1; }
    } else if (c === '*') re += capture ? '([^/]*)' : '[^/]*';
    else if (c === '?') re += '[^/]';
    else re += c.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp(`^${re}$`);
}

function compilePattern(raw) {
  let p = raw.trim();
  const neg = p.startsWith('!');
  if (neg) p = p.slice(1);
  const dirOnly = p.endsWith('/');
  if (dirOnly) p = p.slice(0, -1);
  const anchored = p.includes('/');
  if (p.startsWith('/')) p = p.slice(1);
  return { neg, dirOnly, anchored, re: globToRegex(p) };
}

// gitignore-style: a pattern without a trailing slash also matches a folder of that name.
// With `fileOnly`, it matches the file path itself, and only `dir/` patterns match folders.
function makeMatcher(patterns, fileOnly = false) {
  const compiled = (patterns || []).filter((p) => p && !p.startsWith('#')).map(compilePattern);
  const test = (pat, rel) => {
    const parts = rel.split('/');
    const last = pat.dirOnly ? parts.length - 1 : parts.length;
    const first = fileOnly && !pat.dirOnly ? parts.length : 1;
    for (let i = first; i <= last; i++) {
      const cand = pat.anchored ? parts.slice(0, i).join('/') : parts[i - 1];
      if (pat.re.test(cand)) return true;
    }
    return false;
  };
  return (rel) => {
    let hit = false;
    for (const pat of compiled) if (hit === pat.neg && test(pat, rel)) hit = !pat.neg;
    return hit;
  };
}

// ---------------------------------------------------------------- config

function loadConfig(args) {
  const base = readJson(path.join(TOOL_DIR, 'config.json'), null);
  if (!base) throw new Error(`Cannot read ${path.join(TOOL_DIR, 'config.json')}`);
  const local = readJson(path.join(TOOL_DIR, 'config.local.json'), {});
  const cfg = { ...base, ...local, layout: { ...base.layout, ...local.layout } };
  cfg.exclude = [...(cfg.exclude || []), ...(base.exclude_add || []), ...(local.exclude_add || [])];
  cfg.include = [...(cfg.include || ['**']), ...(local.include_add || [])];
  cfg.parsers = { ...DEFAULT_PARSERS, ...(cfg.parsers || {}) };
  cfg.hash = sha1(JSON.stringify([base, local, 3]));

  cfg.root = path.resolve(TOOL_DIR, args.root || cfg.root || '../..');
  cfg.vaultAbs = path.resolve(cfg.root, cfg.vault || '.');
  cfg.outAbs = args.out ? path.resolve(args.out) : path.resolve(cfg.root, cfg.output_dir);
  cfg.stateAbs = args.state ? path.resolve(args.state) : path.resolve(cfg.root, cfg.state_dir);
  cfg.vaultPrefix = posix(path.relative(cfg.root, cfg.vaultAbs));
  if (cfg.vaultPrefix.startsWith('..')) throw new Error('The vault must be inside the project root.');

  // Generated output and state never feed back into the index or the watcher.
  const own = [cfg.outAbs, cfg.stateAbs].map((p) => posix(path.relative(cfg.root, p)))
    .filter((r) => r && !r.startsWith('..'));
  cfg.ownDirs = own;
  cfg.isIncluded = makeMatcher(cfg.include);
  cfg.isExcluded = makeMatcher([...cfg.exclude, ...own.map((r) => `/${r}/`)]);
  cfg.noParse = makeMatcher(cfg.no_parse || []);
  cfg.groupRules = (cfg.groups || []).map((g, i) => ({ ...g, order: i, test: makeMatcher(g.match, true) }));
  cfg.aliasRules = (cfg.aliases || []).map((a) => ({ re: globToRegex(a.files, true), name: a.name }));
  return cfg;
}

function gitDir(root) {
  try {
    const out = execFileSync('git', ['-C', root, 'rev-parse', '--git-dir'], { stdio: ['ignore', 'pipe', 'ignore'] });
    return path.resolve(root, out.toString().trim());
  } catch { return null; }
}

// ---------------------------------------------------------------- scanning

function listCandidates(cfg, git) {
  if (git && cfg.respect_gitignore !== false) {
    const out = execFileSync('git', ['-C', cfg.root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
      { maxBuffer: 256 << 20, stdio: ['ignore', 'pipe', 'ignore'] });
    return [...new Set(out.toString('utf8').split('\0').filter(Boolean))];
  }
  // No git: walk the tree, using the root .gitignore as extra exclusions when asked to.
  let ignore = () => false;
  if (cfg.respect_gitignore !== false) {
    try { ignore = makeMatcher(fs.readFileSync(path.join(cfg.root, '.gitignore'), 'utf8').split(/\r?\n/)); } catch { /* none */ }
  }
  const out = [];
  const walk = (dirRel) => {
    let entries = [];
    try { entries = fs.readdirSync(path.join(cfg.root, dirRel), { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      const rel = dirRel ? `${dirRel}/${e.name}` : e.name;
      if (e.isDirectory()) {
        if (!cfg.isExcluded(`${rel}/x`) && !ignore(`${rel}/x`)) walk(rel);
      } else if (e.isFile() && !ignore(rel)) out.push(rel);
    }
  };
  walk('');
  return out;
}

function scan(cfg, git, cache) {
  const files = new Map();
  for (const rel of listCandidates(cfg, git).sort()) {
    if (!cfg.isIncluded(rel) || cfg.isExcluded(rel)) continue;
    const abs = path.join(cfg.root, rel);
    let st;
    try { st = fs.lstatSync(abs); } catch { continue; } // tracked but deleted on disk
    if (!st.isFile()) continue; // skips symlinks too, so nothing outside the root is read
    const prev = cache.files[rel];
    if (prev && prev.mtimeMs === st.mtimeMs && prev.size === st.size) { files.set(rel, prev); continue; }
    const entry = { mtimeMs: st.mtimeMs, size: st.size, hash: `size:${st.size}`, refs: [] };
    const kind = cfg.parsers[path.extname(rel).toLowerCase()];
    try {
      if (st.size <= (cfg.max_hash_bytes ?? 20e6)) {
        const buf = fs.readFileSync(abs);
        entry.hash = sha1(buf);
        // Attachments and other binary files are hashed (for rename detection) but never parsed.
        if (kind && st.size <= (cfg.max_parse_bytes ?? 1e6) && !cfg.noParse(rel)) {
          entry.refs = parseRefs(kind, buf.toString('utf8'), rel);
        }
      }
    } catch { /* unreadable right now; listed without references */ }
    files.set(rel, entry);
  }
  return files;
}

// ---------------------------------------------------------------- parsers

function parseRefs(kind, text, rel) {
  const refs = [];
  const add = (k, s) => { if (s && s.length <= 300) refs.push({ k, s }); };
  if (kind === 'md') parseMarkdown(text, add);
  else if (kind === 'canvas') {
    const c = readJsonText(text);
    for (const n of c?.nodes || []) if (n.type === 'file' && typeof n.file === 'string') add('canvas', n.file);
  } else if (kind === 'js') {
    for (const re of [/\b(?:import|export)\s+(?:type\s+)?(?:[\w*{}\s,$]+?\s+from\s+)?['"]([^'"\n]+)['"]/g,
      /\bimport\s*\(\s*['"]([^'"\n]+)['"]\s*\)/g, /\brequire\s*\(\s*['"]([^'"\n]+)['"]\s*\)/g]) {
      for (const m of text.matchAll(re)) if (/^\.{0,2}\//.test(m[1])) add('import', m[1].split('?')[0]);
    }
  } else if (kind === 'css') {
    for (const m of text.matchAll(/@import\s+(?:url\()?\s*['"]?([^'")\s;]+)|url\(\s*['"]?([^'")]+)['"]?\s*\)/g)) {
      const s = m[1] || m[2];
      if (!/^[a-z][a-z0-9+.-]*:|^#/i.test(s)) add('css', s.split(/[?#]/)[0]);
    }
  } else if (kind === 'html') {
    for (const m of text.matchAll(/\b(?:src|href)\s*=\s*["']([^"']+)["']/g)) {
      if (!/^[a-z][a-z0-9+.-]*:|^#|^\/\//i.test(m[1])) add('html', m[1].split(/[?#]/)[0]);
    }
  } else if (kind === 'rs') {
    for (const m of text.matchAll(/^\s*(?:#\[[^\]]*\]\s*)*(?:pub(?:\([^)]*\))?\s+)?mod\s+([A-Za-z_]\w*)\s*;/gm)) add('mod', m[1]);
    for (const m of text.matchAll(/\binclude(?:_str|_bytes)?!\s*\(\s*"([^"]+)"\s*\)/g)) add('include', m[1]);
  } else if (kind === 'py') {
    for (const m of text.matchAll(/^\s*from\s+(\.+[\w.]*|[A-Za-z_][\w.]*)\s+import\s+\(?([^\n#)]+)/gm)) {
      add('py', m[1]);
      for (const name of m[2].split(',')) {
        const n = name.trim().split(/\s+/)[0];
        if (/^\w+$/.test(n)) add('py', m[1].endsWith('.') ? m[1] + n : `${m[1]}.${n}`);
      }
    }
    for (const m of text.matchAll(/^\s*import\s+([^\n#]+)/gm)) {
      for (const name of m[1].split(',')) add('py', name.trim().split(/\s+/)[0]);
    }
  } else if (kind === 'config') {
    const strings = new Set();
    const json = path.extname(rel) === '.json' ? readJsonText(text) : undefined;
    if (json !== undefined) {
      const walk = (v) => {
        if (typeof v === 'string') strings.add(v);
        else if (Array.isArray(v)) v.forEach(walk);
        else if (v && typeof v === 'object') Object.values(v).forEach(walk);
      };
      walk(json);
    } else {
      for (const m of text.matchAll(/"((?:[^"\\\n]|\\.){1,300})"|'([^'\n]{1,300})'/g)) strings.add(m[1] ?? m[2]);
      for (const t of text.split(/[\s"'`,;=()[\]{}<>]+/)) strings.add(t.replace(/:$/, ''));
    }
    for (const s of strings) {
      if (s && !/[*$\n]|:\/\/|^-/.test(s) && (s.includes('/') || /\.[A-Za-z0-9]{1,8}$/.test(s))) add('config', s);
    }
  }
  const seen = new Set();
  return refs.filter((r) => { const k = `${r.k}\0${r.s}`; if (seen.has(k)) return false; seen.add(k); return true; });
}

function readJsonText(text) {
  try { return JSON.parse(text); } catch { return undefined; }
}

function parseMarkdown(text, add) {
  // Links inside fenced code blocks and comments are examples, not links.
  const lines = text.split(/\r?\n/);
  let fence = null;
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^ {0,3}(`{3,}|~{3,})/);
    if (fence) {
      if (m && m[1][0] === fence[0] && m[1].length >= fence.length && /^ {0,3}(`+|~+)\s*$/.test(lines[i])) fence = null;
      lines[i] = '';
    } else if (m) { fence = m[1]; lines[i] = ''; }
  }
  let body = lines.join('\n').replace(/<!--[\s\S]*?-->/g, ' ').replace(/%%[\s\S]*?%%/g, ' ');
  // Inline code: a path or skill name in backticks is an inferred mention, never a link.
  body = body.replace(/(`+)([^`\n](?:[^\n]*?[^`\n])?)\1(?!`)/g, (_, _t, code) => {
    add('mention', code.trim());
    return ' ';
  });
  for (const m of body.matchAll(/(!?)\[\[([^[\]\n]+?)\]\]/g)) {
    const target = m[2].split('|')[0].split('#')[0].trim();
    if (target) add(m[1] ? 'embed' : 'wikilink', target);
  }
  body = body.replace(/!?\[\[[^[\]\n]+?\]\]/g, ' ');
  const mdTarget = (raw, kind) => {
    let t = raw.startsWith('<') ? raw.slice(1, -1) : raw;
    if (/^[a-z][a-z0-9+.-]*:/i.test(t) || t.startsWith('#')) return;
    t = t.split('#')[0].split('?')[0];
    try { t = decodeURIComponent(t); } catch { /* keep as written */ }
    add(kind, t);
  };
  const MDLINK = /(!?)\[((?:\\.|[^\]\\\n])*)\]\(\s*(<[^>\n]*>|[^\s()]+(?:\([^\s()]*\)[^\s()]*)*)(?:\s+(?:"[^"]*"|'[^']*'|\([^)]*\)))?\s*\)/g;
  for (const m of body.matchAll(MDLINK)) mdTarget(m[3], m[1] ? 'mdembed' : 'mdlink');
  for (const m of body.matchAll(/^ {0,3}\[[^\]\n]+\]:\s*(<[^>\n]+>|\S+)/gm)) mdTarget(m[1], 'mdlink');
}

// ---------------------------------------------------------------- resolving

function makeIndex(cfg, files) {
  const vp = cfg.vaultPrefix;
  const inVault = (rel) => vp === '' || rel.startsWith(`${vp}/`);
  const vaultRel = (rel) => (vp === '' ? rel : rel.slice(vp.length + 1));
  const byName = new Map();
  const byVaultPath = new Map();
  const dirs = new Set();
  const aliases = new Map();
  const nameCount = new Map();
  const push = (map, k, v) => { if (!map.has(k)) map.set(k, []); map.get(k).push(v); };
  for (const rel of files.keys()) {
    for (let d = path.posix.dirname(rel); d !== '.' && !dirs.has(d); d = path.posix.dirname(d)) dirs.add(d);
    nameCount.set(path.posix.basename(rel), (nameCount.get(path.posix.basename(rel)) || 0) + 1);
    for (const a of cfg.aliasRules) {
      const m = rel.match(a.re);
      if (m) aliases.set(a.name.replace(/\{(\d+)\}/g, (_, i) => m[Number(i)] ?? ''), rel);
    }
    if (!inVault(rel)) continue;
    const base = path.posix.basename(rel).toLowerCase();
    push(byName, base, rel);
    if (base.endsWith('.md')) push(byName, base.slice(0, -3), rel);
    const vr = vaultRel(rel).toLowerCase();
    push(byVaultPath, vr, rel);
    if (vr.endsWith('.md')) push(byVaultPath, vr.slice(0, -3), rel);
  }
  return { cfg, files, dirs, byName, byVaultPath, aliases, nameCount, inVault, vaultRel };
}

// Obsidian-style tie-break: same folder first, then the shortest path.
function pickBest(cands, from) {
  const dir = path.posix.dirname(from);
  return [...new Set(cands)].sort((a, b) =>
    (path.posix.dirname(b) === dir) - (path.posix.dirname(a) === dir) || a.length - b.length || (a < b ? -1 : 1))[0];
}

function joinRel(base, spec) {
  const p = path.posix.normalize(path.posix.join(base, spec)).replace(/\/$/, '');
  return p.startsWith('..') || p === '.' ? null : p;
}

function nearestPackageDir(idx, from) {
  for (let d = path.posix.dirname(from); d !== '.'; d = path.posix.dirname(d)) {
    if (idx.files.has(`${d}/package.json`)) return d;
  }
  return '';
}

// Returns { to, kind } when resolved, { unresolved: true } for an explicit link that points
// nowhere, or null for anything else (packages, URLs, folders, plain words).
function resolveRef(ref, from, idx) {
  const { files, dirs } = idx;
  const dir = path.posix.dirname(from) === '.' ? '' : path.posix.dirname(from);
  const first = (cands) => cands.find((c) => c && files.has(c));
  const vp = idx.cfg.vaultPrefix;

  switch (ref.k) {
    case 'wikilink': case 'embed': {
      const t = ref.s.replace(/^\.\//, '').toLowerCase();
      let cands = idx.byVaultPath.get(t) || [];
      if (!cands.length && t.includes('/')) {
        for (const [k, v] of idx.byVaultPath) if (k.endsWith(`/${t}`)) cands = cands.concat(v);
      }
      if (!cands.length && !t.includes('/')) cands = idx.byName.get(t) || [];
      const to = cands.length ? pickBest(cands, from) : null;
      return to ? { to, kind: ref.k } : { unresolved: true };
    }
    case 'mdlink': case 'mdembed': {
      const s = ref.s;
      const bases = s.startsWith('/') ? [vp, ''] : [dir, idx.inVault(from) ? vp : null, ''];
      const cands = [];
      for (const b of bases) {
        if (b === null) continue;
        const p = joinRel(b, s.replace(/^\//, ''));
        if (p) cands.push(p, `${p}.md`);
      }
      const to = first(cands);
      if (to) return { to, kind: ref.k };
      return cands.some((c) => dirs.has(c)) ? null : { unresolved: true };
    }
    case 'canvas': {
      const to = first([joinRel(vp, ref.s)]);
      return to ? { to, kind: 'canvas' } : { unresolved: true };
    }
    case 'mention': {
      const s = ref.s.replace(/^\.\//, '');
      const alias = idx.aliases.get(s.replace(/^\//, ''));
      if (alias) return { to: alias, kind: 'alias' };
      if (!s.includes('/') && !/\.[A-Za-z0-9]{1,8}$/.test(s)) return null;
      const to = first([joinRel('', s), joinRel(dir, s), joinRel(vp, s)]);
      return to ? { to, kind: 'mention' } : null;
    }
    case 'import': case 'css': case 'html': {
      const s = ref.s;
      const bases = s.startsWith('/') ? [nearestPackageDir(idx, from), ''] : [dir];
      const exts = ref.k === 'import' ? JS_EXTS : [''];
      const cands = [];
      for (const b of bases) {
        const p = joinRel(b, s.replace(/^\//, ''));
        if (!p) continue;
        for (const e of exts) cands.push(p + e);
        if (ref.k === 'import') {
          for (const e of JS_EXTS.slice(1)) cands.push(`${p}/index${e}`);
          if (/\.[mc]?js$/.test(p)) cands.push(p.replace(/\.([mc]?)js$/, '.$1ts'), p.replace(/\.js$/, '.tsx'));
        }
      }
      const to = first(cands);
      return to ? { to, kind: ref.k } : null;
    }
    case 'mod': {
      const stem = path.posix.basename(from, '.rs');
      const base = ['main', 'lib', 'mod'].includes(stem) ? dir : joinRel(dir, stem);
      const to = first([joinRel(base, `${ref.s}.rs`), joinRel(base, `${ref.s}/mod.rs`)]);
      return to ? { to, kind: 'mod' } : null;
    }
    case 'include': {
      const to = first([joinRel(dir, ref.s)]);
      return to ? { to, kind: 'include' } : null;
    }
    case 'py': {
      const m = ref.s.match(/^(\.*)(.*)$/);
      const parts = m[2] ? m[2].split('.').join('/') : '';
      let bases = [dir, ''];
      if (m[1]) {
        let b = dir;
        for (let i = 1; i < m[1].length; i++) b = path.posix.dirname(b || '.') === '.' ? '' : path.posix.dirname(b);
        bases = [b];
      }
      if (!parts) return null;
      const to = first(bases.flatMap((b) => [joinRel(b, `${parts}.py`), joinRel(b, `${parts}/__init__.py`)]));
      return to ? { to, kind: 'py' } : null;
    }
    case 'config': {
      const s = ref.s.replace(/^\.\//, '');
      const to = first([joinRel(dir, s), joinRel('', s)]);
      return to ? { to, kind: 'config' } : null;
    }
    default: return null;
  }
}

function buildGraph(cfg, files) {
  const idx = makeIndex(cfg, files);
  const edges = new Map();
  const unresolved = [];
  for (const [from, entry] of files) {
    for (const ref of entry.refs || []) {
      const r = resolveRef(ref, from, idx);
      if (!r) continue;
      if (r.unresolved) { unresolved.push({ from, raw: ref.s, kind: ref.k }); continue; }
      if (r.to === from) continue;
      const key = `${from}\0${r.to}`;
      const e = edges.get(key) || { from, to: r.to, labels: new Set(), cat: 9 };
      const [cat, label] = KINDS[r.kind];
      e.labels.add(label);
      e.cat = Math.min(e.cat, cat);
      edges.set(key, e);
    }
  }
  const neighbors = new Map([...files.keys()].map((k) => [k, new Set()]));
  for (const e of edges.values()) { neighbors.get(e.from).add(e.to); neighbors.get(e.to).add(e.from); }
  const groupOf = new Map();
  for (const rel of files.keys()) groupOf.set(rel, neighbors.get(rel).size ? assignGroup(cfg, rel) : unconnectedGroup());
  return { idx, edges: [...edges.values()], unresolved, neighbors, groupOf };
}

function unconnectedGroup() {
  return { key: `group:${UNCONNECTED}`, label: UNCONNECTED, color: '1', order: 1e6 };
}

function assignGroup(cfg, rel) {
  for (const r of cfg.groupRules) {
    if (!r.test(rel)) continue;
    let label = r.label;
    if (r.split) {
      const rest = rel.slice(r.split.length + 1);
      label = label.replace('{dir}', rest.includes('/') ? rest.split('/')[0] : '(top level)');
    }
    return { key: `group:${label}`, label, color: r.color, order: r.order };
  }
  return { key: 'group:Other', label: 'Other', color: undefined, order: 1e5 };
}

// ---------------------------------------------------------------- canvas models

function sanitizeName(s) {
  return s.replace(/[\\/:*?"<>|#^[\]]/g, '-').replace(/\s+/g, ' ').trim();
}

function escMd(s) { return s.replace(/([[\]\\|*_`])/g, '\\$1'); }

function fileUrl(abs) {
  return pathToFileURL(abs).href.replace(/\(/g, '%28').replace(/\)/g, '%29');
}

function wikiTarget(cfg, idx, rel) {
  const vr = idx.vaultRel(rel);
  return vr.endsWith('.md') ? vr.slice(0, -3) : vr;
}

// Vault files become real file nodes (they open in Obsidian). Files outside the vault cannot be
// file nodes, so they become cards whose title is a file:// link that opens the default app.
function fileTemplate(cfg, idx, rel) {
  if (idx.inVault(rel)) return { type: 'file', file: idx.vaultRel(rel) };
  const dir = path.posix.dirname(rel);
  return {
    type: 'text',
    text: `**[${escMd(displayName(idx, rel))}](${fileUrl(path.join(cfg.root, rel))})**\n\`${dir === '.' ? 'repo root' : `${dir}/`}\``,
  };
}

// Common names (SKILL.md, README.md, mod.rs) get their folder in front so cards tell apart.
function displayName(idx, rel) {
  const base = path.posix.basename(rel);
  const dir = path.posix.dirname(rel);
  return (idx.nameCount.get(base) || 0) > 1 && dir !== '.' ? `${path.posix.basename(dir)}/${base}` : base;
}

function outVaultPath(cfg, name) {
  return posix(path.relative(cfg.vaultAbs, path.join(cfg.outAbs, name)));
}

function buildModels(cfg, files, graph) {
  const { idx, edges, neighbors, groupOf, unresolved } = graph;
  const base = cfg.overview_name || 'Project Map';
  const cap = cfg.overview_max_per_group ?? 18;
  const overviewName = `${base}.canvas`;
  const indexName = `${base} Index.md`;
  const counts = [0, 0, 0];
  edges.forEach((e) => counts[e.cat]++);
  const unconnected = [...groupOf.values()].filter((g) => g.label === UNCONNECTED).length;

  const groups = new Map();
  for (const rel of files.keys()) {
    const g = groupOf.get(rel);
    if (!groups.has(g.key)) groups.set(g.key, { ...g, items: [] });
    groups.get(g.key).items.push(rel);
  }
  const ordered = [...groups.values()].sort((a, b) => a.order - b.order || (a.label < b.label ? -1 : 1));
  const degree = (rel) => neighbors.get(rel).size;
  const byDegree = (a, b) => degree(b) - degree(a) || (a < b ? -1 : 1);

  const header = (title, extra) => ({
    key: 'card:header', width: 820, height: 250, template: {
      type: 'text',
      text: [`## ${title}`,
        `Generated by \`tools/project-map\` from ${files.size} files. Move and resize cards freely; positions are kept. Generated cards are rewritten on every update, so add your own notes as new cards.`,
        '**Lines:** purple = explicit link (wikilink, embed, Markdown link, canvas) · green = verified dependency (import, mod, include, config path) · grey "≈" = inferred (path or skill name mentioned in text)',
        extra].join('\n\n'),
    },
  });
  const indexLink = `[[${outVaultPath(cfg, indexName).replace(/\.md$/, '')}|Full index of every file]]`;
  const stats = `${counts[0]} explicit · ${counts[1]} verified · ${counts[2]} inferred connections · ${unconnected} unconnected · ${unresolved.length} unresolved links · ${indexLink}`;

  const models = [];
  const overview = { name: overviewName, groups: [], cards: [header('TraderGO project map', stats)], edges: [] };
  const visible = new Map(); // rel -> node key on the overview (itself or a "more" card)
  const details = [];

  for (const g of ordered) {
    const og = { key: g.key, label: g.label, color: g.color, items: [] };
    if (g.items.length <= cap) {
      for (const rel of g.items) { og.items.push({ key: rel, template: fileTemplate(cfg, idx, rel) }); visible.set(rel, rel); }
    } else {
      const detailName = `${base} – ${sanitizeName(g.label)}.canvas`;
      const shown = g.items.slice().sort(g.label === UNCONNECTED ? undefined : byDegree).slice(0, cap - 1);
      const moreKey = `more:${g.key}`;
      og.items.push({ key: moreKey, template: { type: 'text', text: `### [[${outVaultPath(cfg, detailName)}|Open all ${g.items.length} files →]]\nShowing the ${shown.length} most connected here.` } });
      for (const rel of g.items) visible.set(rel, moreKey);
      for (const rel of shown) { og.items.push({ key: rel, template: fileTemplate(cfg, idx, rel) }); visible.set(rel, rel); }
      details.push({ g, detailName });
    }
    overview.groups.push(og);
  }
  overview.edges = aggregateEdges(edges, visible);
  models.push(overview);

  for (const { g, detailName } of details) {
    const members = new Set(g.items);
    const outside = new Set();
    for (const rel of g.items) for (const n of neighbors.get(rel)) if (!members.has(n)) outside.add(n);
    const m = {
      name: detailName,
      groups: [{ key: g.key, label: g.label, color: g.color, items: g.items.map((rel) => ({ key: rel, template: fileTemplate(cfg, idx, rel) })) }],
      cards: [header(`${g.label} (${g.items.length} files)`, `[[${outVaultPath(cfg, overviewName)}|← Back to the overview]] · ${indexLink}`)],
      edges: [],
    };
    if (outside.size) {
      m.groups.push({ key: `group:${ELSEWHERE}`, label: ELSEWHERE, color: undefined, items: [...outside].sort().map((rel) => ({ key: rel, template: fileTemplate(cfg, idx, rel) })) });
    }
    const keys = new Map([...members, ...outside].map((r) => [r, r]));
    m.edges = aggregateEdges(edges.filter((e) => members.has(e.from) || members.has(e.to)), keys);
    models.push(m);
  }
  return { models, indexName, ordered, details, overviewName };
}

// Map edge endpoints to visible node keys; edges into a collapsed group go to its "more" card.
function aggregateEdges(edges, visible) {
  const out = new Map();
  for (const e of edges) {
    const a = visible.get(e.from);
    const b = visible.get(e.to);
    if (!a || !b || a === b) continue;
    const key = `${a}\0${b}`;
    const agg = out.get(key) || { from: a, to: b, labels: new Set(), cat: 9, n: 0, direct: a === e.from && b === e.to };
    e.labels.forEach((l) => agg.labels.add(l));
    agg.cat = Math.min(agg.cat, e.cat);
    agg.n++;
    out.set(key, agg);
  }
  return [...out.values()].map((e) => ({
    from: e.from, to: e.to, cat: e.cat,
    label: e.direct && e.n === 1 ? [...e.labels].sort().join(' · ') : `${e.n} connections`,
  })).sort((x, y) => (x.from + x.to < y.from + y.to ? -1 : 1));
}

// ---------------------------------------------------------------- layout

function rectsDiffer(a, b) {
  return ['x', 'y', 'width', 'height'].some((k) => Math.round(a[k]) !== Math.round(b[k]));
}

// Compare the canvas on disk with what we wrote last time. Moved generated nodes become pins,
// unknown nodes and edges are the user's own and are kept as they are.
function harvest(model, file, L, renames) {
  let cur;
  try { cur = JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return; }
  const pins = (L.pins[model.name] ||= {});
  const colors = (L.colors[model.name] ||= {});
  const manual = (L.manual[model.name] ||= { nodes: {}, edges: {} });
  const written = L.written[model.name];
  const generatedIds = new Set();
  const keyOfId = new Map();
  for (const g of model.groups) {
    keyOfId.set(nid(g.key), { key: g.key, group: null });
    for (const it of g.items) keyOfId.set(nid(it.key), { key: it.key, group: g.key });
  }
  for (const c of model.cards) keyOfId.set(nid(c.key), { key: c.key, group: null });
  for (const e of model.edges) generatedIds.add(nid(`edge:${e.from}\0${e.to}`));

  const seen = new Set();
  for (const n of cur.nodes || []) {
    seen.add(n.id);
    const w = written?.nodes?.[n.id];
    if (w && !w.manual) {
      const key = renames.get(w.key) ?? w.key;
      if (rectsDiffer(n, w)) pins[key] = { x: n.x, y: n.y, width: n.width, height: n.height, group: w.group };
      if ((n.color ?? null) !== (w.color ?? null)) colors[key] = n.color ?? null;
    } else if (!written && keyOfId.has(n.id)) {
      // State was lost: keep whatever positions the canvas already has.
      const k = keyOfId.get(n.id);
      pins[k.key] = { x: n.x, y: n.y, width: n.width, height: n.height, group: k.group };
    } else {
      manual.nodes[n.id] = n;
    }
  }
  if (written) for (const [id, w] of Object.entries(written.nodes)) if (w.manual && !seen.has(id)) delete manual.nodes[id];
  const seenEdges = new Set();
  for (const e of cur.edges || []) {
    seenEdges.add(e.id);
    const w = written?.edges?.[e.id];
    if (w === false || (!written && generatedIds.has(e.id))) continue;
    // The user's arrow may point at a file that was just renamed.
    for (const [a, b] of renames) {
      if (e.fromNode === nid(a)) e.fromNode = nid(b);
      if (e.toNode === nid(a)) e.toNode = nid(b);
    }
    manual.edges[e.id] = e;
  }
  if (written) for (const [id, isManual] of Object.entries(written.edges)) if (isManual && !seenEdges.has(id)) delete manual.edges[id];
}

function layoutModel(model, L, lay) {
  const pins = (L.pins[model.name] ||= {});
  const colors = (L.colors[model.name] ||= {});
  const slots = (L.slots[model.name] ||= { cols: {}, seq: {}, items: {} });
  const { node_width: nw, node_height: nh, gap_x: gx, gap_y: gy, group_padding: pad, group_gap: gg } = lay;
  const gcols = lay.group_columns;
  const ccols = lay.canvas_columns;
  const colW = gcols * (nw + gx) - gx + 2 * pad;

  const live = new Set(model.groups.map((g) => g.key));
  for (const k of Object.keys(slots.cols)) if (!live.has(k)) { delete slots.cols[k]; delete slots.seq[k]; delete slots.items[k]; }

  // Each node keeps the slot it was first given, so adding a file never shuffles the others.
  const sized = model.groups.map((g) => {
    const its = (slots.items[g.key] ||= {});
    const keys = new Set(g.items.map((i) => i.key));
    const isPinned = (k) => pins[k] && pins[k].group === g.key;
    for (const k of Object.keys(its)) if (!keys.has(k) || isPinned(k)) delete its[k];
    const used = new Set(Object.values(its));
    for (const it of g.items) {
      if (isPinned(it.key) || its[it.key] !== undefined) continue;
      let s = 0;
      while (used.has(s)) s++;
      its[it.key] = s;
      used.add(s);
    }
    const maxSlot = Math.max(-1, ...Object.values(its));
    const rows = Math.max(1, Math.floor(maxSlot / gcols) + 1);
    const usedCols = Math.max(1, Math.min(gcols, maxSlot + 1));
    return { g, its, isPinned, w: usedCols * (nw + gx) - gx + 2 * pad, h: rows * (nh + gy) - gy + 2 * pad };
  });

  // Groups stack in columns; a new group goes to the shortest column and keeps it.
  const heights = new Array(ccols).fill(0);
  let seq = Math.max(0, ...Object.values(slots.seq));
  const known = sized.filter((s) => slots.cols[s.g.key] !== undefined).sort((a, b) => slots.seq[a.g.key] - slots.seq[b.g.key]);
  for (const s of known) if (!pins[s.g.key]) heights[slots.cols[s.g.key] % ccols] += s.h + gg;
  for (const s of sized.filter((x) => slots.cols[x.g.key] === undefined)) {
    const col = heights.indexOf(Math.min(...heights));
    slots.cols[s.g.key] = col;
    slots.seq[s.g.key] = ++seq;
    heights[col] += s.h + gg;
  }

  const groupNodes = [];
  const itemNodes = [];
  const rects = new Map();
  const cursor = new Array(ccols).fill(0);
  const withColor = (key, node) => {
    if (key in colors) { if (colors[key] === null) delete node.color; else node.color = colors[key]; }
    return node;
  };
  for (const s of sized.slice().sort((a, b) => slots.seq[a.g.key] - slots.seq[b.g.key])) {
    const col = slots.cols[s.g.key] % ccols;
    const gp = pins[s.g.key];
    const ox = gp ? gp.x : col * (colW + gg);
    const oy = gp ? gp.y : cursor[col];
    let right = ox + s.w;
    let bottom = oy + s.h;
    for (const it of s.g.items) {
      let r;
      if (s.isPinned(it.key)) {
        const p = pins[it.key];
        r = { x: p.x, y: p.y, width: p.width, height: p.height };
      } else {
        const slot = s.its[it.key];
        r = { x: ox + pad + (slot % gcols) * (nw + gx), y: oy + pad + Math.floor(slot / gcols) * (nh + gy), width: nw, height: nh };
        right = Math.max(right, r.x + r.width + pad);
        bottom = Math.max(bottom, r.y + r.height + pad);
      }
      rects.set(it.key, r);
      itemNodes.push(withColor(it.key, { id: nid(it.key), ...it.template, ...r }));
    }
    let gr = { x: ox, y: oy, width: right - ox, height: bottom - oy };
    if (gp) gr = { x: ox, y: oy, width: Math.max(gr.width, gp.width), height: Math.max(gr.height, gp.height) };
    else cursor[col] = gr.y + gr.height + gg;
    const gnode = { id: nid(s.g.key), type: 'group', label: s.g.label, ...gr };
    if (s.g.color) gnode.color = s.g.color;
    groupNodes.push(withColor(s.g.key, gnode));
  }
  const cardNodes = model.cards.map((c, i) => {
    const p = pins[c.key];
    const r = p ? { x: p.x, y: p.y, width: p.width, height: p.height } : { x: i * (c.width + gg), y: -(c.height + gg), width: c.width, height: c.height };
    rects.set(c.key, r);
    return withColor(c.key, { id: nid(c.key), ...c.template, ...r });
  });

  const edgeNodes = model.edges.map((e) => {
    const a = rects.get(e.from);
    const b = rects.get(e.to);
    const [fromSide, toSide] = sides(a, b);
    const edge = { id: nid(`edge:${e.from}\0${e.to}`), fromNode: nid(e.from), fromSide, toNode: nid(e.to), toSide, toEnd: 'arrow', label: e.label };
    if (CAT_COLORS[e.cat]) edge.color = CAT_COLORS[e.cat];
    return edge;
  });
  return { nodes: [...groupNodes, ...cardNodes, ...itemNodes], edges: edgeNodes };
}

function sides(a, b) {
  const dx = b.x + b.width / 2 - (a.x + a.width / 2);
  const dy = b.y + b.height / 2 - (a.y + a.height / 2);
  if (Math.abs(dx) > Math.abs(dy)) return dx > 0 ? ['right', 'left'] : ['left', 'right'];
  return dy > 0 ? ['bottom', 'top'] : ['top', 'bottom'];
}

// ---------------------------------------------------------------- index note

function buildIndexNote(cfg, files, graph, built) {
  const { idx, neighbors, unresolved, edges } = graph;
  const outCount = new Map();
  const inCount = new Map();
  for (const e of edges) { outCount.set(e.from, (outCount.get(e.from) || 0) + 1); inCount.set(e.to, (inCount.get(e.to) || 0) + 1); }
  const link = (rel) => {
    const name = displayName(idx, rel);
    if (idx.inVault(rel) && !/[[\]|#^]/.test(rel)) return `[[${wikiTarget(cfg, idx, rel)}|${name}]]`;
    if (idx.inVault(rel)) return `[${escMd(name)}](<${idx.vaultRel(rel)}>)`;
    return `[${escMd(name)}](${fileUrl(path.join(cfg.root, rel))})`;
  };
  const detailOf = new Map(built.details.map((d) => [d.g.key, d.detailName]));
  const lines = [
    '---', 'tags: [project-map, generated]', '---',
    '# Project map index', '',
    '> [!info] Generated by `tools/project-map`. Every update overwrites this note, so do not edit it.',
    `> Overview: [[${outVaultPath(cfg, built.overviewName)}|${built.overviewName}]]. Guide: [tools/project-map/README.md](${fileUrl(path.join(cfg.root, 'tools/project-map/README.md'))})`,
    '',
    `${files.size} files, ${edges.length} connections, ${unresolved.length} unresolved links.`,
  ];
  for (const g of built.ordered) {
    lines.push('', `## ${g.label} (${g.items.length})`);
    if (detailOf.has(g.key)) lines.push(`Detail canvas: [[${outVaultPath(cfg, detailOf.get(g.key))}|${detailOf.get(g.key)}]]`, '');
    for (const rel of g.items) {
      const n = neighbors.get(rel).size;
      lines.push(`- ${link(rel)} · \`${rel}\`${n ? ` · ${outCount.get(rel) || 0} out, ${inCount.get(rel) || 0} in` : ''}`);
    }
  }
  if (unresolved.length) {
    lines.push('', '## Unresolved links', '');
    for (const u of unresolved) lines.push(`- \`${u.from}\` → \`${u.raw}\` (${u.kind})`);
  }
  return `${lines.join('\n')}\n`;
}

// ---------------------------------------------------------------- reconcile

function withLock(cfg, fn) {
  fs.mkdirSync(cfg.stateAbs, { recursive: true });
  const lock = path.join(cfg.stateAbs, 'reconcile.lock');
  const deadline = Date.now() + 60_000;
  for (;;) {
    try {
      const fd = fs.openSync(lock, 'wx');
      fs.writeSync(fd, String(process.pid));
      fs.closeSync(fd);
      break;
    } catch (e) {
      if (e.code !== 'EEXIST') throw e;
      const pid = Number(fs.readFileSync(lock, 'utf8') || 0);
      if (!pid || !alive(pid)) { try { fs.unlinkSync(lock); } catch { /* raced */ } continue; }
      if (Date.now() > deadline) throw new Error(`Another reconcile (pid ${pid}) holds ${lock}`);
      sleepSync(200);
    }
  }
  try { return fn(); } finally { try { fs.unlinkSync(lock); } catch { /* gone */ } }
}

function emptyLayout() {
  return { version: 1, pins: {}, colors: {}, slots: {}, manual: {}, written: {}, outputs: [] };
}

function reconcile(cfg, reason = 'manual') {
  return withLock(cfg, () => {
    const t0 = Date.now();
    const cachePath = path.join(cfg.stateAbs, 'cache.json');
    const layoutPath = path.join(cfg.stateAbs, 'layout.json');
    let cache = readJson(cachePath, null);
    if (!cache || cache.config !== cfg.hash) cache = { config: cfg.hash, files: {} };
    const L = { ...emptyLayout(), ...readJson(layoutPath, {}) };

    const files = scan(cfg, gitDir(cfg.root), cache);

    // A file that disappears while an identical file appears is a rename: carry its layout over.
    const renames = new Map();
    const added = [...files.keys()].filter((k) => !cache.files[k]);
    const removed = Object.keys(cache.files).filter((k) => !files.has(k));
    for (const old of removed) {
      const h = cache.files[old].hash;
      const matches = added.filter((a) => files.get(a).hash === h && ![...renames.values()].includes(a));
      if (matches.length === 1) renames.set(old, matches[0]);
    }
    if (renames.size) applyRenames(L, renames);

    const graph = buildGraph(cfg, files);
    const built = buildModels(cfg, files, graph);
    const written = [];
    const outputs = [];
    for (const model of built.models) {
      const file = path.join(cfg.outAbs, model.name);
      harvest(model, file, L, renames);
      const { nodes, edges } = layoutModel(model, L, cfg.layout);
      const manual = L.manual[model.name] || { nodes: {}, edges: {} };
      const ids = new Set(nodes.map((n) => n.id));
      const manualNodes = Object.values(manual.nodes).filter((n) => !ids.has(n.id));
      manualNodes.forEach((n) => ids.add(n.id));
      const edgeIds = new Set(edges.map((e) => e.id));
      const manualEdges = [];
      for (const [id, e] of Object.entries(manual.edges)) {
        if (ids.has(e.fromNode) && ids.has(e.toNode) && !edgeIds.has(id)) manualEdges.push(e);
        else delete manual.edges[id]; // points at a file that no longer exists
      }
      const canvas = { nodes: [...nodes, ...manualNodes], edges: [...edges, ...manualEdges] };
      if (atomicWrite(file, `${JSON.stringify(canvas, null, '\t')}\n`)) written.push(model.name);
      outputs.push(model.name);
      const keyOf = new Map();
      for (const g of model.groups) { keyOf.set(nid(g.key), [g.key, null]); for (const it of g.items) keyOf.set(nid(it.key), [it.key, g.key]); }
      for (const c of model.cards) keyOf.set(nid(c.key), [c.key, null]);
      L.written[model.name] = {
        nodes: Object.fromEntries(canvas.nodes.map((n) => {
          const k = keyOf.get(n.id);
          return [n.id, k ? { key: k[0], group: k[1], x: n.x, y: n.y, width: n.width, height: n.height, color: n.color ?? null } : { manual: true }];
        })),
        edges: Object.fromEntries([...edges.map((e) => [e.id, false]), ...manualEdges.map((e) => [e.id, true])]),
      };
    }
    if (atomicWrite(path.join(cfg.outAbs, built.indexName), buildIndexNote(cfg, files, graph, built))) written.push(built.indexName);
    outputs.push(built.indexName);

    // Remove generated files that are no longer produced (e.g. a detail canvas that is now small).
    for (const old of L.outputs || []) {
      if (outputs.includes(old)) continue;
      try { fs.unlinkSync(path.join(cfg.outAbs, old)); written.push(`-${old}`); } catch { /* already gone */ }
      for (const k of ['pins', 'colors', 'slots', 'manual', 'written']) delete L[k][old];
    }
    L.outputs = outputs;

    atomicWrite(cachePath, JSON.stringify({ config: cfg.hash, files: Object.fromEntries(files) }));
    atomicWrite(layoutPath, `${JSON.stringify(L, null, 1)}\n`);
    const counts = [0, 0, 0];
    graph.edges.forEach((e) => counts[e.cat]++);
    const summary = {
      reason, files: files.size, edges: Object.fromEntries(CAT_NAMES.map((n, i) => [n, counts[i]])),
      unconnected: [...graph.groupOf.values()].filter((g) => g.label === UNCONNECTED).length,
      unresolved: graph.unresolved.length, renames: renames.size, canvases: built.models.length,
      written, ms: Date.now() - t0,
    };
    log(`reconcile (${reason}): ${summary.files} files, ${counts.join('/')} explicit/verified/inferred edges, ` +
      `${summary.unconnected} unconnected, ${summary.unresolved} unresolved, ${summary.renames} renames → ` +
      `${written.length ? `wrote ${written.join(', ')}` : 'no changes'} (${summary.ms} ms)`);
    return summary;
  });
}

function applyRenames(L, renames) {
  for (const name of Object.keys(L.pins)) {
    for (const [a, b] of renames) {
      if (L.pins[name][a]) { L.pins[name][b] = L.pins[name][a]; delete L.pins[name][a]; }
      if (L.colors[name] && a in L.colors[name]) { L.colors[name][b] = L.colors[name][a]; delete L.colors[name][a]; }
    }
  }
  for (const name of Object.keys(L.slots)) {
    for (const its of Object.values(L.slots[name].items || {})) {
      for (const [a, b] of renames) if (a in its) { its[b] = its[a]; delete its[a]; }
    }
  }
  const idMap = new Map([...renames].map(([a, b]) => [nid(a), nid(b)]));
  for (const m of Object.values(L.manual)) {
    for (const e of Object.values(m.edges)) {
      if (idMap.has(e.fromNode)) e.fromNode = idMap.get(e.fromNode);
      if (idMap.has(e.toNode)) e.toNode = idMap.get(e.toNode);
    }
  }
}

// ---------------------------------------------------------------- check

function check(cfg) {
  const L = readJson(path.join(cfg.stateAbs, 'layout.json'), emptyLayout());
  const files = scan(cfg, gitDir(cfg.root), { files: readJson(path.join(cfg.stateAbs, 'cache.json'), { files: {} }).files });
  const problems = [];
  const covered = new Set();
  let nodes = 0;
  let edges = 0;
  const vp = cfg.vaultPrefix;
  for (const name of L.outputs.filter((n) => n.endsWith('.canvas'))) {
    const c = readJson(path.join(cfg.outAbs, name), null);
    if (!c) { problems.push(`${name}: missing or invalid JSON`); continue; }
    const ids = new Set();
    for (const n of c.nodes) {
      if (ids.has(n.id)) problems.push(`${name}: duplicate id ${n.id}`);
      ids.add(n.id);
      for (const k of ['x', 'y', 'width', 'height']) if (!Number.isInteger(n[k])) problems.push(`${name}: node ${n.id} has non-integer ${k}`);
      if (n.type === 'file') {
        if (!fs.existsSync(path.join(cfg.vaultAbs, n.file))) problems.push(`${name}: file node points at missing ${n.file}`);
        covered.add(vp ? `${vp}/${n.file}` : n.file);
      }
      if (n.type === 'text') {
        for (const m of n.text.matchAll(/\]\((file:\/\/[^)\s]+)\)/g)) {
          const abs = fileURLToPath(m[1].replace(/%28/g, '(').replace(/%29/g, ')'));
          if (!fs.existsSync(abs)) problems.push(`${name}: card links to missing ${abs}`);
          covered.add(posix(path.relative(cfg.root, abs)));
        }
      }
    }
    const nodeIds = new Set(ids);
    for (const e of c.edges) {
      if (ids.has(e.id)) problems.push(`${name}: duplicate id ${e.id}`);
      ids.add(e.id);
      if (!nodeIds.has(e.fromNode)) problems.push(`${name}: edge ${e.id} from missing node`);
      if (!nodeIds.has(e.toNode)) problems.push(`${name}: edge ${e.id} to missing node`);
    }
    nodes += c.nodes.length;
    edges += c.edges.length;
  }
  for (const rel of files.keys()) if (!covered.has(rel)) problems.push(`not on any canvas: ${rel}`);
  for (const rel of covered) if (!files.has(rel)) problems.push(`stale node for ${rel}`);
  console.log(`check: ${L.outputs.length} outputs, ${nodes} nodes, ${edges} edges, ${files.size} eligible files, ${covered.size} on canvases`);
  for (const p of problems) console.log(`  PROBLEM ${p}`);
  console.log(problems.length ? `check: ${problems.length} problem(s)` : 'check: OK');
  return problems.length === 0;
}

// ---------------------------------------------------------------- watcher

function pidFile(cfg) { return path.join(cfg.stateAbs, 'watcher.pid'); }
function logFile(cfg) { return path.join(cfg.stateAbs, 'watcher.log'); }

function runningPid(cfg) {
  const pid = Number(readJson(pidFile(cfg), 0));
  return pid && alive(pid) ? pid : 0;
}

function watch(cfg, args) {
  fs.mkdirSync(cfg.stateAbs, { recursive: true });
  const other = runningPid(cfg);
  if (other && other !== process.pid) { console.error(`A watcher is already running (pid ${other}).`); process.exit(1); }
  fs.writeFileSync(pidFile(cfg), String(process.pid));
  const git = gitDir(cfg.root);
  const safe = (reason) => { try { reconcile(cfg, reason); } catch (e) { log(`reconcile failed: ${e.message}`); } };
  safe('startup');

  const debounce = cfg.debounce_ms ?? 1500;
  const settle = cfg.settle_ms ?? 400;
  const pending = new Set();
  let timer = null;
  let gitWaits = 0;
  const schedule = (ms = debounce) => { clearTimeout(timer); timer = setTimeout(flush, ms); };
  const ownPrefixes = cfg.ownDirs.map((d) => `${d}/`);

  // Wait until git has finished (no index.lock) and changed files have stopped growing.
  async function flush() {
    if (git && fs.existsSync(path.join(git, 'index.lock')) && gitWaits++ < 60) return schedule(1000);
    gitWaits = 0;
    const paths = [...pending];
    const stat = () => paths.map((p) => { try { const s = fs.statSync(path.join(cfg.root, p)); return `${s.size}:${s.mtimeMs}`; } catch { return '-'; } });
    const before = stat();
    await new Promise((r) => setTimeout(r, settle));
    if (stat().some((v, i) => v !== before[i])) return schedule();
    paths.forEach((p) => pending.delete(p));
    safe(`change: ${paths.slice(0, 3).join(', ')}${paths.length > 3 ? ` +${paths.length - 3}` : ''}`);
  }

  const onEvent = (_event, filename) => {
    if (!filename) { schedule(); return; }
    const rel = posix(filename.toString());
    if (rel === '.git' || rel.startsWith('.git/') || ownPrefixes.some((p) => rel.startsWith(p)) || cfg.isExcluded(rel)) return;
    pending.add(rel);
    schedule();
  };

  let watcher = null;
  const start = () => {
    try {
      watcher = fs.watch(cfg.root, { recursive: true }, onEvent);
      watcher.on('error', (e) => { log(`watcher error: ${e.message}; restarting in 5 s`); watcher.close(); setTimeout(start, 5000); });
    } catch (e) { log(`cannot watch: ${e.message}; retrying in 10 s`); setTimeout(start, 10_000); }
  };
  const poll = Number(args.poll || 0);
  if (poll > 0) setInterval(() => safe('poll'), poll * 1000);
  else start();
  // Safety net for events the OS dropped (sleep, network drives, huge git checkouts).
  const minutes = cfg.reconcile_minutes ?? 10;
  if (minutes > 0) setInterval(() => safe('periodic'), minutes * 60_000);
  log(`watching ${cfg.root} (${poll > 0 ? `polling every ${poll} s` : 'file events'}); output ${cfg.outAbs}`);

  const stop = () => {
    log('watcher stopping');
    watcher?.close();
    try { if (Number(fs.readFileSync(pidFile(cfg), 'utf8')) === process.pid) fs.unlinkSync(pidFile(cfg)); } catch { /* gone */ }
    process.exit(0);
  };
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
}

function startBackground(cfg, args) {
  const pid = runningPid(cfg);
  if (pid) { console.log(`Watcher already running (pid ${pid}).`); return; }
  fs.mkdirSync(cfg.stateAbs, { recursive: true });
  trimLog(cfg);
  const fd = fs.openSync(logFile(cfg), 'a');
  const extra = ['poll', 'root', 'out', 'state'].flatMap((k) => (args[k] ? [`--${k}`, String(args[k])] : []));
  const child = spawn(process.execPath, [SCRIPT, 'watch', ...extra], { detached: true, stdio: ['ignore', fd, fd], cwd: cfg.root });
  fs.writeFileSync(pidFile(cfg), String(child.pid));
  child.unref();
  console.log(`Watcher started (pid ${child.pid}). Log: ${logFile(cfg)}`);
}

function stopBackground(cfg) {
  const pid = runningPid(cfg);
  if (!pid) { console.log('No watcher running.'); return; }
  process.kill(pid, 'SIGTERM');
  for (let i = 0; i < 50 && alive(pid); i++) sleepSync(100);
  try { fs.unlinkSync(pidFile(cfg)); } catch { /* removed by the watcher */ }
  console.log(alive(pid) ? `Sent SIGTERM to ${pid}, still running.` : `Watcher stopped (pid ${pid}).`);
  if (agentLoaded()) console.log('Note: the LaunchAgent is installed and will start it again at next login (uninstall-agent removes it).');
}

function trimLog(cfg) {
  try {
    const st = fs.statSync(logFile(cfg));
    if (st.size > 5e6) fs.writeFileSync(logFile(cfg), fs.readFileSync(logFile(cfg)).subarray(-1e6));
  } catch { /* no log yet */ }
}

function status(cfg) {
  const pid = runningPid(cfg);
  console.log(pid ? `Watcher running (pid ${pid}).` : 'Watcher not running.');
  if (process.platform === 'darwin') console.log(`LaunchAgent: ${fs.existsSync(agentPlist()) ? (agentLoaded() ? 'installed and loaded' : 'installed, not loaded') : 'not installed'}`);
  try {
    const lines = fs.readFileSync(logFile(cfg), 'utf8').trim().split('\n');
    console.log(`Last log lines (${logFile(cfg)}):\n${lines.slice(-5).join('\n')}`);
  } catch { /* no log */ }
}

// ---------------------------------------------------------------- macOS LaunchAgent

function agentPlist() { return path.join(os.homedir(), 'Library/LaunchAgents', `${AGENT_LABEL}.plist`); }

function agentLoaded() {
  if (process.platform !== 'darwin') return false;
  try { execFileSync('launchctl', ['print', `gui/${process.getuid()}/${AGENT_LABEL}`], { stdio: 'ignore' }); return true; } catch { return false; }
}

function installAgent(cfg) {
  if (process.platform !== 'darwin') throw new Error('install-agent is for macOS only.');
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const envPath = [path.dirname(process.execPath), '/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', '/bin', '/usr/sbin', '/sbin'].join(':');
  fs.mkdirSync(cfg.stateAbs, { recursive: true });
  const plist = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key><string>${AGENT_LABEL}</string>
	<key>ProgramArguments</key>
	<array>
		<string>${esc(process.execPath)}</string>
		<string>${esc(SCRIPT)}</string>
		<string>watch</string>
	</array>
	<key>WorkingDirectory</key><string>${esc(cfg.root)}</string>
	<key>EnvironmentVariables</key><dict><key>PATH</key><string>${esc(envPath)}</string></dict>
	<key>RunAtLoad</key><true/>
	<key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
	<key>ThrottleInterval</key><integer>30</integer>
	<key>ProcessType</key><string>Background</string>
	<key>LowPriorityIO</key><true/>
	<key>Nice</key><integer>10</integer>
	<key>StandardOutPath</key><string>${esc(logFile(cfg))}</string>
	<key>StandardErrorPath</key><string>${esc(logFile(cfg))}</string>
</dict>
</plist>
`;
  stopBackground(cfg);
  if (agentLoaded()) execFileSync('launchctl', ['bootout', `gui/${process.getuid()}/${AGENT_LABEL}`], { stdio: 'ignore' });
  fs.mkdirSync(path.dirname(agentPlist()), { recursive: true });
  fs.writeFileSync(agentPlist(), plist);
  execFileSync('launchctl', ['bootstrap', `gui/${process.getuid()}`, agentPlist()], { stdio: 'inherit' });
  console.log(`Installed and started ${agentPlist()}. Log: ${logFile(cfg)}`);
}

function uninstallAgent() {
  if (process.platform !== 'darwin') throw new Error('uninstall-agent is for macOS only.');
  if (agentLoaded()) execFileSync('launchctl', ['bootout', `gui/${process.getuid()}/${AGENT_LABEL}`], { stdio: 'inherit' });
  if (fs.existsSync(agentPlist())) fs.unlinkSync(agentPlist());
  console.log('LaunchAgent removed.');
}

// ---------------------------------------------------------------- main

function main() {
  const args = parseArgs(process.argv.slice(2));
  const cmd = args._[0] || 'refresh';
  const cfg = loadConfig(args);
  switch (cmd) {
    case 'refresh': reconcile(cfg, 'manual refresh'); break;
    case 'rebuild':
      try { fs.unlinkSync(path.join(cfg.stateAbs, 'cache.json')); } catch { /* none */ }
      if (args['reset-layout']) {
        // Keep the user's own cards and lines; forget positions so the auto layout starts over.
        const L = readJson(path.join(cfg.stateAbs, 'layout.json'), emptyLayout());
        atomicWrite(path.join(cfg.stateAbs, 'layout.json'), JSON.stringify({ ...emptyLayout(), manual: L.manual, outputs: L.outputs }));
        for (const name of L.outputs || []) try { fs.unlinkSync(path.join(cfg.outAbs, name)); } catch { /* gone */ }
      }
      reconcile(cfg, 'rebuild');
      break;
    case 'watch': watch(cfg, args); break;
    case 'start': startBackground(cfg, args); break;
    case 'stop': stopBackground(cfg); break;
    case 'status': status(cfg); break;
    case 'check': process.exitCode = check(cfg) ? 0 : 1; break;
    case 'install-agent': installAgent(cfg); break;
    case 'uninstall-agent': uninstallAgent(); break;
    default:
      console.error(`Unknown command "${cmd}". Commands: refresh, rebuild [--reset-layout], watch [--poll S], start, stop, status, check, install-agent, uninstall-agent`);
      process.exitCode = 2;
  }
}

main();
