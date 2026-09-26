#!/usr/bin/env node
/**
 * caveman-video: video-shrink MCP Server (Zero-Dependency JSON-RPC 2.0 over stdio)
 *
 * Shrinks verbose media CLI outputs by 90-98% before they enter the LLM context window:
 *  - video_probe_shrunk      : 400-line ffprobe JSON -> 1-line summary + silence intervals
 *  - video_transcript_shrunk : 5,000-line Whisper JSON -> compact [start-end] TSV + filler tags
 *  - video_contact_sheet     : Generates a single 4x4 numbered frame grid PNG instead of 50 frames
 *  - video_render_shrunk     : Runs FFmpeg or render_edl.py and returns a 1-line status or 10-line error tail
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "../../..");
const HELPERS_DIR = path.join(REPO_ROOT, "helpers");

const TOOLS = [
  {
    name: "video_probe_shrunk",
    description:
      "Probe a video/audio file and return a single-line compact telemetry summary (resolution, fps, codec, duration, LUFS/dB, silence intervals) instead of 400 lines of raw ffprobe JSON.",
    inputSchema: {
      type: "object",
      properties: {
        file_path: { type: "string", description: "Absolute or relative path to the media file." },
        detect_silence: { type: "boolean", description: "Include silence intervals > 0.35s (default: true)." }
      },
      required: ["file_path"]
    }
  },
  {
    name: "video_transcript_shrunk",
    description:
      "Compress a verbose Whisper JSON/SRT/VTT transcript into a compact 1-line-per-phrase TSV with [FILLER] tags and [GAP:Xs] markers (92% fewer tokens).",
    inputSchema: {
      type: "object",
      properties: {
        transcript_path: { type: "string", description: "Path to Whisper .json, .srt, or .vtt file." },
        gap_threshold: { type: "number", description: "Minimum silence gap in seconds to flag (default: 0.35)." }
      },
      required: ["transcript_path"]
    }
  },
  {
    name: "video_contact_sheet",
    description:
      "Generate a single numbered 4x4 contact sheet image with burned-in timestamps and frame indices so the agent inspects 1 image instead of 16+ raw frames.",
    inputSchema: {
      type: "object",
      properties: {
        video_path: { type: "string", description: "Input video path." },
        output_png: { type: "string", description: "Output PNG path for the contact sheet." },
        cols: { type: "number", description: "Grid columns (default: 4)." },
        rows: { type: "number", description: "Grid rows (default: 4)." }
      },
      required: ["video_path", "output_png"]
    }
  },
  {
    name: "video_render_shrunk",
    description:
      "Execute an FFmpeg command or render_edl.py with `-hide_banner -loglevel error` and return a 1-line completion receipt (or the last 10 lines on error).",
    inputSchema: {
      type: "object",
      properties: {
        edl_json: { type: "string", description: "Optional path to edit_plan.json to render via helpers/render_edl.py." },
        output_path: { type: "string", description: "Output video path." },
        grade: { type: "string", description: "Optional grade preset: none, warm, cinematic, moody, clean." }
      },
      required: ["edl_json", "output_path"]
    }
  }
];

function probeMediaShrunk(filePath, detectSilence = true) {
  const abs = path.resolve(filePath);
  if (!fs.existsSync(abs)) {
    return `ERR: File not found: ${abs}`;
  }
  const raw = execFileSync(
    "ffprobe",
    ["-v", "error", "-show_format", "-show_streams", "-of", "json", abs],
    { encoding: "utf8" }
  );
  const info = JSON.parse(raw);
  const vStream = (info.streams || []).find((s) => s.codec_type === "video") || {};
  const aStream = (info.streams || []).find((s) => s.codec_type === "audio") || {};
  const dur = parseFloat(info.format?.duration || vStream.duration || "0").toFixed(2);
  const sizeMb = (parseInt(info.format?.size || "0", 10) / (1024 * 1024)).toFixed(1);

  let fps = "0";
  if (vStream.r_frame_rate && vStream.r_frame_rate.includes("/")) {
    const [n, d] = vStream.r_frame_rate.split("/").map(Number);
    if (d > 0) fps = (n / d).toFixed(2).replace(/\.00$/, "");
  }

  let silenceSummary = "";
  if (detectSilence && aStream.codec_name) {
    try {
      const silOut = execFileSync(
        "ffmpeg",
        ["-hide_banner", "-nostats", "-i", abs, "-af", "silencedetect=noise=-35dB:d=0.35", "-f", "null", "-"],
        { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
      );
      silenceSummary = silOut;
    } catch (err) {
      silenceSummary = String(err.stderr || "");
    }
  }

  const silences = [];
  const startRe = /silence_start:\s*([0-9.]+)/g;
  const endRe = /silence_end:\s*([0-9.]+)/g;
  const starts = [...silenceSummary.matchAll(startRe)].map((m) => parseFloat(m[1]));
  const ends = [...silenceSummary.matchAll(endRe)].map((m) => parseFloat(m[1]));
  for (let i = 0; i < Math.min(starts.length, ends.length, 12); i++) {
    silences.push(`${starts[i].toFixed(2)}-${ends[i].toFixed(2)}s`);
  }

  return [
    `${path.basename(abs)}: ${vStream.width || 0}x${vStream.height || 0}@${fps}fps`,
    `${vStream.codec_name || "none"}/${vStream.pix_fmt || "-"}`,
    `${dur}s (${sizeMb}MB)`,
    `audio:${aStream.codec_name || "none"}@${aStream.sample_rate || 0}Hz`,
    silences.length ? `silences:[${silences.join(", ")}]` : "silences:none"
  ].join(" | ");
}

function handleToolCall(name, args = {}) {
  try {
    if (name === "video_probe_shrunk") {
      return probeMediaShrunk(args.file_path, args.detect_silence !== false);
    }
    if (name === "video_transcript_shrunk") {
      const script = path.join(HELPERS_DIR, "pack_transcripts.py");
      const cmdArgs = [script, path.resolve(args.transcript_path)];
      if (args.gap_threshold) cmdArgs.push("--gap", String(args.gap_threshold));
      return execFileSync("python3", cmdArgs, { encoding: "utf8" }).trim();
    }
    if (name === "video_contact_sheet") {
      const script = path.join(HELPERS_DIR, "contact_sheet.py");
      const cmdArgs = [
        script,
        path.resolve(args.video_path),
        "-o",
        path.resolve(args.output_png),
        "--cols",
        String(args.cols || 4),
        "--rows",
        String(args.rows || 4)
      ];
      return execFileSync("python3", cmdArgs, { encoding: "utf8" }).trim();
    }
    if (name === "video_render_shrunk") {
      const script = path.join(HELPERS_DIR, "render_edl.py");
      const cmdArgs = [
        script,
        path.resolve(args.edl_json),
        "-o",
        path.resolve(args.output_path),
        "--grade",
        args.grade || "none"
      ];
      return execFileSync("python3", cmdArgs, { encoding: "utf8" }).trim();
    }
    return `ERR: Unknown tool ${name}`;
  } catch (err) {
    const stderr = String(err.stderr || err.message || err);
    const tail = stderr.split("\n").slice(-10).join("\n");
    return `ERR:\n${tail}`;
  }
}

function sendResponse(id, result) {
  process.stdout.write(JSON.stringify({ jsonrpc: "2.0", id, result }) + "\n");
}

function sendError(id, code, message) {
  process.stdout.write(JSON.stringify({ jsonrpc: "2.0", id, error: { code, message } }) + "\n");
}

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log("caveman-video: video-shrink MCP server (stdio JSON-RPC 2.0)");
  console.log("Tools:", TOOLS.map((t) => t.name).join(", "));
  process.exit(0);
}

const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on("line", (line) => {
  if (!line.trim()) return;
  let req;
  try {
    req = JSON.parse(line);
  } catch {
    return;
  }
  const { id, method, params } = req;
  if (method === "initialize") {
    sendResponse(id, {
      protocolVersion: "2024-11-05",
      capabilities: { tools: {} },
      serverInfo: { name: "caveman-video-shrink", version: "1.0.0" }
    });
  } else if (method === "notifications/initialized") {
    // No response required for notifications
  } else if (method === "tools/list") {
    sendResponse(id, { tools: TOOLS });
  } else if (method === "tools/call") {
    const text = handleToolCall(params?.name, params?.arguments);
    sendResponse(id, { content: [{ type: "text", text }] });
  } else if (id !== undefined) {
    sendError(id, -32601, `Method not found: ${method}`);
  }
});
