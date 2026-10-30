#!/usr/bin/env node
// Tiny zero-dependency README builder.  node build/build.mjs [--check]
// Syntax: {{> path key="lit" key=var}}  {{ var }}  {{ var|default }}  {{#each list}}..{{/each}}  {{#if var}}..{{/if}}
import { readFileSync, writeFileSync, existsSync, readdirSync, mkdirSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'src'), OUT = join(ROOT, 'README.md');
const HEADER = '<!-- GENERATED FILE - edit src/ instead (node build/build.mjs) -->\n';
const used = new Set();
const fail = (m) => { console.error(`build error: ${m}`); process.exit(1); };

function lookup(scopes, path, where, soft = false) {
  const miss = () => soft ? undefined : fail(`missing var "${path}" in ${where}`);
  const [head, ...rest] = path.split('.');
  for (let i = scopes.length - 1; i >= 0; i--) {
    if (head in scopes[i]) {
      let v = scopes[i][head];
      for (const k of rest) { if (v == null || !(k in v)) return miss(); v = v[k]; }
      return v;
    }
  }
  return miss();
}
function parseArgs(str, scopes, where) {
  const out = {}; const re = /(\w+)=(?:"([^"]*)"|([\w.]+))/g; let m;
  while ((m = re.exec(str))) { const v = m[2] !== undefined ? m[2] : lookup(scopes, m[3], where, true); if (v !== undefined) out[m[1]] = v; }
  return out;
}
function partial(name, scopes, where) {
  const file = join(SRC, name + '.md');
  if (!existsSync(file)) fail(`missing partial "${name}" (included from ${where})`);
  used.add(relative(SRC, file));
  return render(readFileSync(file, 'utf8').replace(/\n$/, ''), scopes, name);
}
// find the matching {{/tag}} for a block starting at index i
function block(tpl, i, tag) {
  const re = new RegExp(`{{(#${tag}\\s[^}]*|/${tag})}}`, 'g'); re.lastIndex = i; let depth = 1, m;
  while ((m = re.exec(tpl))) { depth += m[1][0] === '#' ? 1 : -1; if (!depth) return [m.index, re.lastIndex]; }
  fail(`unclosed {{#${tag}}}`);
}
function render(tpl, scopes, where) {
  let out = '', i = 0; const re = /{{\s*([>#\/]?)\s*([^}]*?)\s*}}/g; let m;
  while ((re.lastIndex = i, m = re.exec(tpl))) {
    out += tpl.slice(i, m.index); const [kind, body] = [m[1], m[2]];
    if (kind === '>') { const [name, ...a] = body.split(/\s+/); const args = parseArgs(a.join(' '), scopes, where);
      if (args.name !== undefined && !('alt' in args)) { const auto = lookup(scopes, 'alts', where)[args.name]; if (auto === undefined) fail(`no alt for image "${args.name}" (add it to alts.json via gen_assets.py or pass alt="")`); args.alt = auto; }
      if (typeof args.alt === 'string') args.alt = args.alt.replace(/&(?!amp;|quot;|lt;|#\d+;)/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
      out += partial(name, [...scopes, args], where); i = re.lastIndex; }
    else if (kind === '#') {
      const [tag, expr] = body.split(/\s+/); const [s, e] = block(tpl, re.lastIndex, tag); const inner = tpl.slice(re.lastIndex, s);
      const v = lookup(scopes, expr, where);
      if (tag === 'each') { if (!Array.isArray(v)) fail(`"${expr}" is not a list in ${where}`); v.forEach((it, n) => out += render(inner, [...scopes, { this: it, '@index': n }], where)); }
      else if (tag === 'if') { if (v) out += render(inner, scopes, where); }
      else fail(`unknown block #${tag} in ${where}`);
      i = e;
    } else if (kind === '/') fail(`stray {{/${body}}} in ${where}`);
    else { const [p, def] = body.split('|'); let v = lookup(scopes, p, where, def !== undefined);
      if (def !== undefined && (v === undefined || v === '')) v = def; out += v; i = re.lastIndex; }
  }
  return out + tpl.slice(i);
}
function walk(d) { return readdirSync(d, { withFileTypes: true }).flatMap(f => f.isDirectory() ? walk(join(d, f.name)) : f.name.endsWith('.md') && !f.name.endsWith('.tpl.md') ? [relative(SRC, join(d, f.name))] : []); }

const data = JSON.parse(readFileSync(join(SRC, 'data', 'site.json'), 'utf8'));
// alts.json: build/gen_assets.py, gen_activity.py 가 SVG 안 글자로 만든 대체 텍스트. picture 에 alt 를 주지 않으면 이름으로 찾아 넣습니다.
const ALTS_FILE = join(SRC, 'data', 'alts.json');
data.alts = existsSync(ALTS_FILE) ? JSON.parse(readFileSync(ALTS_FILE, 'utf8')) : {};
const result = HEADER + render(readFileSync(join(SRC, 'README.tpl.md'), 'utf8'), [data], 'README.tpl.md');
const unused = walk(SRC).filter(f => !used.has(f));
for (const f of unused) console.warn(`${f.startsWith('partials') ? 'error' : 'warn'}: unused ${f}`);
if (unused.some(f => f.startsWith('partials'))) process.exit(1);
if (process.argv.includes('--check')) {
  const cur = existsSync(OUT) ? readFileSync(OUT, 'utf8') : '';
  if (cur !== result) { console.error('check failed: README.md is out of date, run node build/build.mjs'); process.exit(1); }
  console.log('check ok: README.md is up to date');
} else { mkdirSync(dirname(OUT), { recursive: true }); writeFileSync(OUT, result); console.log(`wrote ${relative(ROOT, OUT)} (${result.length} chars)`); }
