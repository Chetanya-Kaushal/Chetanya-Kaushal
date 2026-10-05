"""
Prep a photo for ASCII conversion.
  1. Remove the background (rembg, if installed)
  2. Boost local contrast with CLAHE
  3. Composite onto pure white -> grayscale source-prepped.png

Usage: python scripts/prep_photo.py source-photo.jpg
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "source-prepped.png"


def grabcut(img: Image.Image) -> Image.Image:
    """No-download fallback: OpenCV GrabCut seeded with a head-and-shoulders shape."""
    print("· rembg not installed - isolating subject with GrabCut")
    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    cv2.ellipse(mask, (w // 2, int(h * .48)), (int(w * .31), int(h * .45)), 0, 0, 360, cv2.GC_PR_FGD, -1)
    mask[int(h * .72):, int(w * .1):int(w * .9)] = cv2.GC_PR_FGD
    cv2.ellipse(mask, (w // 2, int(h * .58)), (int(w * .19), int(h * .26)), 0, 0, 360, cv2.GC_FGD, -1)
    b = max(4, w // 35)
    mask[:, :b] = mask[:, -b:] = cv2.GC_BGD
    mask[:b // 2, :] = cv2.GC_BGD
    cv2.grabCut(bgr, mask, None, np.zeros((1, 65)), np.zeros((1, 65)), 8, cv2.GC_INIT_WITH_MASK)
    m = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        m = np.where(lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]), 255, 0).astype(np.uint8)
    m = cv2.GaussianBlur(m, (7, 7), 0)
    rgba = img.convert("RGBA"); rgba.putalpha(Image.fromarray(m))
    return rgba


def remove_background(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA" and np.array(img.split()[-1]).min() < 250:
        print("· photo already has a transparent background - using it")
        return img
    try:
        from rembg import remove
    except ImportError:
        return grabcut(img.convert("RGB"))
    print("· removing background with rembg…")
    return remove(img.convert("RGB")).convert("RGBA")


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/prep_photo.py <photo>")
    src = Image.open(sys.argv[1])
    src = src.convert("RGBA" if "A" in src.getbands() else "RGB")

    # keep it a sensible size
    src.thumbnail((1200, 1200))
    rgba = remove_background(src)

    # grayscale + CLAHE on the subject
    rgb = np.array(rgba.convert("RGB"))
    alpha = np.array(rgba.split()[-1]).astype(np.float32) / 255.0
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray = clahe.apply(gray).astype(np.float32)

    # composite onto white so the background maps to spaces
    out = gray * alpha + 255.0 * (1 - alpha)
    keep_alpha = alpha * 255.0

    # crop to the subject's bounding box (with a little padding)
    ys, xs = np.where(alpha > 0.1)
    if len(xs) and len(ys) and alpha.mean() < 0.98:
        pad = 20
        y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, out.shape[0])
        x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, out.shape[1])
        out = out[y0:y1, x0:x1]
        keep_alpha = keep_alpha[y0:y1, x0:x1]

    g = Image.fromarray(out.clip(0, 255).astype(np.uint8), "L")
    g.putalpha(Image.fromarray(keep_alpha.clip(0, 255).astype(np.uint8)))
    g.save(OUT)  # grayscale + alpha
    print(f"✓ wrote {OUT.name}")


if __name__ == "__main__":
    main()
