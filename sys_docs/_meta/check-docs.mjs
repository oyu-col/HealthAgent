import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const meta = path.dirname(fileURLToPath(import.meta.url));
const docs = path.dirname(meta);
const root = path.dirname(docs);
const snapshotFlag = process.argv.indexOf('--snapshot-name');
const snapshotName = snapshotFlag >= 0 ? process.argv[snapshotFlag + 1] : 'source-snapshot-phase-12.json';
if (!/^source-snapshot(?:-[a-z0-9-]+)?\.json$/.test(snapshotName || '')) throw new Error('Invalid snapshot filename');
const snapshotPath = path.join(meta, snapshotName);
const ignored = new Set(['.venv', 'node_modules', 'dist', 'test-results', 'playwright-report', '__pycache__', '.pytest_cache', '.pytest-tmp', '.ruff_cache', '.vite', '.pnpm-store', 'build']);
const files = [];
const directories = [''];
const slash = p => p.split(path.sep).join('/');
function walk(relative) {
  directories.push(relative);
  for (const entry of fs.readdirSync(path.join(root, relative), { withFileTypes: true })) {
    if (ignored.has(entry.name) || entry.name.startsWith('.smoke-') || entry.name.startsWith('.benchmark-') || entry.name.startsWith('.pytest-tmp-') || entry.name.endsWith('.egg-info') || (relative === 'benchmark' && entry.name === 'runs')) continue;
    const child = slash(path.join(relative, entry.name));
    if (entry.isDirectory()) walk(child);
    else if (entry.isFile()) files.push(child);
  }
}
for (const name of ['.env', '.env.example', '.gitignore', 'AGENTS.md', 'README.md', 'HEALTH_AGENT_SPEC.md']) {
  if (fs.existsSync(path.join(root, name))) files.push(name);
}
for (const name of ['backend', 'frontend', 'docs', 'benchmark']) walk(name);
files.sort(); directories.sort();
const hash = relative => crypto.createHash('sha256').update(fs.readFileSync(path.join(root, relative))).digest('hex');
// Never read or hash .env: the guide documents the public configuration contract only.
const inventory = files.map(source => ({ source, guide: `${source}.md`, sha256: source === '.env' ? null : hash(source), mode: source === '.env' ? 'schema-only-no-content-read' : 'source-reviewed' }));
if (process.argv.includes('--index')) {
  const lines = ['# HealthAgent 逐文件索引', '', '- 对应目录：`HealthAgent/`', '- 索引依据：当前实际文件清单；不读取 `.env` 内容。', `- 覆盖：${files.length} 个文件、${directories.length} 个目录（含项目根及空目录）。`, '', '本索引由 `_meta/check-docs.mjs --index` 生成。目录链接打开其职责说明，文件链接打开逐文件说明；原始 README.md 的说明名为 README.md.md。', '', '[返回总览](README.md)', ''];
  for (const directory of directories) {
    const guide = directory ? `${directory}/README.md` : 'README.md';
    lines.push(`## ${directory || 'HealthAgent 根目录'}`, '', `[目录职责与上下游](${guide})`, '', '| 原始文件 | 中文说明 |', '| --- | --- |');
    const children = files.filter(source => slash(path.dirname(source)) === (directory || '.'));
    for (const source of children) lines.push(`| \`${source}\` | [${path.basename(source)} 说明](${source}.md) |`);
    if (!children.length) lines.push('| 本目录没有直接文件 | 请阅读目录说明及下级目录 |');
    lines.push('');
  }
  fs.writeFileSync(path.join(docs, '文件索引.md'), lines.join('\n'));
}
if (process.argv.includes('--snapshot')) {
  if (fs.existsSync(snapshotPath)) throw new Error('Refusing to overwrite the original source snapshot');
  fs.writeFileSync(snapshotPath, JSON.stringify({ recorded_at: new Date().toISOString(), files: inventory, directories }, null, 2) + '\n');
  console.log(JSON.stringify({ snapshot: slash(path.relative(root, snapshotPath)), files: files.length, directories: directories.length }));
  process.exit(0);
}
const snapshot = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));
const failures = [];
for (const row of inventory) {
  const guidePath = path.join(docs, row.guide);
  if (!fs.existsSync(guidePath)) failures.push(`Missing file guide: ${row.guide}`);
  else {
    const guide = fs.readFileSync(guidePath, 'utf8');
    if (!guide.includes(`对应源码：\`${row.source}\``)) failures.push(`Source metadata mismatch: ${row.guide}`);
    if (!/核对日期：\d{4}-\d{2}-\d{2}/.test(guide)) failures.push(`Missing review date: ${row.guide}`);
  }
  const old = snapshot.files.find(item => item.source === row.source);
  if (!old) failures.push(`Source added after snapshot: ${row.source}`);
  else if (old.sha256 !== row.sha256) failures.push(`Source changed after snapshot: ${row.source}`);
}
for (const row of snapshot.files) if (!files.includes(row.source)) failures.push(`Source removed: ${row.source}`);
for (const directory of directories) {
  if (!fs.existsSync(path.join(docs, directory, 'README.md'))) failures.push(`Missing directory guide: ${directory || '.'}/README.md`);
}
if (JSON.stringify(snapshot.directories) !== JSON.stringify(directories)) failures.push('Source directory inventory changed after snapshot');
const pages = [];
function scan(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) scan(full);
    else if (entry.name.endsWith('.md')) pages.push(full);
  }
}
scan(docs);
let links = 0;
for (const page of pages) {
  const content = fs.readFileSync(page, 'utf8');
  if (content.includes('\uFFFD')) failures.push(`Invalid UTF-8 replacement character: ${slash(path.relative(docs, page))}`);
  if (/^(<<<<<<< |=======\s*$|>>>>>>> )/m.test(content)) failures.push(`Merge marker: ${page}`);
  if ((content.match(/^```/gm) || []).length % 2) failures.push(`Unbalanced code fence: ${page}`);
  for (const match of content.matchAll(/!?\[[^\]\n]*\]\(([^)\n]+)\)/g)) {
    let target = match[1].trim().replace(/^<|>$/g, '');
    if (/^(https?:|mailto:|#|app:|codex:)/i.test(target)) continue;
    target = decodeURIComponent(target.split('#')[0]);
    if (!target) continue;
    links++;
    if (!fs.existsSync(path.resolve(path.dirname(page), target))) failures.push(`Broken link ${slash(path.relative(docs, page))} -> ${target}`);
  }
}
const report = { checked_at: new Date().toISOString(), snapshot: snapshotName, status: failures.length ? 'failed' : 'passed', source_files: files.length, source_directories: directories.length, file_guides: inventory.filter(row => fs.existsSync(path.join(docs, row.guide))).length, directory_guides: directories.filter(dir => fs.existsSync(path.join(docs, dir, 'README.md'))).length, markdown_pages: pages.length, local_links_checked: links, nonsecret_source_hashes_checked: inventory.filter(row => row.sha256).length, env_content_read: false, scope: 'Documentation coverage, local link existence, UTF-8, fences and source against the named snapshot; this command does not execute application tests', failures };
fs.writeFileSync(path.join(meta, 'coverage.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
process.exitCode = failures.length ? 1 : 0;
