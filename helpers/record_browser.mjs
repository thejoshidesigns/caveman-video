#!/usr/bin/env node
/**
 * caveman-video: helpers/record_browser.mjs
 *
 * Automated & Interactive Browser Walkthrough Recorder for Explainer Videos.
 * Captures a clean viewport video AND generates `cursor_events.json` with exact
 * timestamped (x, y, zoom, type, label, keys) events for `render_screen_studio.py`.
 *
 * Modes:
 *   1. Scripted Walkthrough:
 *      node helpers/record_browser.mjs --plan edit/walkthrough.json -o edit/raw_screen.mp4
 *
 *   2. Interactive Live Recording:
 *      node helpers/record_browser.mjs --url https://example.com --interactive -o edit/raw_screen.mp4
 *
 *   3. Generate Template Plan:
 *      node helpers/record_browser.mjs --init-plan edit/walkthrough.json --url http://localhost:3000
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const SAMPLE_PLAN = {
  url: "https://example.com",
  width: 1920,
  height: 1080,
  fps: 30,
  windowTitle: "Product Walkthrough",
  steps: [
    { action: "wait", duration: 0.8 },
    {
      action: "click",
      selector: "a, button",
      zoom: 1.85,
      hold: 2.0,
      label: "STEP 01 // GET STARTED",
      sublabel: "Open the primary action flow"
    },
    {
      action: "keystroke",
      keys: "⌘ + K",
      zoom: 1.6,
      hold: 1.8,
      label: "STEP 02 // QUICK COMMAND"
    },
    { action: "wait", duration: 1.0 }
  ]
};

function parseArgs(argv) {
  const out = {
    plan: null,
    url: null,
    output: "edit/raw_screen.mp4",
    eventsOut: "edit/cursor_events.json",
    interactive: false,
    initPlan: null,
    duration: 20,
    width: 1920,
    height: 1080,
    fps: 30
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--plan") out.plan = argv[++i];
    else if (a === "--url") out.url = argv[++i];
    else if (a === "-o" || a === "--output") out.output = argv[++i];
    else if (a === "--events") out.eventsOut = argv[++i];
    else if (a === "--interactive") out.interactive = true;
    else if (a === "--init-plan") out.initPlan = argv[++i];
    else if (a === "--duration") out.duration = parseFloat(argv[++i]);
    else if (a === "--width") out.width = parseInt(argv[++i], 10);
    else if (a === "--height") out.height = parseInt(argv[++i], 10);
    else if (a === "--help" || a === "-h") {
      console.log(`usage: record_browser.mjs [options]
  --plan <walkthrough.json>   Run scripted browser walkthrough & log cursor_events.json
  --url <https://...>         Target URL (for --interactive or --init-plan)
  --interactive               Open visible browser & record real user clicks/keys
  --init-plan <path.json>     Write a starter walkthrough.json template
  -o, --output <path.mp4>     Output video path (default: edit/raw_screen.mp4)
  --events <path.json>        Output events JSON (default: edit/cursor_events.json)
  --duration <sec>            Max interactive recording duration (default: 20s)`);
      process.exit(0);
    }
  }
  return out;
}

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch {
    try {
      const globalNm = execFileSync("npm", ["root", "-g"], { encoding: "utf8" }).trim();
      return await import(path.join(globalNm, "playwright", "index.mjs"));
    } catch {
      throw new Error(
        "Playwright not found. Install with `npm i -D playwright` or `npx playwright install chromium`."
      );
    }
  }
}

async function run() {
  const args = parseArgs(process.argv);

  if (args.initPlan) {
    const p = path.resolve(args.initPlan);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    const tpl = { ...SAMPLE_PLAN, url: args.url || SAMPLE_PLAN.url };
    fs.writeFileSync(p, JSON.stringify(tpl, null, 2) + "\n", "utf8");
    console.log(`OK | template=${p}`);
    return;
  }

  let plan = null;
  if (args.plan) {
    plan = JSON.parse(fs.readFileSync(path.resolve(args.plan), "utf8"));
  } else if (args.url) {
    plan = {
      url: args.url,
      width: args.width,
      height: args.height,
      fps: args.fps,
      windowTitle: new URL(args.url).host,
      steps: []
    };
  } else {
    console.error("ERR: Provide --plan <walkthrough.json>, --url <url>, or --init-plan <path.json>");
    process.exit(1);
  }

  const width = plan.width || args.width;
  const height = plan.height || args.height;
  const fps = plan.fps || args.fps;
  const outMp4 = path.resolve(args.output);
  const eventsPath = path.resolve(args.eventsOut);
  const tmpVideoDir = path.join(path.dirname(outMp4), ".pw_video_tmp");

  fs.mkdirSync(path.dirname(outMp4), { recursive: true });
  fs.mkdirSync(path.dirname(eventsPath), { recursive: true });
  fs.mkdirSync(tmpVideoDir, { recursive: true });

  const { chromium } = await loadPlaywright();
  const browser = await chromium.launch({ headless: !args.interactive });
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    recordVideo: { dir: tmpVideoDir, size: { width, height } }
  });

  const page = await context.newPage();
  const t0 = Date.now();
  const nowSec = () => Number(((Date.now() - t0) / 1000).toFixed(3));
  const events = [];

  if (args.interactive) {
    await page.exposeFunction("__cavemanLogEvent", (evt) => {
      events.push({ ...evt, t: nowSec() });
    });
    await page.addInitScript(() => {
      window.addEventListener(
        "mousedown",
        (e) => {
          window.__cavemanLogEvent({
            type: "click",
            x: Math.round(e.clientX),
            y: Math.round(e.clientY),
            duration: 2.0,
            zoom: 1.85,
            label: (e.target?.innerText || e.target?.getAttribute?.("aria-label") || "ACTION")
              .trim()
              .slice(0, 32)
              .toUpperCase()
          });
        },
        true
      );
      window.addEventListener(
        "keydown",
        (e) => {
          if (e.metaKey || e.ctrlKey || e.key === "Enter" || e.key === "Escape") {
            const mods = [
              e.metaKey ? "⌘" : "",
              e.ctrlKey ? "Ctrl" : "",
              e.shiftKey ? "⇧" : "",
              e.altKey ? "⌥" : "",
              e.key.length === 1 ? e.key.toUpperCase() : e.key
            ].filter(Boolean);
            window.__cavemanLogEvent({
              type: "keystroke",
              x: Math.round(window.innerWidth / 2),
              y: Math.round(window.innerHeight / 2),
              duration: 1.6,
              zoom: 1.35,
              keys: mods.join(" + ")
            });
          }
        },
        true
      );
    });
  }

  await page.goto(plan.url, { waitUntil: "domcontentloaded" });

  if (args.interactive) {
    await page.waitForTimeout(args.duration * 1000);
  } else {
    let curX = Math.round(width / 2);
    let curY = Math.round(height / 2);

    for (const step of plan.steps || []) {
      const action = step.action || "wait";
      if (action === "wait") {
        await page.waitForTimeout((step.duration || 1.0) * 1000);
      } else if (action === "goto") {
        await page.goto(step.url, { waitUntil: "domcontentloaded" });
      } else if (action === "click" || action === "type" || action === "spotlight") {
        let targetX = step.x ?? curX;
        let targetY = step.y ?? curY;
        let boxW = step.w ?? 320;
        let boxH = step.h ?? 120;

        if (step.selector) {
          const loc = page.locator(step.selector).first();
          await loc.waitFor({ state: "visible", timeout: 8000 }).catch(() => {});
          const box = await loc.boundingBox();
          if (box) {
            targetX = Math.round(box.x + box.width / 2);
            targetY = Math.round(box.y + box.height / 2);
            boxW = Math.round(box.width + 32);
            boxH = Math.round(box.height + 32);
          }
        }

        await page.mouse.move(targetX, targetY, { steps: 18 });
        curX = targetX;
        curY = targetY;

        const tEvent = nowSec();
        const holdDur = step.hold || step.duration || 2.2;

        if (action === "click") {
          await page.mouse.click(targetX, targetY);
          events.push({
            t: tEvent,
            duration: holdDur,
            type: "click",
            x: targetX,
            y: targetY,
            zoom: step.zoom || 1.85,
            label: step.label || "",
            sublabel: step.sublabel || ""
          });
        } else if (action === "type") {
          await page.mouse.click(targetX, targetY);
          const text = step.text || "";
          await page.keyboard.type(text, { delay: step.delayMs || 55 });
          events.push({
            t: tEvent,
            duration: Math.max(holdDur, (text.length * (step.delayMs || 55)) / 1000 + 0.8),
            type: "click",
            x: targetX,
            y: targetY,
            zoom: step.zoom || 1.95,
            label: step.label || "",
            sublabel: step.sublabel || ""
          });
        } else if (action === "spotlight") {
          events.push({
            t: tEvent,
            duration: holdDur,
            type: "spotlight",
            x: targetX,
            y: targetY,
            w: boxW,
            h: boxH,
            zoom: step.zoom || 1.55,
            label: step.label || "",
            sublabel: step.sublabel || ""
          });
        }
        await page.waitForTimeout(holdDur * 1000);
      } else if (action === "keystroke") {
        const tEvent = nowSec();
        const holdDur = step.hold || step.duration || 1.8;
        if (step.playwrightKey) {
          await page.keyboard.press(step.playwrightKey);
        }
        events.push({
          t: tEvent,
          duration: holdDur,
          type: "keystroke",
          x: step.x ?? curX,
          y: step.y ?? curY,
          zoom: step.zoom || 1.4,
          keys: step.keys || "⌘ + K",
          label: step.label || ""
        });
        await page.waitForTimeout(holdDur * 1000);
      } else if (action === "scroll") {
        await page.mouse.wheel(step.deltaX || 0, step.deltaY || 480);
        await page.waitForTimeout((step.duration || 1.2) * 1000);
      }
    }
  }

  const videoObj = page.video();
  await context.close();
  await browser.close();

  const webmPath = await videoObj.path();
  execFileSync(
    "ffmpeg",
    [
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-i",
      webmPath,
      "-vf",
      `fps=${fps},scale=${width}:${height}:flags=lanczos,format=yuv420p`,
      "-c:v",
      "libx264",
      "-preset",
      "fast",
      "-crf",
      "16",
      "-movflags",
      "+faststart",
      outMp4
    ],
    { stdio: "inherit" }
  );

  fs.rmSync(tmpVideoDir, { recursive: true, force: true });

  const payload = {
    width,
    height,
    fps,
    windowTitle: plan.windowTitle || plan.url || "Screen Walkthrough",
    events
  };
  fs.writeFileSync(eventsPath, JSON.stringify(payload, null, 2) + "\n", "utf8");

  console.log(
    `OK | video=${path.basename(outMp4)} | events=${events.length} (${path.basename(eventsPath)}) | res=${width}x${height}@${fps}`
  );
}

run().catch((err) => {
  console.error("ERR:", err.message || err);
  process.exit(1);
});
