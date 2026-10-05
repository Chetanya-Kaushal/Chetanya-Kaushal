"""
Render data/contributions.json as an animated 53x7 contribution heatmap.
Boxes slide in on a diagonal once, then freeze. No looping glow.

Usage: python scripts/render_heatmap_svg.py           -> contrib-heatmap.svg
       STATIC=1 python scripts/render_heatmap_svg.py  (frozen frame)
"""
import json
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"
STATIC = os.environ.get("STATIC") == "1"

PALETTE = ["#161b22", "#0e4429", "#006d32",
           "#26a641", "#39d353", "#69f0a0"]
#          none -> brightest (level 5 is a neon top end)

W = 860
PAD = 20
LEFT = 30            # room for Mon/Wed/Fri labels
TOP = 46             # header line + month labels
WEEKS = 53
STEP = (W - PAD * 2 - LEFT) / WEEKS
CELL = STEP - 3
FG = "#c9d1d9"
MUTED = "#8b949e"
BG = "#0d1117"
BORDER = "#30363d"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


def with_neon(days: list[dict]) -> None:
    """Promote the top ~5% of active days to level 5."""
    active = sorted(d["count"] for d in days if d["count"] > 0)
    if len(active) < 10:
        return
    cutoff = active[int(len(active) * 0.95)]
    for d in days:
        if d["count"] >= cutoff and d["level"] >= 4:
            d["level"] = 5


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    days = data["days"][-WEEKS * 7:]
    s = data["stats"]
    with_neon(days)

    first = date.fromisoformat(days[0]["date"])
    offset = (first.weekday() + 1) % 7  # GitHub weeks start on Sunday
    n_weeks = (len(days) + offset + 6) // 7
    grid_w = n_weeks * STEP
    H = TOP + 7 * STEP + 44

    css = [f"text{{font-family:{FONT};fill:{MUTED};font-size:11px}}",
           f".h{{fill:{FG};font-size:13px}}", f".b{{fill:{FG}}}"]
    if not STATIC:
        css.append("@keyframes d{from{opacity:0;transform:translateY(-7px)}"
                   "to{opacity:1;transform:none}}")
        css.append(".c{opacity:0;animation:d .35s ease-out forwards}")
        css.append("@keyframes f{to{opacity:1}}.fd{opacity:0;animation:f .6s ease-out forwards}")

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="{W}" '
        f'height="{H:.0f}" role="img" aria-label="{s["total"]} contributions in the last year">',
        f"<style>{''.join(css)}</style>",
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1:.0f}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<text class="h" x="{PAD}" y="24"><tspan class="b">{s["total"]:,}</tspan> contributions '
        f'in the last year</text>',
        f'<text x="{W - PAD}" y="24" text-anchor="end">updated {data.get("fetched", "")}</text>',
    ]

    x0, y0 = PAD + LEFT, TOP

    # month labels
    last_month, last_col = None, -9
    for col in range(n_weeks):
        i = max(col * 7 - offset, 0)          # first day shown in this week column
        if i >= len(days):
            break
        m = days[i]["date"][5:7]
        if m != last_month:
            if col - last_col >= 3 and col < n_weeks - 1:   # avoid overlapping labels
                label = date.fromisoformat(days[i]["date"]).strftime("%b")
                out.append(f'<text x="{x0 + col * STEP:.1f}" y="{y0 - 8}">{label}</text>')
                last_col = col
            last_month = m

    for r, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="{PAD}" y="{y0 + r * STEP + CELL - 2:.1f}">{label}</text>')

    # cells
    for i, d in enumerate(days):
        col, row = divmod(i + offset, 7)
        x, y = x0 + col * STEP, y0 + row * STEP
        anim = ""
        if not STATIC:
            anim = f' class="c" style="animation-delay:{(col + row) * 0.02 + 0.2:.2f}s"'
        plural = "" if d["count"] == 1 else "s"
        out.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL:.1f}" height="{CELL:.1f}" rx="2.5" '
            f'fill="{PALETTE[d["level"]]}"{anim}><title>{d["count"]} contribution{plural} '
            f'on {d["date"]}</title></rect>'
        )

    # footer: stats + legend
    fy = y0 + 7 * STEP + 26
    fd = ' class="fd" style="animation-delay:1.4s"' if not STATIC else ""
    best = s["best_day"]
    out.append(
        f'<text x="{x0}" y="{fy:.1f}"{fd}>current streak <tspan class="b">{s["current_streak"]}d</tspan>'
        f'   ·   longest <tspan class="b">{s["longest_streak"]}d</tspan>'
        f'   ·   best day <tspan class="b">{best["count"]}</tspan> ({best["date"]})</text>'
    )
    lx = x0 + grid_w - 6 * 14 - 34
    out.append(f'<g{fd}><text x="{lx - 6}" y="{fy:.1f}" text-anchor="end">Less</text>')
    for j, c in enumerate(PALETTE):
        out.append(f'<rect x="{lx + j * 14}" y="{fy - 10:.1f}" width="11" height="11" rx="2" fill="{c}"/>')
    out.append(f'<text x="{lx + 6 * 14 + 4}" y="{fy:.1f}">More</text></g>')

    out.append("</svg>")
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"✓ wrote {OUT.name} ({len(days)} days, {s['total']} contributions)")


if __name__ == "__main__":
    main()
