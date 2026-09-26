// caveman-video: helpers/templates/render_native_template.m
// Reusable macOS Native Objective-C / CoreGraphics / CoreText RGBA Pipe Compositor
// Derived from the Hey Siya production pipeline (render_siya.m).
//
// Compile:
//   clang -O3 -fobjc-arc -framework Cocoa -framework CoreGraphics -framework CoreText \
//     helpers/templates/render_native_template.m -o build/render_native
//
// Preview Mode (Mandatory Rule #9 - verify keyframes BEFORE full video encode):
//   ./build/render_native --preview
//
// Full Video Pipe Mode:
//   ffmpeg -i input.mp4 -f rawvideo -pix_fmt rgba - | ./build/render_native | \
//     ffmpeg -y -f rawvideo -pix_fmt rgba -s 1080x1920 -r 30 -i - -i input.mp4 \
//     -map 0:v -map 1:a -c:v libx264 -crf 18 -pix_fmt yuv420p \
//     -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
//     -af "loudnorm=I=-14:TP=-1.5:LRA=11" -movflags +faststart output_final.mp4

#import <Cocoa/Cocoa.h>
#import <CoreGraphics/CoreGraphics.h>
#import <CoreText/CoreText.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static const int W = 1080;
static const int H = 1920;
static const double FPS = 30.0;

// ============================================================================
// 1. Easing & Interpolation Helpers
// ============================================================================

static inline double clamp01(double v) {
    return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : v);
}

static inline double prog(double t, double t0, double t1) {
    if (t1 <= t0) return 1.0;
    return clamp01((t - t0) / (t1 - t0));
}

static double solve_cubic_bezier(double p1x, double p1y, double p2x, double p2y, double x) {
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

// Physical entrance curve: cubic-bezier(0.16, 1, 0.3, 1)
static inline double ease_out_expo(double t) {
    return solve_cubic_bezier(0.16, 1.0, 0.3, 1.0, t);
}

// Smooth exit curve: cubic-bezier(0.4, 0, 1, 1)
static inline double ease_in_quad(double t) {
    return solve_cubic_bezier(0.4, 0.0, 1.0, 1.0, t);
}

// Spring overshoot: cubic-bezier(0.34, 1.56, 0.64, 1)
static inline double ease_spring(double t) {
    return solve_cubic_bezier(0.34, 1.56, 0.64, 1.0, t);
}

// ============================================================================
// 2. Color & Vector Drawing Primitives
// ============================================================================

static inline void set_rgba(CGContextRef ctx, double r, double g, double b, double a) {
    CGContextSetRGBFillColor(ctx, r / 255.0, g / 255.0, b / 255.0, a);
    CGContextSetRGBStrokeColor(ctx, r / 255.0, g / 255.0, b / 255.0, a);
}

static void fill_round_rect(CGContextRef ctx, CGRect rect, double radius,
                            double r, double g, double b, double a) {
    CGContextSaveGState(ctx);
    set_rgba(ctx, r, g, b, a);
    CGPathRef path = CGPathCreateWithRoundedRect(rect, radius, radius, NULL);
    CGContextAddPath(ctx, path);
    CGContextFillPath(ctx);
    CGPathRelease(path);
    CGContextRestoreGState(ctx);
}

static void stroke_round_rect(CGContextRef ctx, CGRect rect, double radius, double lineW,
                              double r, double g, double b, double a) {
    CGContextSaveGState(ctx);
    set_rgba(ctx, r, g, b, a);
    CGContextSetLineWidth(ctx, lineW);
    CGPathRef path = CGPathCreateWithRoundedRect(rect, radius, radius, NULL);
    CGContextAddPath(ctx, path);
    CGContextStrokePath(ctx);
    CGPathRelease(path);
    CGContextRestoreGState(ctx);
}

static void draw_glass_card(CGContextRef ctx, CGRect rect, double radius, double alpha) {
    CGContextSaveGState(ctx);
    // Drop shadow
    CGSize offset = CGSizeMake(0, -14);
    CGColorRef shadowCol = CGColorCreateGenericRGB(0, 0, 0, 0.42 * alpha);
    CGContextSetShadowWithColor(ctx, offset, 32.0, shadowCol);
    fill_round_rect(ctx, rect, radius, 12, 18, 16, 0.90 * alpha);
    CGColorRelease(shadowCol);
    CGContextRestoreGState(ctx);

    // Subtle glass border
    stroke_round_rect(ctx, rect, radius, 2.0, 255, 255, 255, 0.16 * alpha);
}

static CGRect draw_text(CGContextRef ctx, NSString *str, NSString *fontName, double fontSize,
                        double x, double y, double r, double g, double b, double a,
                        int alignMode) {
    if (!str || str.length == 0 || a <= 0.001) return CGRectZero;
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

    double drawX = x;
    if (alignMode == 1) drawX = x - width * 0.5;      // Center
    else if (alignMode == 2) drawX = x - width;       // Right

    CGContextSaveGState(ctx);
    CGContextSetTextMatrix(ctx, CGAffineTransformIdentity);
    CGContextSetTextPosition(ctx, drawX, y);
    CTLineDraw(line, ctx);
    CGContextRestoreGState(ctx);

    CFRelease(line);
    CGColorRelease(color);
    CFRelease(font);
    return CGRectMake(drawX, y - descent, width, ascent + descent);
}

// ============================================================================
// 3. Caption TSV Loader (edit/captions.tsv -> start \t end \t text)
// ============================================================================

typedef struct {
    double start;
    double end;
    char text[128];
} CaptionChunk;

static CaptionChunk g_captions[2048];
static int g_caption_count = 0;

static void load_captions_tsv(const char *path) {
    FILE *fp = fopen(path, "r");
    if (!fp) return;
    char line[512];
    while (fgets(line, sizeof(line), fp) && g_caption_count < 2048) {
        if (line[0] == '#' || strlen(line) < 3) continue;
        double s = 0, e = 0;
        char txt[128] = {0};
        if (sscanf(line, "%lf\t%lf\t%127[^\r\n]", &s, &e, txt) == 3) {
            g_captions[g_caption_count].start = s;
            g_captions[g_caption_count].end = e;
            strncpy(g_captions[g_caption_count].text, txt, 127);
            g_caption_count++;
        }
    }
    fclose(fp);
}

// ============================================================================
// 4. Overlay & Scene Compositor
// ============================================================================

static void draw_persistent_brand_bug(CGContextRef ctx, double t) {
    double alpha = ease_out_expo(prog(t, 0.2, 0.8)) * 0.88;
    CGRect pill = CGRectMake(56, H - 154, 248, 56);
    fill_round_rect(ctx, pill, 28, 12, 18, 16, 0.76 * alpha);
    stroke_round_rect(ctx, pill, 28, 1.5, 255, 255, 255, 0.18 * alpha);

    // Pulsing emerald status dot
    double pulse = 0.65 + 0.35 * sin(t * 4.5);
    fill_round_rect(ctx, CGRectMake(78, H - 134, 16, 16), 8, 16, 185, 129, pulse * alpha);
    draw_text(ctx, @"CAVEMAN STUDIO", @"AvenirNext-Bold", 21, 108, H - 134, 245, 245, 240, alpha, 0);
}

static void draw_lower_third_callout(CGContextRef ctx, double t, double tStart, double tEnd,
                                     NSString *badge, NSString *headline, NSString *subline) {
    if (t < tStart || t > tEnd) return;
    double enter = ease_out_expo(prog(t, tStart, tStart + 0.45));
    double exit = 1.0 - ease_in_quad(prog(t, tEnd - 0.35, tEnd));
    double alpha = enter * exit;
    double ySlide = (1.0 - enter) * -48.0;

    CGRect card = CGRectMake(64, 420 + ySlide, W - 128, 190);
    draw_glass_card(ctx, card, 28, alpha);

    // Accent bar
    fill_round_rect(ctx, CGRectMake(88, 448 + ySlide, 8, 134), 4, 245, 158, 11, alpha);

    draw_text(ctx, badge, @"AvenirNext-Bold", 22, 118, 556 + ySlide, 245, 158, 11, alpha, 0);
    draw_text(ctx, headline, @"AvenirNext-Heavy", 42, 118, 502 + ySlide, 255, 255, 255, alpha, 0);
    draw_text(ctx, subline, @"AvenirNext-Medium", 28, 118, 456 + ySlide, 200, 210, 205, alpha, 0);
}

static void draw_caption_pill(CGContextRef ctx, double t) {
    for (int i = 0; i < g_caption_count; i++) {
        if (t >= g_captions[i].start && t <= g_captions[i].end) {
            double pop = ease_spring(prog(t, g_captions[i].start, g_captions[i].start + 0.14));
            NSString *txt = [NSString stringWithUTF8String:g_captions[i].text];
            CGRect pill = CGRectMake(140, 285, W - 280, 88);
            fill_round_rect(ctx, pill, 44, 10, 14, 12, 0.86);
            stroke_round_rect(ctx, pill, 44, 2.0, 245, 158, 11, 0.45);
            draw_text(ctx, txt, @"AvenirNext-Heavy", 38 * (0.92 + 0.08 * pop),
                      W * 0.5, 316, 255, 255, 255, 1.0, 1);
            break;
        }
    }
}

static void render_overlay_frame(CGContextRef ctx, double t, BOOL isPreviewBg) {
    if (isPreviewBg) {
        // Dark slate background for standalone keyframe PNG preview inspection
        fill_round_rect(ctx, CGRectMake(0, 0, W, H), 0, 22, 26, 29, 1.0);
    }
    draw_persistent_brand_bug(ctx, t);
    draw_lower_third_callout(ctx, t, 0.5, 4.5,
                             @"15 HARD RULES",
                             @"Zero Verbose Video Fluff",
                             @"60fps CoreGraphics + Surgical FFmpeg");
    draw_caption_pill(ctx, t);
}

// ============================================================================
// 5. Preview Mode & Raw RGBA Pipe Loop
// ============================================================================

static void save_preview_png(uint8_t *buf, CGContextRef ctx, double t, const char *outPath) {
    memset(buf, 0, (size_t)W * H * 4);
    CGContextSaveGState(ctx);
    render_overlay_frame(ctx, t, YES);
    CGContextRestoreGState(ctx);

    CGImageRef img = CGBitmapContextCreateImage(ctx);
    CFURLRef url = CFURLCreateFromFileSystemRepresentation(
        kCFAllocatorDefault, (const UInt8 *)outPath, strlen(outPath), false);
    CGImageDestinationRef dest = CGImageDestinationCreateWithURL(url, kUTTypePNG, 1, NULL);
    if (dest) {
        CGImageDestinationAddImage(dest, img, NULL);
        CGImageDestinationFinalize(dest);
        CFRelease(dest);
    }
    CFRelease(url);
    CGImageRelease(img);
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        load_captions_tsv("edit/captions.tsv");

        size_t frameBytes = (size_t)W * H * 4;
        uint8_t *buf = (uint8_t *)calloc(1, frameBytes);
        CGColorSpaceRef cs = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
        CGContextRef ctx = CGBitmapContextCreate(
            buf, W, H, 8, W * 4, cs,
            kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big);

        if (argc > 1 && strcmp(argv[1], "--preview") == 0) {
            mkdir("edit", 0755);
            mkdir("edit/preview_frames", 0755);
            double previewTimes[] = {1.0, 2.5, 5.0};
            for (int i = 0; i < 3; i++) {
                char path[256];
                snprintf(path, sizeof(path), "edit/preview_frames/preview_%02d_%.1fs.png", i + 1, previewTimes[i]);
                save_preview_png(buf, ctx, previewTimes[i], path);
                fprintf(stderr, "PREVIEW OK | %s\n", path);
            }
            CGContextRelease(ctx);
            CGColorSpaceRelease(cs);
            free(buf);
            return 0;
        }

        // Raw RGBA stdin -> stdout pipe loop
        int frameIdx = 0;
        while (fread(buf, 1, frameBytes, stdin) == frameBytes) {
            double t = (double)frameIdx / FPS;
            CGContextSaveGState(ctx);
            render_overlay_frame(ctx, t, NO);
            CGContextRestoreGState(ctx);
            fwrite(buf, 1, frameBytes, stdout);
            frameIdx++;
        }

        CGContextRelease(ctx);
        CGColorSpaceRelease(cs);
        free(buf);
    }
    return 0;
}
