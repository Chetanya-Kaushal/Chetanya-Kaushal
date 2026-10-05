"""
Hand-author a neofetch-style info card SVG from scripts/config.py.
Each line fades + slides in on a short stagger, then stays put.

Usage: python scripts/make_info_card.py           -> info-card.svg
       STATIC=1 python scripts/make_info_card.py  (frozen frame)
"""
import os
from pathlib import Path
from xml.sax.saxutils import escape

import config

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "info-card.svg"
STATIC = os.environ.get("STATIC") == "1"

W = 490
PAD = 22
TITLE_H = 34
FONT = 13
CHAR_W = FONT * 0.6
LINE_H = 22

BG = "#0d1117"
BAR = "#161b22"
BORDER = "#30363d"
FG = "#c9d1d9"
MUTED = "#8b949e"
KEY = "#39d353"
ACCENT = "#58a6ff"
BLOCKS = ["#161b22", "#f85149", "#39d353", "#d29922",
          "#58a6ff", "#bc8cff", "#39c5cf", "#c9d1d9"]

START = 0.4
STAGGER = 0.12


def fit(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def main():
    key_w = max(len(k) for k, _ in config.INFO_ROWS) + 2
    max_val = int((W - 2 * PAD) / CHAR_W) - key_w

    # each entry: list of (text, color) spans, or "blocks"
    lines = []
    lines.append([(config.HANDLE, ACCENT)])
    lines.append([("─" * len(config.HANDLE), MUTED)])
    for k, v in config.INFO_ROWS:
        label = (k + ":").ljust(key_w) if k else " " * key_w
        lines.append([(label, KEY), (fit(v, max_val), FG)])
    if config.LINKS:
        lines.append([("", FG)])
        for k, v in config.LINKS:
            lines.append([((k + ":").ljust(key_w), ACCENT), (fit(v, max_val), FG)])
    lines.append([("", FG)])
    lines.append("blocks")

    body_top = TITLE_H + PAD
    H = body_top + len(lines) * LINE_H + PAD - 4

    css = [
        "text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"
        f"'Liberation Mono',monospace;font-size:{FONT}px;white-space:pre}}",
        ".t{font-size:12px;fill:%s}" % MUTED,
    ]
    if not STATIC:
        css.append("@keyframes in{from{opacity:0;transform:translateX(-8px)}"
                   "to{opacity:1;transform:none}}")
        css.append(".l{opacity:0;animation:in .45s ease-out forwards}")

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
        f'height="{H}" role="img" aria-label="{escape(config.HANDLE)} info">',
        f"<style>{''.join(css)}</style>",
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<path d="M.5 {TITLE_H}V10.5a10 10 0 0 1 10-10h{W - 21}a10 10 0 0 1 10 10V{TITLE_H}z" fill="{BAR}"/>',
        f'<line x1="0" y1="{TITLE_H}" x2="{W}" y2="{TITLE_H}" stroke="{BORDER}"/>',
    ]
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        out.append(f'<circle cx="{18 + i * 18}" cy="{TITLE_H / 2}" r="5.5" fill="{c}"/>')
    out.append(f'<text class="t" x="{W / 2}" y="{TITLE_H / 2 + 4}" text-anchor="middle">'
               f'{escape(config.HANDLE)} — neofetch</text>')

    for i, line in enumerate(lines):
        y = body_top + i * LINE_H
        delay = f' style="animation-delay:{START + i * STAGGER:.2f}s"' if not STATIC else ""
        cls = ' class="l"' if not STATIC else ""
        if line == "blocks":
            out.append(f"<g{cls}{delay}>")
            for j, c in enumerate(BLOCKS):
                out.append(f'<rect x="{PAD + j * 26}" y="{y - 12}" width="22" height="14" rx="2" fill="{c}"/>')
            out.append("</g>")
            continue
        spans = "".join(f'<tspan fill="{c}">{escape(t)}</tspan>' for t, c in line if t)
        if spans:
            out.append(f'<text x="{PAD}" y="{y}" xml:space="preserve"{cls}{delay}>{spans}</text>')

    out.append("</svg>")
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"✓ wrote {OUT.name}")


if __name__ == "__main__":
    main()
