#!/usr/bin/env node
/**
 * scripts/show-help.mjs
 * Print Makefile targets with their docstring.
 */
import { promises as fs } from "node:fs";
import path from "node:path";

const root = path.resolve(new URL("..", import.meta.url).pathname);
const makefile = await fs.readFile(path.join(root, "Makefile"), "utf8");
const lines = makefile.split(/\r?\n/);
let current = null;
const targets = {};
for (const line of lines) {
  const t = line.match(/^([a-zA-Z0-9_\-]+):\s*([^#]*?)##\s*(.+)$/);
  if (t) {
    targets[t[1]] = t[3].trim();
  }
}
const max = Math.max(...Object.keys(targets).map((k) => k.length));
for (const [k, v] of Object.entries(targets)) {
  console.log(`  ${k.padEnd(max)}  ${v}`);
}
