import { gzipSync } from "node:zlib";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const dist = new URL("../dist/", import.meta.url);
const html = readFileSync(new URL("index.html", dist), "utf8");
const initialAssets = [
  ...html.matchAll(/(?:src|href)="(\/assets\/[^"?]+\.(?:js|css))"/g),
].map((match) => match[1].replace("/assets/", ""));

if (initialAssets.length === 0)
  throw new Error("No initial JavaScript or CSS assets found");
const known = new Set(readdirSync(new URL("assets/", dist)));
let total = 0;
for (const asset of initialAssets) {
  if (!known.has(asset))
    throw new Error(`Referenced build asset is missing: ${asset}`);
  total += gzipSync(
    readFileSync(join(fileURLToPath(new URL("assets/", dist)), asset)),
  ).byteLength;
}

const limit = 250 * 1024;
console.log(
  JSON.stringify({
    initial_assets: initialAssets,
    gzip_bytes: total,
    limit_bytes: limit,
  }),
);
if (total > limit)
  throw new Error(`Home-page bundle is ${total} bytes gzip; limit is ${limit}`);
