#!/usr/bin/env python3
"""Generate Control Center brand assets from raw OEM artwork.

Takes a wide logo lockup and a square mark, and emits everything the UI needs:
tightly cropped, correctly sized, plus the reversed white variants the dark
screens require.

Usage:
    python tools/make_brand_assets.py --wide LOGO.png --mark MARK.png --prefix addiwise

Then register the outputs in ui/resources/resource.qrc, recompile with
    pyrcc5 resource.qrc -o resource_rc.py
and point octoprint_ControlCenter/branding.py at the new paths.

Why the white variants exist
----------------------------
The splash and home screens sit on rgb(40,40,40). Saturated brand colours die
there -- the Addiwise purple #503890 manages only 1.62:1 contrast, which is
illegible. Every original Fracktal splash asset was therefore white knockout
ink (#f0f0f0, 14.7:1), and this script reproduces that treatment automatically.

Requires Pillow:  pip install Pillow
"""
import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")

# Matches the existing assets: slightly off-white so the mark doesn't glare
# against the dark chrome.
KNOCKOUT = (240, 240, 240)

# Default output directory, relative to the repo root.
DEFAULT_OUT = os.path.join(
    "octoprint_ControlCenter", "ui", "resources", "img", "Logos"
)

# Render targets. The splash QLabel draws the lockup at 400px wide, so 800px
# keeps it crisp on 2x panels; 210px matches the print-preview placeholder it
# replaces.
LOGO_WIDTH = 800
MARK_BOX = 256
THUMB_BOX = 210
THUMB_INSET = 20


def crop_to_ink(im, pad_frac=0.02):
    """Trim transparent padding, then re-add a small even margin.

    Raw artwork usually ships with generous whitespace. Left in place it eats
    the fixed-size QLabel, so the mark renders far smaller than intended.
    """
    bbox = im.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("image is fully transparent -- is the alpha channel right?")
    im = im.crop(bbox)
    pad = int(round(max(im.size) * pad_frac))
    if pad:
        canvas = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        canvas.paste(im, (pad, pad))
        im = canvas
    return im


def fit_width(im, width):
    """Scale to an exact width, preserving aspect ratio."""
    height = max(1, round(im.height * width / im.width))
    return im.resize((width, height), Image.LANCZOS)


def fit_box(im, size):
    """Scale to fit inside a square box, preserving aspect ratio."""
    scale = size / max(im.size)
    return im.resize(
        (max(1, round(im.width * scale)), max(1, round(im.height * scale))),
        Image.LANCZOS,
    )


def knockout(im):
    """Recolour visible pixels to the knockout tone, preserving antialiasing.

    Only RGB is replaced; alpha is carried over untouched, so soft edges and
    interior cut-outs (the spokes of a gear, say) survive intact.
    """
    solid = Image.new("RGBA", im.size, KNOCKOUT + (255,))
    solid.putalpha(im.getchannel("A"))
    return solid


def contrast_ratio(fg, bg):
    """WCAG contrast ratio, used to warn when brand colour won't work on dark."""
    def lum(c):
        def channel(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * channel(c[0]) + 0.7152 * channel(c[1]) + 0.0722 * channel(c[2])
    hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def dominant_ink(im):
    """Most common opaque colour -- the brand colour, in practice."""
    import collections
    # Read raw RGBA bytes rather than getdata(), which is deprecated in
    # Pillow 11+, or get_flattened_data(), which older Pillow lacks.
    raw = im.tobytes()
    px = [raw[i:i + 4] for i in range(0, len(raw), 4)]
    px = [p for p in px if p[3] > 200]
    if not px:
        return None
    (r, g, b), _ = collections.Counter(
        (r // 8 * 8, g // 8 * 8, b // 8 * 8) for r, g, b, _ in px
    ).most_common(1)[0]
    return (r, g, b)


def load(path):
    im = Image.open(path).convert("RGBA")
    if im.getchannel("A").getextrema() == (255, 255):
        print(f"  ! {os.path.basename(path)} has no transparency -- the opaque "
              f"background will show as a block on the dark UI.")
    return crop_to_ink(im)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wide", required=True, help="wide logo lockup (logo + wordmark)")
    ap.add_argument("--mark", required=True, help="square icon / symbol only")
    ap.add_argument("--prefix", required=True, help="output filename prefix, e.g. 'addiwise'")
    ap.add_argument("--out", default=DEFAULT_OUT, help=f"output dir (default: {DEFAULT_OUT})")
    args = ap.parse_args()

    if not os.path.isdir(args.out):
        sys.exit(f"output directory does not exist: {args.out}")

    print("reading artwork:")
    wide = load(args.wide)
    mark = load(args.mark)
    print(f"  wide lockup cropped to {wide.size}  aspect {wide.width / wide.height:.2f}:1")
    print(f"  square mark cropped to {mark.size}  aspect {mark.width / mark.height:.2f}:1")

    ink = dominant_ink(wide)
    if ink:
        ratio = contrast_ratio(ink, (40, 40, 40))
        note = "OK" if ratio >= 4.5 else "TOO LOW -> dark screens must use the white variant"
        print(f"  brand ink #{ink[0]:02x}{ink[1]:02x}{ink[2]:02x} vs rgb(40,40,40): "
              f"{ratio:.2f}:1  {note}")

    thumb = Image.new("RGBA", (THUMB_BOX, THUMB_BOX), (0, 0, 0, 0))
    thumb.alpha_composite(fit_box(knockout(mark), THUMB_BOX - 2 * THUMB_INSET),
                          (THUMB_INSET, THUMB_INSET))

    outputs = {
        f"{args.prefix}_logo.png": fit_width(wide, LOGO_WIDTH),
        f"{args.prefix}_logo_white.png": knockout(fit_width(wide, LOGO_WIDTH)),
        f"{args.prefix}_mark.png": fit_box(mark, MARK_BOX),
        f"{args.prefix}_mark_white.png": knockout(fit_box(mark, MARK_BOX)),
        f"{args.prefix}_thumbnail.png": thumb,
    }

    print("\nwritten:")
    for name, im in outputs.items():
        path = os.path.join(args.out, name)
        im.save(path, "PNG", optimize=True)
        print(f"  {name:34s} {im.width:4d}x{im.height:<4d}")

    print("\nnext: register these in resource.qrc, run "
          "`pyrcc5 resource.qrc -o resource_rc.py`, then update branding.py")


if __name__ == "__main__":
    main()
