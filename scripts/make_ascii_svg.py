"""
Convert source-prepped.png into a monochrome ASCII portrait SVG that
"types" itself in row by row (SMIL clip wipes + a riding block cursor),
then freezes. No looping.

Usage: python scripts/make_ascii_svg.py     -> ascii-portrait.svg
       STATIC=1 python scripts/make_ascii_svg.py   (frozen frame, no animation)
"""
import os
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source-prepped.png"
OUT = ROOT / "ascii-portrait.svg"

RAMP = " .`:-=+*cs#%@"      # bright (sparse) -> dark (dense)
COLS = 100                  # character columns
MAX_ROWS = 56
WHITE_CUTOFF = 235          # anything brighter than this becomes a space
# INVERT=1: bright skin -> dense glyphs. Reads like a real photo on a dark
# terminal. INVERT=0 is the blog's original look (dark hair/beard -> dense).
INVERT = os.environ.get("INVERT", "1") == "1"

FONT_SIZE = 10
CHAR_W = FONT_SIZE * 0.6    # monospace advance
LINE_H = FONT_SIZE * 1.12
PAD = 18
FG = "#c9d1d9"
BG = "#0d1117"

ROW_START = 0.3             # seconds before the first row starts
ROW_STAGGER = 0.055         # delay between rows
ROW_DUR = 0.32              # how long each row's wipe takes

STATIC = os.environ.get("STATIC") == "1"


def to_ascii(img: Image.Image) -> list[str]:
    w, h = img.size
    rows = min(MAX_ROWS, max(10, round(COLS * (h / w) * (CHAR_W / LINE_H))))
    has_alpha = img.mode == "LA"
    gray = img.getchannel(0) if has_alpha else img
    small = gray.resize((COLS, rows), Image.LANCZOS)
    px = np.asarray(small, dtype=np.float32)
    if has_alpha:
        a = np.asarray(img.getchannel(1).resize((COLS, rows), Image.LANCZOS), dtype=np.float32)
        subject = a > 110
        # stretch contrast using subject pixels only
        lo, hi = np.percentile(px[subject], [2, 98]) if subject.any() else (0, 255)
        px = ((px - lo) / max(hi - lo, 1) * 255).clip(0, 255)
    else:
        px = np.asarray(ImageOps.autocontrast(small, cutoff=1), dtype=np.float32)
        subject = px < WHITE_CUTOFF

    n = len(RAMP) - 1          # usable glyphs (index 1..n)
    lines = []
    for r in range(rows):
        chars = []
        for c, v in enumerate(px[r]):
            if not subject[r, c]:
                chars.append(" ")
                continue
            t = v / 255.0 if INVERT else 1.0 - v / 255.0   # 0 -> sparse, 1 -> dense
            idx = 1 + int(t * (n - 1) + 0.5)
            chars.append(RAMP[min(idx, n)])
        lines.append("".join(chars).rstrip())

    # drop fully-blank rows at top and bottom
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def build_svg(lines: list[str]) -> str:
    width = PAD * 2 + COLS * CHAR_W
    height = PAD * 2 + len(lines) * LINE_H
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" aria-label="ASCII portrait">',
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>',
        "<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"
        "'Liberation Mono',monospace;font-size:%dpx;fill:%s;white-space:pre}</style>"
        % (FONT_SIZE, FG),
    ]

    if not STATIC:
        out.append("<defs>")
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            y = PAD + i * LINE_H
            w = len(line) * CHAR_W
            b = ROW_START + i * ROW_STAGGER
            out.append(
                f'<clipPath id="r{i}"><rect x="{PAD}" y="{y:.2f}" width="0" height="{LINE_H + 1:.2f}">'
                f'<animate attributeName="width" from="0" to="{w:.2f}" begin="{b:.3f}s" '
                f'dur="{ROW_DUR}s" fill="freeze"/></rect></clipPath>'
            )
        out.append("</defs>")

    for i, line in enumerate(lines):
        if not line.strip():
            continue
        y = PAD + i * LINE_H
        baseline = y + FONT_SIZE * 0.85
        w = len(line) * CHAR_W
        clip = "" if STATIC else f' clip-path="url(#r{i})"'
        out.append(
            f'<text x="{PAD}" y="{baseline:.2f}" textLength="{w:.2f}" '
            f'lengthAdjust="spacing" xml:space="preserve"{clip}>{escape(line)}</text>'
        )
        if not STATIC:
            b = ROW_START + i * ROW_STAGGER
            out.append(
                f'<rect x="{PAD}" y="{y + 1:.2f}" width="{CHAR_W:.2f}" height="{LINE_H - 1:.2f}" '
                f'fill="{FG}" opacity="0">'
                f'<set attributeName="opacity" to="0.85" begin="{b:.3f}s"/>'
                f'<animate attributeName="x" from="{PAD}" to="{PAD + w:.2f}" '
                f'begin="{b:.3f}s" dur="{ROW_DUR}s" fill="freeze"/>'
                f'<set attributeName="opacity" to="0" begin="{b + ROW_DUR:.3f}s"/>'
                f"</rect>"
            )

    out.append("</svg>")
    return "\n".join(out)


def main():
    if not SRC.exists():
        raise SystemExit(f"{SRC.name} not found - run prep_photo.py first")
    im = Image.open(SRC)
    lines = to_ascii(im.convert("LA") if "A" in im.getbands() else im.convert("L"))
    OUT.write_text(build_svg(lines), encoding="utf-8")
    print(f"✓ wrote {OUT.name} ({len(lines)} rows × {COLS} cols)")


if __name__ == "__main__":
    main()
