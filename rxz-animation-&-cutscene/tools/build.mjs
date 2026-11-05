// Builds dist/rxz-animation-v<version>.zip whose single top-level folder is
// roblox-animation/, ready to drop into .claude/skills.
import { readFileSync, existsSync, readdirSync, statSync, mkdirSync, rmSync, cpSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join, extname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const NAME = "roblox-animation";
const { version } = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));

const SOURCE = resolve(root, "skills", NAME);
const DOCS = ["START-HERE.txt", "README.md", "CHANGELOG.md", "LICENSE.txt"];

// Notes, caches and scratch never travel.
const BAN = new Set([
  "LOCAL.md", "LOCAL.template.md", "__pycache__", ".git", "node_modules",
  "dist", "tools", "work", ".DS_Store", "Thumbs.db",
]);
const BAN_EXT = new Set([".pyc", ".zip"]);
// No setup skill, no config file, no pack dependency: any mention means this
// is not standalone.
const FORBIDDEN = /roblox-skills-setup|LOCAL\.(template\.)?md|rxz-roblox-skills/;

function walk(dir, out) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (BAN.has(entry.name)) continue;
    if (BAN_EXT.has(extname(entry.name))) {
      throw new Error(`refusing to ship ${join(dir, entry.name)}`);
    }
    const path = join(dir, entry.name);
    if (entry.isDirectory()) walk(path, out);
    else out.push(path);
  }
}

if (!existsSync(SOURCE)) throw new Error(`skill not found at ${SOURCE}`);
const missingDocs = DOCS.filter((name) => !existsSync(join(root, name)));
if (missingDocs.length) throw new Error(`missing from product root: ${missingDocs.join(", ")}`);

const files = [];
walk(SOURCE, files);
if (!files.some((f) => f.endsWith(`SKILL.md`))) throw new Error(`${NAME} has no SKILL.md`);

const stageRoot = join(root, "dist", "stage");
const stage = join(stageRoot, NAME);
rmSync(stageRoot, { recursive: true, force: true });
mkdirSync(stage, { recursive: true });
for (const name of readdirSync(join(root, "dist"))) {
  if (/^rxz-animation-v.*\.zip$/.test(name) && name !== `rxz-animation-v${version}.zip`) {
    rmSync(join(root, "dist", name), { force: true });
  }
}

const skip = (src) => {
  const base = src.split(/[\\/]/).pop();
  return !BAN.has(base) && !BAN_EXT.has(extname(base));
};
cpSync(SOURCE, stage, { recursive: true, filter: skip });
for (const doc of DOCS) cpSync(join(root, doc), join(stage, doc));

const staged = [];
walk(stage, staged);

// Standalone check: no SKILL file may mention the setup skill, a LOCAL file or
// the pack. Product docs are exempt; they describe the boundary.
for (const file of files) {
  if (![".md", ".txt", ".py", ".json", ".luau"].includes(extname(file))) continue;
  const hit = readFileSync(file, "utf8").match(FORBIDDEN);
  if (hit) throw new Error(`${file} still references "${hit[0]}" - not standalone`);
}

const skillMd = join(stage, "SKILL.md");
const head = readFileSync(skillMd, "utf8").replace(/\r\n/g, "\n");
if (!head.startsWith(`---\nname: ${NAME}\n`)) {
  throw new Error(`SKILL.md does not declare name: ${NAME}`);
}

// Zip the stage PARENT so the archive contains exactly one folder.
const zip = join(root, "dist", `rxz-animation-v${version}.zip`);
execFileSync("py", [join(root, "tools", "zip.py"), stageRoot, zip], { stdio: "inherit" });

console.log(`  ${NAME} v${version}`);
console.log(`  ${zip}`);
console.log(`  ${staged.length} files, ${Math.round(statSync(zip).size / 1024)} KB`);
