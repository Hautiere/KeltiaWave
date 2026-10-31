import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const pages = ["index.html", "portal-simple.html"];
const assets = pages.flatMap((page) => {
  const htmlPath = resolve(root, page);
  if (!existsSync(htmlPath)) throw new Error(`${page} is missing`);
  const html = readFileSync(htmlPath, "utf8");
  return [...html.matchAll(/(?:src=["']|url\(["']?)(assets\/[^"')]+)/g)].map((match) => match[1]);
});
const missing = [...new Set(assets)].filter((asset) => !existsSync(resolve(root, asset)));
if (missing.length) throw new Error(`Missing portal assets: ${missing.join(", ")}`);

console.log(`KeltiaWave Portal validated (${pages.length} pages, ${new Set(assets).size} local assets).`);
