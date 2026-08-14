#!/usr/bin/env python3
"""Deploy the Addiwise brand logo into the OctoPrint web UI on the printer.

OctoPrint does not expose a config.yaml setting for its logo -- the header icon
and favicon are static files (`static/img/tentacle-*.png`) and the login/about
pages use `static/img/logo.svg`. OEM builds like the Fracktal one brand these
files directly, so this script does the same with the Addiwise artwork:

  * every `tentacle-<W>x<H>.png` (incl. the `@2x` and `-light` variants) is
    replaced with the Addiwise gear mark, resized to the dimensions encoded in
    the filename (`-light` variants use the white knockout mark),
  * `logo.svg` is replaced with an SVG embedding the Addiwise lockup so the
    login page shows the Addiwise logo,
  * the original files are backed up to `static/img/_brand_backup_<date>/`
    so the change is reversible.

Usage (run on the printer, inside the OctoPrint venv if possible):

    python tools/deploy_octoprint_logo.py
    python tools/deploy_octoprint_logo.py --octoprint-dir /home/pi/oprint/lib/python3.11/site-packages/octoprint

Requires Pillow for resizing:  pip install Pillow
"""
import argparse
import base64
import glob
import os
import re
import shutil
import sys
from datetime import datetime

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")

# Assets shipped with the Addiwise build (relative to this repo's root).
# Override with --assets-dir when running on the printer against the installed
# plugin's resource folder.
MARK = os.path.join("octoprint_ControlCenter", "ui", "resources", "img", "Logos", "addiwise_mark.png")
MARK_WHITE = os.path.join("octoprint_ControlCenter", "ui", "resources", "img", "Logos", "addiwise_mark_white.png")
LOCKUP = os.path.join("octoprint_ControlCenter", "ui", "resources", "img", "Logos", "addiwise_logo.png")

# Common roots where the `octoprint` package may live on a Raspberry Pi.
COMMON_ROOTS = [
    "/home/pi/oprint/lib",
    "/home/pi/oenv/lib",
    "/usr/local/lib",
    "/usr/lib",
    "/opt/octoprint",
]


def find_octoprint_dir(override=None):
    """Locate the octoprint package directory (the one containing static/img)."""
    if override:
        if os.path.isdir(os.path.join(override, "static", "img")):
            return override
        sys.exit("--octoprint-dir does not look like an OctoPrint package dir: " + override)

    # 1) Try importing from the current interpreter (works when run in the venv).
    try:
        import octoprint
        pkg_dir = os.path.dirname(os.path.abspath(octoprint.__file__))
        if os.path.isdir(os.path.join(pkg_dir, "static", "img")):
            return pkg_dir
    except Exception:
        pass

    # 2) Fall back to scanning common install roots for the octoprint package.
    for root in COMMON_ROOTS:
        pattern = os.path.join(root, "**", "octoprint")
        for candidate in glob.glob(pattern, recursive=True):
            if os.path.isdir(os.path.join(candidate, "static", "img")):
                return candidate

    sys.exit(
        "Could not locate the OctoPrint package. Pass --octoprint-dir explicitly, "
        "or run this script from inside the OctoPrint virtualenv."
    )


def size_from_filename(name):
    """Return (width, height) encoded in tentacle filenames, e.g. 20x20@2x -> (40, 40)."""
    m = re.search(r"(\d+)x(\d+)(?:-light)?(?:@(\d+)x)?", name)
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    if m.group(3):
        scale = int(m.group(3))
        w, h = w * scale, h * scale
    return w, h


def embed_svg(lockup_path):
    """Build an <svg> that displays the Addiwise lockup via an embedded PNG."""
    with open(lockup_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    try:
        with Image.open(lockup_path) as im:
            w, h = im.size
    except Exception:
        w, h = 800, 243
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        f'  <image width="{w}" height="{h}" '
        f'xlink:href="data:image/png;base64,{b64}"/>\n'
        "</svg>\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--octoprint-dir", default=None,
                        help="Path to the octoprint package dir (contains static/img).")
    parser.add_argument("--assets-dir", default=None,
                        help="Directory holding addiwise_mark.png, addiwise_mark_white.png "
                             "and addiwise_logo.png (defaults to this repo's Logos folder).")
    args = parser.parse_args()

    if args.assets_dir:
        global MARK, MARK_WHITE, LOCKUP
        MARK = os.path.join(args.assets_dir, "addiwise_mark.png")
        MARK_WHITE = os.path.join(args.assets_dir, "addiwise_mark_white.png")
        LOCKUP = os.path.join(args.assets_dir, "addiwise_logo.png")

    pkg_dir = find_octoprint_dir(args.octoprint_dir)
    img_dir = os.path.join(pkg_dir, "static", "img")
    print("OctoPrint package: {0}".format(pkg_dir))
    print("Static img dir:    {0}".format(img_dir))

    # Back up originals once.
    backup_dir = os.path.join(img_dir, "_brand_backup_{0}".format(datetime.now().strftime("%Y%m%d_%H%M%S")))
    os.makedirs(backup_dir, exist_ok=True)
    print("Backup dir:        {0}".format(backup_dir))

    if not os.path.exists(MARK) or not os.path.exists(LOCKUP):
        sys.exit("Addiwise artwork not found. Run this from the repo root "
                 "(expected {0} and {1}).".format(MARK, LOCKUP))

    replaced = []

    # 1) Navbar/favicon tentacle icons.
    for tentacle in sorted(glob.glob(os.path.join(img_dir, "tentacle-*.png"))):
        name = os.path.basename(tentacle)
        dims = size_from_filename(name)
        if not dims:
            continue
        shutil.copy2(tentacle, os.path.join(backup_dir, name))
        source = MARK_WHITE if "light" in name else MARK
        with Image.open(source) as im:
            im = im.convert("RGBA").resize(dims, Image.LANCZOS)
            im.save(tentacle, "PNG")
        replaced.append(name)
        print("  replaced {0} ({1}x{2})".format(name, dims[0], dims[1]))

    # 2) Login / about page logo.
    logo_svg = os.path.join(img_dir, "logo.svg")
    if os.path.exists(logo_svg):
        shutil.copy2(logo_svg, os.path.join(backup_dir, "logo.svg"))
        with open(logo_svg, "w") as f:
            f.write(embed_svg(LOCKUP))
        replaced.append("logo.svg")
        print("  replaced logo.svg (Addiwise lockup embedded)")

    # 3) Also handle the login page's standalone logo PNG if an OEM added one.
    for extra in ("logo.png", "brand-logo.png"):
        path = os.path.join(img_dir, extra)
        if os.path.exists(path):
            shutil.copy2(path, os.path.join(backup_dir, extra))
            shutil.copy2(LOCKUP, path)
            replaced.append(extra)
            print("  replaced {0}".format(extra))

    if not replaced:
        print("No OctoPrint logo assets found to replace under {0}.".format(img_dir))
        print("You may need to restart OctoPrint and hard-refresh your browser.")
        return

    print("")
    print("Done. Replaced {0} asset(s).".format(len(replaced)))
    print("Restart OctoPrint, then hard-refresh the web UI (Ctrl+F5):")
    print("    sudo service octoprint restart")
    print("To restore the originals: copy them back from {0}".format(backup_dir))


if __name__ == "__main__":
    main()
