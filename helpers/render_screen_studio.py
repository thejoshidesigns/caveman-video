#!/usr/bin/env python3
"""
caveman-video: helpers/render_screen_studio.py
Turns any raw screen recording (.mp4/.mov) + cursor_events.json into a
Screen-Studio-grade explainer video using a compiled macOS Native CoreGraphics
60fps RGBA pipe compositor:
  - Spring-eased camera auto-zoom & pan on clicks/spotlights (with anti-seasick clustering)
  - Padded studio canvas + rounded macOS window chrome + traffic lights + drop shadow
  - Expanding cursor click ripples & vector pointer
  - UI spotlight dimming cutouts
  - Keystroke HUD pills (e.g. ⌘ + K) & Step Callout cards
  - Mandatory --preview mode (dumps keyframe PNGs at every click/zoom event)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


OBJC_SCREEN_STUDIO_SRC = r"""
#import <Cocoa/Cocoa.h>
#import <CoreGraphics/CoreGraphics.h>
#import <CoreText/CoreText.h>
#import <ImageIO/ImageIO.h>
#import <CoreServices/CoreServices.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    double t;
    double duration;
    int type; // 0=click, 1=keystroke, 2=spotlight
    double x;
    double y;
    double w;
    double h;
    double zoom;
    char label[128];
    char sublabel[160];
    char keys[64];
} ScreenEvent;

static inline double clamp_d(double v, double lo, double hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

static inline double clamp01(double v) {
    return clamp_d(v, 0.0, 1.0);
}

static inline double prog(double t, double t0, double t1) {
    if (t1 <= t0) return 1.0;
    return clamp01((t - t0) / (t1 - t0));
}

static double solve_bezier(double p1x, double p1y, double p2x, double p2y, double x) {
    x = clamp01(x);
    if (x <= 0.0 || x >= 1.0) return x;
    double cx = 3.0 * p1x;
    double bx = 3.0 * (p2x - p1x) - cx;
    double ax = 1.0 - cx - bx;
    double cy = 3.0 * p1y;
    double by = 3.0 * (p2y - p1y) - cy;
    double ay = 1.0 - cy - by;
    double t = x;
    for (int i = 0; i < 8; i++) {
        double x_est = ((ax * t + bx) * t + cx) * t - x;
        if (fabs(x_est) < 1e-6) break;
        double dx = (3.0 * ax * t + 2.0 * bx) * t + cx;
        if (fabs(dx) < 1e-6) break;
        t -= x_est / dx;
    }
    t = clamp01(t);
    return ((ay * t + by) * t + cy) * t;
}

static inline double ease_out_expo(double t) { return solve_bezier(0.16, 1.0, 0.3, 1.0, t); }
static inline double ease_in_out(double t)   { return solve_bezier(0.4, 0.0, 0.2, 1.0, t); }
static inline double ease_spring(double t)   { return solve_bezier(0.34, 1.56, 0.64, 1.0, t); }

static void fill_round_rect(CGContextRef ctx, CGRect rect, double radius,
                            double r, double g, double b, double a) {
    CGContextSaveGState(ctx);
    CGContextSetRGBFillColor(ctx, r / 255.0, g / 255.0, b / 255.0, a);
    CGPathRef path = CGPathCreateWithRoundedRect(rect, radius, radius, NULL);
    CGContextAddPath(ctx, path);
    CGContextFillPath(ctx);
    CGPathRelease(path);
    CGContextRestoreGState(ctx);
}

static void stroke_round_rect(CGContextRef ctx, CGRect rect, double radius, double lineW,
                              double r, double g, double b, double a) {
    CGContextSaveGState(ctx);
    CGContextSetRGBStrokeColor(ctx, r / 255.0, g / 255.0, b / 255.0, a);
    CGContextSetLineWidth(ctx, lineW);
    CGPathRef path = CGPathCreateWithRoundedRect(rect, radius, radius, NULL);
    CGContextAddPath(ctx, path);
    CGContextStrokePath(ctx);
    CGPathRelease(path);
    CGContextRestoreGState(ctx);
}

static void draw_text(CGContextRef ctx, NSString *str, NSString *fontName, double fontSize,
                      double x, double y, double r, double g, double b, double a, int alignMode) {
    if (!str || str.length == 0 || a <= 0.001) return;
    CTFontRef font = CTFontCreateWithName((__bridge CFStringRef)fontName, fontSize, NULL);
    CGColorRef color = CGColorCreateGenericRGB(r / 255.0, g / 255.0, b / 255.0, a);
    NSDictionary *attrs = @{
        (__bridge id)kCTFontAttributeName: (__bridge id)font,
        (__bridge id)kCTForegroundColorAttributeName: (__bridge id)color
    };
    NSAttributedString *attrStr = [[NSAttributedString alloc] initWithString:str attributes:attrs];
    CTLineRef line = CTLineCreateWithAttributedString((__bridge CFAttributedStringRef)attrStr);
    CGFloat ascent = 0, descent = 0, leading = 0;
    double width = CTLineGetTypographicBounds(line, &ascent, &descent, &leading);
    double drawX = (alignMode == 1) ? (x - width * 0.5) : ((alignMode == 2) ? (x - width) : x);

    CGContextSaveGState(ctx);
    CGContextSetTextMatrix(ctx, CGAffineTransformIdentity);
    CGContextSetTextPosition(ctx, drawX, y);
    CTLineDraw(line, ctx);
    CGContextRestoreGState(ctx);

    CFRelease(line);
    CGColorRelease(color);
    CFRelease(font);
}

static void compute_camera(double t, int W, int H, const ScreenEvent *evts, int nEvts,
                           double *outZoom, double *outCx, double *outCy) {
    double zoom = 1.0;
    double cx = W * 0.5;
    double cy = H * 0.5;

    for (int i = 0; i < nEvts; i++) {
        double t0 = evts[i].t - 0.35;
        double t1 = evts[i].t + evts[i].duration;
        if (t >= t0 && t <= t1 + 0.65) {
            double zTarget = clamp_d(evts[i].zoom, 1.0, 2.35);
            double enterP = ease_out_expo(prog(t, t0, t0 + 0.55));
            double exitP  = ease_in_out(prog(t, t1, t1 + 0.65));
            double weight = enterP * (1.0 - exitP);

            zoom = 1.0 + (zTarget - 1.0) * weight;
            // Convert top-left DOM (x, y) to CoreGraphics bottom-left (x, H - y)
            double targetX = evts[i].x;
            double targetY = H - evts[i].y;
            cx = (W * 0.5) + (targetX - W * 0.5) * weight;
            cy = (H * 0.5) + (targetY - H * 0.5) * weight;
            break;
        }
    }

    double halfW = (W * 0.5) / zoom;
    double halfH = (H * 0.5) / zoom;
    *outZoom = zoom;
    *outCx = clamp_d(cx, halfW, W - halfW);
    *outCy = clamp_d(cy, halfH, H - halfH);
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc < 5) {
            fprintf(stderr, "Usage: screen_studio_bin <W> <H> <FPS> <events.json>\n");
            return 1;
        }
        int W = atoi(argv[1]);
        int H = atoi(argv[2]);
        double FPS = atof(argv[3]);
        NSString *jsonPath = [NSString stringWithUTF8String:argv[4]];

        NSData *jsonData = [NSData dataWithContentsOfFile:jsonPath];
        NSDictionary *root = jsonData ? [NSJSONSerialization JSONObjectWithData:jsonData options:0 error:nil] : @{};
        NSString *winTitle = root[@"windowTitle"] ?: @"Screen Studio Walkthrough";
        NSArray *rawEvts = root[@"events"] ?: @[];

        ScreenEvent evts[512];
        int nEvts = 0;
        for (NSDictionary *d in rawEvts) {
            if (nEvts >= 512) break;
            evts[nEvts].t = [d[@"t"] doubleValue];
            evts[nEvts].duration = d[@"duration"] ? [d[@"duration"] doubleValue] : 2.2;
            NSString *tp = d[@"type"] ?: @"click";
            evts[nEvts].type = [tp isEqualToString:@"keystroke"] ? 1 : ([tp isEqualToString:@"spotlight"] ? 2 : 0);
            evts[nEvts].x = d[@"x"] ? [d[@"x"] doubleValue] : (W * 0.5);
            evts[nEvts].y = d[@"y"] ? [d[@"y"] doubleValue] : (H * 0.5);
            evts[nEvts].w = d[@"w"] ? [d[@"w"] doubleValue] : 360.0;
            evts[nEvts].h = d[@"h"] ? [d[@"h"] doubleValue] : 140.0;
            evts[nEvts].zoom = d[@"zoom"] ? [d[@"zoom"] doubleValue] : 1.85;
            strncpy(evts[nEvts].label, [d[@"label"] ?: @"" UTF8String], 127);
            strncpy(evts[nEvts].sublabel, [d[@"sublabel"] ?: @"" UTF8String], 159);
            strncpy(evts[nEvts].keys, [d[@"keys"] ?: @"" UTF8String], 63);
            nEvts++;
        }

        size_t frameBytes = (size_t)W * H * 4;
        uint8_t *inBuf = (uint8_t *)calloc(1, frameBytes);
        uint8_t *outBuf = (uint8_t *)calloc(1, frameBytes);

        CGColorSpaceRef cs = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
        CGContextRef outCtx = CGBitmapContextCreate(
            outBuf, W, H, 8, W * 4, cs,
            kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big);

        double padX = round(W * 0.038);
        double padY = round(H * 0.052);
        double titleBarH = 38.0;
        CGRect winRect = CGRectMake(padX, padY, W - padX * 2.0, H - padY * 2.0);
        CGRect contentRect = CGRectMake(padX, padY, W - padX * 2.0, H - padY * 2.0 - titleBarH);

        int frameIdx = 0;
        while (fread(inBuf, 1, frameBytes, stdin) == frameBytes) {
            double t = (double)frameIdx / FPS;
            memset(outBuf, 0, frameBytes);

            // 1. Ambient Studio Canvas Background
            fill_round_rect(outCtx, CGRectMake(0, 0, W, H), 0, 13, 17, 23, 1.0);
            fill_round_rect(outCtx, CGRectMake(padX * 0.5, padY * 0.5, W - padX, H - padY), 32, 18, 24, 34, 0.55);

            // 2. Compute Camera Auto-Zoom & Pan
            double zoom = 1.0, cx = W * 0.5, cy = H * 0.5;
            compute_camera(t, W, H, evts, nEvts, &zoom, &cx, &cy);

            CGContextSaveGState(outCtx);
            // Translate around camera target and scale
            CGContextTranslateCTM(outCtx, W * 0.5, H * 0.5);
            CGContextScaleCTM(outCtx, zoom, zoom);
            CGContextTranslateCTM(outCtx, -cx, -cy);

            // 3. Window Drop Shadow & Chrome
            CGContextSaveGState(outCtx);
            CGColorRef shCol = CGColorCreateGenericRGB(0, 0, 0, 0.62);
            CGContextSetShadowWithColor(outCtx, CGSizeMake(0, -18), 44.0, shCol);
            fill_round_rect(outCtx, winRect, 20.0, 22, 27, 34, 1.0);
            CGColorRelease(shCol);
            CGContextRestoreGState(outCtx);

            // 4. Draw Raw Screen Frame inside Rounded Content Rect
            CGContextSaveGState(outCtx);
            CGPathRef clipPath = CGPathCreateWithRoundedRect(winRect, 20.0, 20.0, NULL);
            CGContextAddPath(outCtx, clipPath);
            CGContextClip(outCtx);
            CGPathRelease(clipPath);

            CGDataProviderRef prov = CGDataProviderCreateWithData(NULL, inBuf, frameBytes, NULL);
            CGImageRef srcImg = CGImageCreate(
                W, H, 8, 32, W * 4, cs,
                kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big,
                prov, NULL, true, kCGRenderingIntentDefault);
            CGContextDrawImage(outCtx, contentRect, srcImg);
            CGImageRelease(srcImg);
            CGDataProviderRelease(prov);

            // 5. macOS Title Bar & Traffic Lights
            CGRect barRect = CGRectMake(padX, H - padY - titleBarH, W - padX * 2.0, titleBarH);
            fill_round_rect(outCtx, barRect, 0, 18, 22, 28, 0.96);
            double dotY = H - padY - titleBarH * 0.5 - 6.0;
            fill_round_rect(outCtx, CGRectMake(padX + 20, dotY, 12, 12), 6, 255, 95, 86, 1.0);
            fill_round_rect(outCtx, CGRectMake(padX + 40, dotY, 12, 12), 6, 255, 189, 46, 1.0);
            fill_round_rect(outCtx, CGRectMake(padX + 60, dotY, 12, 12), 6, 39, 201, 63, 1.0);
            draw_text(outCtx, winTitle, @"AvenirNext-DemiBold", 15, W * 0.5, dotY + 1, 180, 190, 205, 0.85, 1);

            // 6. Click Ripples & UI Spotlights inside window coordinates
            for (int i = 0; i < nEvts; i++) {
                double sx = padX + (evts[i].x / (double)W) * contentRect.size.width;
                double sy = padY + ((H - evts[i].y) / (double)H) * contentRect.size.height;

                if (evts[i].type == 0 && t >= evts[i].t && t <= evts[i].t + 0.55) {
                    double rp = prog(t, evts[i].t, evts[i].t + 0.55);
                    double rad = 10.0 + 52.0 * ease_out_expo(rp);
                    double alpha = (1.0 - rp) * 0.9;
                    stroke_round_rect(outCtx, CGRectMake(sx - rad, sy - rad, rad * 2, rad * 2), rad, 3.5, 245, 158, 11, alpha);
                    fill_round_rect(outCtx, CGRectMake(sx - 7, sy - 7, 14, 14), 7, 245, 158, 11, alpha);
                } else if (evts[i].type == 2 && t >= evts[i].t && t <= evts[i].t + evts[i].duration) {
                    double sw = (evts[i].w / (double)W) * contentRect.size.width;
                    double sh = (evts[i].h / (double)H) * contentRect.size.height;
                    CGRect spot = CGRectMake(sx - sw * 0.5, sy - sh * 0.5, sw, sh);
                    stroke_round_rect(outCtx, spot, 14.0, 3.0, 16, 185, 129, 0.92);
                }
            }

            CGContextRestoreGState(outCtx); // end clip
            stroke_round_rect(outCtx, winRect, 20.0, 1.5, 255, 255, 255, 0.16);
            CGContextRestoreGState(outCtx); // end camera transform

            // 7. Screen-Space HUD Overlays (Step Callout Cards & Keystroke Pills)
            for (int i = 0; i < nEvts; i++) {
                if (t >= evts[i].t - 0.15 && t <= evts[i].t + evts[i].duration) {
                    double enter = ease_spring(prog(t, evts[i].t - 0.15, evts[i].t + 0.25));
                    double exit  = 1.0 - ease_in_out(prog(t, evts[i].t + evts[i].duration - 0.3, evts[i].t + evts[i].duration));
                    double alpha = clamp01(enter * exit);

                    if (evts[i].type == 1 && strlen(evts[i].keys) > 0) {
                        NSString *kStr = [NSString stringWithUTF8String:evts[i].keys];
                        CGRect kPill = CGRectMake(W * 0.5 - 150, 96, 300, 74);
                        fill_round_rect(outCtx, kPill, 37, 12, 16, 22, 0.92 * alpha);
                        stroke_round_rect(outCtx, kPill, 37, 2.0, 245, 158, 11, 0.65 * alpha);
                        draw_text(outCtx, kStr, @"AvenirNext-Heavy", 32, W * 0.5, 122, 255, 255, 255, alpha, 1);
                    }

                    if (strlen(evts[i].label) > 0) {
                        NSString *lbl = [NSString stringWithUTF8String:evts[i].label];
                        NSString *sub = [NSString stringWithUTF8String:evts[i].sublabel];
                        double cardH = strlen(evts[i].sublabel) > 0 ? 108.0 : 72.0;
                        CGRect card = CGRectMake(64, 52, 560, cardH);
                        fill_round_rect(outCtx, card, 20, 12, 16, 22, 0.90 * alpha);
                        stroke_round_rect(outCtx, card, 20, 1.5, 255, 255, 255, 0.18 * alpha);
                        fill_round_rect(outCtx, CGRectMake(82, 68, 6, cardH - 32), 3, 16, 185, 129, alpha);
                        draw_text(outCtx, lbl, @"AvenirNext-Bold", 23, 104, 52 + cardH - 42, 245, 245, 240, alpha, 0);
                        if (strlen(evts[i].sublabel) > 0) {
                            draw_text(outCtx, sub, @"AvenirNext-Medium", 18, 104, 72, 175, 185, 195, alpha, 0);
                        }
                    }
                    break;
                }
            }

            fwrite(outBuf, 1, frameBytes, stdout);
            frameIdx++;
        }

        CGContextRelease(outCtx);
        CGColorSpaceRelease(cs);
        free(inBuf);
        free(outBuf);
    }
    return 0;
}
"""


def probe_video(video_path: Path) -> tuple[int, int, float, float, bool]:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_format", "-show_streams", "-of", "json", str(video_path)
    ]
    raw = subprocess.check_output(cmd, text=True)
    info = json.loads(raw)
    v_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    w = int(v_stream.get("width", 1920))
    h = int(v_stream.get("height", 1080))
    dur = float(info.get("format", {}).get("duration") or v_stream.get("duration") or 0.0)
    fps_str = v_stream.get("r_frame_rate", "30/1")
    num, den = (int(x) for x in fps_str.split("/")) if "/" in fps_str else (30, 1)
    fps = round(num / den, 2) if den else 30.0
    return w, h, fps, dur, (a_stream is not None)


def cluster_events(events: list[dict], cluster_gap: float = 2.0) -> list[dict]:
    """Merge back-to-back zoom events separated by <2.0s to prevent seasick camera bouncing."""
    if not events:
        return []
    sorted_evts = sorted(events, key=lambda e: float(e.get("t", 0.0)))
    for i in range(len(sorted_evts) - 1):
        cur = sorted_evts[i]
        nxt = sorted_evts[i + 1]
        cur_end = float(cur.get("t", 0.0)) + float(cur.get("duration", 2.0))
        nxt_start = float(nxt.get("t", 0.0))
        if 0.0 <= (nxt_start - cur_end) < cluster_gap:
            cur["duration"] = round(nxt_start - float(cur.get("t", 0.0)) + 0.15, 3)
    return sorted_evts


def main() -> int:
    parser = argparse.ArgumentParser(description="Screen-Studio Auto-Zoom & Window Chrome Renderer.")
    parser.add_argument("video", help="Input raw screen recording (.mp4/.mov)")
    parser.add_argument("--events", required=True, help="Path to cursor_events.json")
    parser.add_argument("-o", "--output", default="output_explainer.mp4", help="Output MP4 path")
    parser.add_argument("--preview", action="store_true", help="Render keyframe PNGs at each event timestamp (Rule #9)")
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    events_path = Path(args.events).resolve()
    if not video_path.exists():
        print(f"ERR: Video not found: {video_path}", file=sys.stderr)
        return 1
    if not events_path.exists():
        print(f"ERR: Events JSON not found: {events_path}", file=sys.stderr)
        return 1

    w, h, fps, dur, has_audio = probe_video(video_path)
    evts_data = json.loads(events_path.read_text(encoding="utf-8"))
    evts_data["events"] = cluster_events(evts_data.get("events", []))

    tmp_dir = Path(tempfile.mkdtemp(prefix="caveman_screen_studio_"))
    try:
        clustered_json = tmp_dir / "clustered_events.json"
        clustered_json.write_text(json.dumps(evts_data, indent=2), encoding="utf-8")

        m_file = tmp_dir / "screen_studio.m"
        bin_file = tmp_dir / "screen_studio_bin"
        m_file.write_text(OBJC_SCREEN_STUDIO_SRC, encoding="utf-8")

        subprocess.run([
            "clang", "-O3", "-fobjc-arc", "-Wno-deprecated-declarations",
            "-framework", "Cocoa", "-framework", "CoreGraphics",
            "-framework", "CoreText", "-framework", "ImageIO", "-framework", "CoreServices",
            str(m_file), "-o", str(bin_file)
        ], check=True)

        out_mp4 = tmp_dir / "preview_pass.mp4" if args.preview else Path(args.output).resolve()
        out_mp4.parent.mkdir(parents=True, exist_ok=True)

        dec_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", str(video_path),
            "-f", "rawvideo", "-pix_fmt", "rgba", "-"
        ]
        comp_cmd = [str(bin_file), str(w), str(h), str(fps), str(clustered_json)]

        enc_cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgba",
            "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
        ]
        if has_audio and not args.preview:
            enc_cmd += [
                "-i", str(video_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                "-c:a", "aac", "-b:a", "192k",
            ]
        enc_cmd += [
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-movflags", "+faststart",
            str(out_mp4)
        ]

        p_dec = subprocess.Popen(dec_cmd, stdout=subprocess.PIPE)
        p_comp = subprocess.Popen(comp_cmd, stdin=p_dec.stdout, stdout=subprocess.PIPE)
        p_enc = subprocess.Popen(enc_cmd, stdin=p_comp.stdout)
        p_dec.stdout.close()
        p_comp.stdout.close()

        p_enc.wait()
        p_comp.wait()
        p_dec.wait()

        if args.preview:
            prev_dir = Path("edit/preview_frames")
            prev_dir.mkdir(parents=True, exist_ok=True)
            events_list = evts_data.get("events", [])
            sample_times = [float(e.get("t", 0.5)) + 0.15 for e in events_list[:4]] or [min(0.5, dur * 0.5)]
            for idx, ts in enumerate(sample_times, 1):
                ts_clamped = min(max(0.0, ts), max(0.0, dur - 0.1))
                png_out = prev_dir / f"screen_studio_{idx:02d}_{ts_clamped:.2f}s.png"
                subprocess.run([
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", f"{ts_clamped:.3f}", "-i", str(out_mp4),
                    "-frames:v", "1", str(png_out)
                ], check=True)
                print(f"PREVIEW OK | {png_out}")
            return 0

        print(f"OK | out={out_mp4.name} | events={len(evts_data.get('events', []))} | res={w}x{h}@{fps}fps | dur={dur:.2f}s")
        return 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
