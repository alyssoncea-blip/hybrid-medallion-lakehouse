#!/usr/bin/env node
/**
 * scripts/validate-mermaid.mjs
 *
 * Extracts every ```mermaid fenced block from all .md files, renders each
 * to SVG with @mermaid-js/mermaid-cli, and reports any syntax errors.
 *
 * Usage: node scripts/validate-mermaid.mjs
 */

import { promises as fs } from "node:fs";
import path from "node:path";
import { exec } from "node:child_process";
import { promisify } from "node:util";
import os from "node:os";
import { fileURLToPath } from "node:url";

const execAsync = promisify(exec);
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");

async function* walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const e of entries) {
    if (e.name === "node_modules" || e.name === ".git" || e.name === "target" || e.name === "dbt_packages") continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else if (e.isFile() && p.endsWith(".md")) yield p;
  }
}

function extractMermaidBlocks(markdown) {
  const blocks = [];
  const regex = /```mermaid\r?\n([\s\S]*?)```/g;
  let match;
  while ((match = regex.exec(markdown)) !== null) {
    blocks.push(match[1]);
  }
  return blocks;
}

async function main() {
  console.log(`Scanning for .md files in: ${root}`);
  const files = [];
  for await (const f of walk(root)) files.push(f);
  console.log(`Found ${files.length} markdown files`);

  // Puppeteer needs --no-sandbox on GitHub Actions (running as root).
  // The config file is committed at scripts/puppeteer-config.json.
  const puppeteerConfig = path.join(__dirname, "puppeteer-config.json");

  // Prefer the local mmdc binary (npm ci installs it); fall back to npx
  // with an explicit version. Built as a shell string via exec() so
  // Windows .cmd shims (mmdc.cmd / npx.cmd) resolve correctly.
  const quote = (s) => `"${String(s).replace(/"/g, '\\"')}"`;
  const localMmdc = path.join(__dirname, "..", "node_modules", ".bin", process.platform === "win32" ? "mmdc.cmd" : "mmdc");
  let mmdcPrefix;
  try {
    await fs.access(localMmdc);
    mmdcPrefix = `${quote(localMmdc)} -p ${quote(puppeteerConfig)}`;
  } catch {
    mmdcPrefix = `npx --yes -p "@mermaid-js/mermaid-cli@10.9.1" mmdc -p ${quote(puppeteerConfig)}`;
  }
  
  let total = 0;
  let failed = 0;
  for (const file of files) {
    const content = await fs.readFile(file, "utf8");
    const blocks = extractMermaidBlocks(content);
    for (const [i, block] of blocks.entries()) {
      total++;
      const tmp = path.join(os.tmpdir(), `mermaid-${Date.now()}-${i}.mmd`);
      const out = `${tmp}.svg`;
      await fs.writeFile(tmp, block, "utf8");
      try {
        await execAsync(`${mmdcPrefix} -i ${quote(tmp)} -o ${quote(out)} -q`);
        console.log(`  OK  ${path.relative(root, file)} [block ${i + 1}]`);
      } catch (err) {
        failed++;
        console.error(`  FAIL ${path.relative(root, file)} [block ${i + 1}]`);
        console.error(err.stderr || err.stdout || err.message);
      } finally {
        await fs.unlink(tmp).catch(() => {});
        await fs.unlink(out).catch(() => {});
      }
    }
  }
  console.log(`\nRendered ${total - failed}/${total} Mermaid blocks successfully.`);
  if (failed > 0) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
