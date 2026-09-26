#!/usr/bin/env node
/**
 * caveman-video: Cross-Agent CLI Installer (bin/install.js)
 *
 * Installs the 7 progressive-disclosure caveman-video skill packs into:
 *   - Workspace: ./.agents/skills/
 *   - Global:    ~/.agents/skills/ and ~/.claude/skills/
 *
 * Usage:
 *   node bin/install.js --workspace [target_dir]
 *   node bin/install.js --global
 *   node bin/install.js --status
 *   node bin/install.js --uninstall
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");
const SKILLS_DIR = path.join(REPO_ROOT, "skills");
const REGISTRY_PATH = path.join(SKILLS_DIR, "registry.json");

const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, "utf8"));
const SKILL_NAMES = (registry.skills || []).map((s) => s.name);
const TOTAL_CONSOLIDATED = (registry.skills || []).reduce(
  (acc, s) => acc + (s.consolidates ? s.consolidates.length : 0),
  0
);

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function copyOrLinkSkill(skillName, targetSkillsRoot, useSymlink = true) {
  const src = path.join(SKILLS_DIR, skillName);
  const dest = path.join(targetSkillsRoot, skillName);
  ensureDir(targetSkillsRoot);

  if (fs.existsSync(dest) || fs.lstatSync(dest, { throwIfNoEntry: false })) {
    fs.rmSync(dest, { recursive: true, force: true });
  }

  if (useSymlink) {
    try {
      const type = process.platform === "win32" ? "junction" : "dir";
      fs.symlinkSync(src, dest, type);
    } catch {
      fs.cpSync(src, dest, { recursive: true });
    }
  } else {
    fs.cpSync(src, dest, { recursive: true });
  }
  return dest;
}

function installToTarget(targetRoot, label) {
  console.log(`\n[caveman-video] Installing ${SKILL_NAMES.length} skill packs -> ${label} (${targetRoot})`);
  for (const name of SKILL_NAMES) {
    const dest = copyOrLinkSkill(name, targetRoot, true);
    console.log(`  + ${name.padEnd(28)} -> ${dest}`);
  }
}

function uninstallFromTarget(targetRoot, label) {
  console.log(`\n[caveman-video] Removing skill packs from ${label} (${targetRoot})`);
  for (const name of SKILL_NAMES) {
    const dest = path.join(targetRoot, name);
    if (fs.existsSync(dest) || fs.lstatSync(dest, { throwIfNoEntry: false })) {
      fs.rmSync(dest, { recursive: true, force: true });
      console.log(`  - Removed ${name}`);
    }
  }
}

function showStatus(workspaceDir) {
  const targets = [
    { label: "Workspace (.agents/skills)", dir: path.join(workspaceDir, ".agents", "skills") },
    { label: "Global (~/.agents/skills)", dir: path.join(os.homedir(), ".agents", "skills") },
    { label: "Claude (~/.claude/skills)", dir: path.join(os.homedir(), ".claude", "skills") }
  ];

  console.log("=== caveman-video Skill Pack Status ===");
  for (const t of targets) {
    console.log(`\n${t.label}: ${t.dir}`);
    for (const name of SKILL_NAMES) {
      const p = path.join(t.dir, name, "SKILL.md");
      const ok = fs.existsSync(p);
      console.log(`  [${ok ? "INSTALLED" : "MISSING  "}] ${name}`);
    }
  }
  console.log(`\nTotal consolidated skills: ${TOTAL_CONSOLIDATED} -> ${SKILL_NAMES.length} packs`);
}

const args = process.argv.slice(2);
const modeGlobal = args.includes("--global") || args.includes("-g");
const modeWorkspace = args.includes("--workspace") || args.includes("-w");
const modeUninstall = args.includes("--uninstall");
const modeStatus = args.includes("--status") || args.length === 0;

const customDirArg = args.find((a) => !a.startsWith("-"));
const workspaceDir = customDirArg ? path.resolve(customDirArg) : process.cwd();

if (modeUninstall) {
  uninstallFromTarget(path.join(workspaceDir, ".agents", "skills"), "Workspace");
  uninstallFromTarget(path.join(os.homedir(), ".agents", "skills"), "Global (~/.agents)");
  uninstallFromTarget(path.join(os.homedir(), ".claude", "skills"), "Claude (~/.claude)");
  process.exit(0);
}

if (modeWorkspace) {
  installToTarget(path.join(workspaceDir, ".agents", "skills"), "Workspace (.agents/skills)");
}

if (modeGlobal) {
  installToTarget(path.join(os.homedir(), ".agents", "skills"), "Global (~/.agents/skills)");
  installToTarget(path.join(os.homedir(), ".claude", "skills"), "Claude (~/.claude/skills)");
}

if (modeStatus || modeWorkspace || modeGlobal) {
  console.log("");
  showStatus(workspaceDir);
}
