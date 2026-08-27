import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const htmlPath = resolve(root, "index.html");
if (!existsSync(htmlPath)) throw new Error("index.html is missing");

const html = readFileSync(htmlPath, "utf8");
const assets = [...html.matchAll(/(?:src=["']|url\(["']?)(assets\/[^"')]+)/g)].map((match) => match[1]);
const missing = [...new Set(assets)].filter((asset) => !existsSync(resolve(root, asset)));
if (missing.length) throw new Error(`Missing portal assets: ${missing.join(", ")}`);

console.log(`KeltiaWave Portal validated (${new Set(assets).size} local assets).`);
