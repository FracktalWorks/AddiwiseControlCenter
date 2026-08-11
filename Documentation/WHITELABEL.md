# Whitelabel Guide — Addiwise Control Center

This branch (`Addiwise_ControlCenter`) is the Addiwise Technologies OEM build of
Control Center. It is functionally identical to the Fracktal build; only
identity, artwork and the update channel differ.

All of that lives in **one file**: [`octoprint_ControlCenter/branding.py`](../octoprint_ControlCenter/branding.py).
Nothing else in the codebase should hardcode a company name, support URL, logo
path or repo. If you find one, move it into `BRAND` — that's the whole point of
the layer.

---

## Quick reference

| I want to… | Do this |
|---|---|
| Change a name, email or support URL | Edit `BRAND` in `branding.py`. Done. |
| Swap the logo artwork | Run `tools/make_brand_assets.py`, register in `resource.qrc`, recompile, point `BRAND` at the new files. See [Rebranding](#rebranding-from-scratch). |
| Change where updates come from | Edit `repo_user`/`repo_name` in `branding.py` **and** the `softwareupdate` block in `config/config.yaml`. Both. See [Update channel](#the-update-channel). |
| Pull in upstream fixes | See [Syncing with upstream](#syncing-with-upstream). |
| Cut a release | See [Releasing](#releasing). |

---

## How the branding layer works

`branding.py` is a plain dict plus four helpers. It is deliberately
dependency-free so it can be imported from all three contexts that need it:

```python
from branding import BRAND          # touch UI (package dir on sys.path)
from .branding import BRAND         # OctoPrint plugin (__init__.py)
sys.path.insert(0, "octoprint_ControlCenter"); from branding import BRAND   # setup.py
```

That last one matters: `setup.py` reads the same file the runtime does, so
packaging metadata and the running app can never disagree about who made this.

### What reads from it

| Consumer | Keys used |
|---|---|
| `setup.py` | `company`, `product`, `support_email`, `homepage_url()` |
| `__init__.py` → `get_update_information()` | `repo_user`, `repo_name`, `product`, `release_archive_url()` |
| `controller/main_controller.py` | `support_message()` — the config-corruption dialogs |
| `ui/loading_screen/loading_screen.py` | `logo_transparent`, `logo_text`, `logo_max_size` |
| `ui/home_screen/home_screen.py` | `thumbnail_placeholder` |
| `ui/print_from_location/print_from_location.py` | `thumbnail_placeholder` |
| `config/config.yaml`, `config/_default.profile` | **not** code — plain YAML, edited by hand |

Those last two are shipped config files, not Python, so they can't import
`branding.py`. **They must be kept in sync by hand.** This is the single most
likely thing to be forgotten in a future rebrand.

---

## Artwork

### The dark-background problem

Every screen sits on `rgb(40, 40, 40)`. Saturated brand colours are unreadable
there:

| Ink | vs `rgb(40,40,40)` | Verdict |
|---|---|---|
| Addiwise purple `#503890` | **1.62 : 1** | invisible |
| Knockout white `#f0f0f0` | **14.74 : 1** | correct |

So each mark ships in two variants, and **dark screens must use the `_white`
one**. This is not an Addiwise quirk — the original Fracktal splash artwork was
white knockout for exactly the same reason. `make_brand_assets.py` computes this
ratio on every run and warns you when the colour version won't work.

### The asset set

| File | Size | Where it appears |
|---|---|---|
| `addiwise_logo.png` | 800×243 | colour lockup — light backgrounds only |
| `addiwise_logo_white.png` | 800×243 | **splash screen**, drawn at 400×121 |
| `addiwise_mark.png` | 256×256 | colour gear mark |
| `addiwise_mark_white.png` | 256×256 | gear mark for dark UI |
| `addiwise_thumbnail.png` | 210×210 | print-preview placeholder (no GCODE thumbnail) |
| `control_center_logo_text.png` | 1486×90 | "CONTROL CENTER" wordmark — **unbranded, shared by all OEMs, do not replace** |

### Aspect ratios are not interchangeable

The splash `QLabel` is a fixed 400×60 with `scaledContents=true`. The Fracktal
lockup was 6.6:1, so it fit that box natively. **The Addiwise lockup is 3.3:1**
— dropped into the same box it would be squashed to half height.

`LoadingScreen._apply_branding()` handles this: it scales with
`Qt.KeepAspectRatio` into `BRAND["logo_max_size"]` and then resizes the label to
the resulting pixmap, overriding the `.ui`'s fixed geometry. The surrounding
vertical spacers absorb the extra height.

**Consequence for future rebrands:** any aspect ratio works without touching a
`.ui` file. Just drop the art in and adjust `logo_max_size` if you want it
bigger or smaller.

### Rebranding from scratch

```bash
# 1. Generate the full asset set from a wide lockup and a square mark.
#    Sources should be transparent PNGs; padding is cropped automatically.
python tools/make_brand_assets.py \
    --wide  /path/to/OEM_wide.png \
    --mark  /path/to/OEM_square.png \
    --prefix oemname

# 2. Register the outputs in the "Logos & Branding" qresource block.
$EDITOR octoprint_ControlCenter/ui/resources/resource.qrc

# 3. Recompile. THIS IS NOT OPTIONAL — the app reads resource_rc.py,
#    never the PNGs on disk. Skipping it means your changes do nothing.
cd octoprint_ControlCenter/ui/resources
pyrcc5 resource.qrc -o resource_rc.py

# 4. Point BRAND at the new resource paths.
$EDITOR octoprint_ControlCenter/branding.py
```

Resource paths use the qrc *prefix*, not the directory:
`:/Logos & Branding/img/Logos/foo.png`. Note the spaces and the ampersand.

### Verifying artwork without a printer

Render the real splash offscreen and look at it:

```bash
cd octoprint_ControlCenter
QT_QPA_PLATFORM=offscreen python -c "
import sys; sys.path.insert(0,'.')
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
from ui.loading_screen.loading_screen import LoadingScreen
ls = LoadingScreen(main_window=None); ls.resize(800,480)
ls.update_progress(70, 'Loading...')
ls.grab().save('/tmp/splash.png')
"
```

Check every `BRAND` asset actually resolves — a typo yields a silent blank, since
`_apply_branding()` deliberately falls back to the `.ui` pixmap rather than
crashing the splash:

```bash
QT_QPA_PLATFORM=offscreen python -c "
import sys; sys.path.insert(0,'.')
from PyQt5.QtWidgets import QApplication; from PyQt5.QtGui import QPixmap
app = QApplication(sys.argv)
import ui.resources.resource_rc
from branding import BRAND
for k in ('logo','logo_transparent','mark','mark_transparent','logo_text','thumbnail_placeholder'):
    print(k, 'MISSING' if QPixmap(BRAND[k]).isNull() else 'ok')
"
```

---

## The update channel

Units check `FracktalWorks/AddiwiseControlCenter` for new GitHub releases. This
is configured in **two places that must agree**:

1. `octoprint_ControlCenter/__init__.py` → `get_update_information()` (reads `BRAND`)
2. `octoprint_ControlCenter/config/config.yaml` → `plugins.softwareupdate.checks.ControlCenter` (hand-edited)

> **The repo must stay public.** OctoPrint's `softwareupdate` plugin fetches
> release metadata and the pip archive unauthenticated. Flipping the repo to
> private silently breaks updates on every unit in the field. The sibling OEM
> repos (`PenroseControlCenter`, `VolterraControlCenter`) are public for the
> same reason.

> **Do not rename the plugin identifier.** It is `ControlCenter` in `setup.py`,
> and the `softwareupdate` check key in `config.yaml` matches on it. Renaming
> either without the other breaks updates. `__plugin_name__` is only the
> human-readable display string and is safe to brand.

---

## Things that must NOT be rebranded

| Item | Why |
|---|---|
| `kinematics: fracktal_hybrid_corexy` in `firmware/PRINTER_*.cfg` | A Klipper kinematics **module name**, not branding. Renaming it stops the printer from moving. |
| Plugin identifier `ControlCenter` in `setup.py` | The softwareupdate check key matches on it. |
| `control_center_logo_text.png` | Product wordmark, not company branding. Shared across OEM builds. |

---

## Syncing with upstream

Feature work and bug fixes happen on `production` in
`FracktalWorks/ControlCenter`. This repo consumes them.

```bash
git remote add upstream https://github.com/FracktalWorks/ControlCenter.git
git fetch upstream
git merge upstream/production
```

The branding layer exists specifically to make this cheap: upstream almost never
touches `branding.py`, so merges rarely conflict on identity. Expect conflicts
only in the handful of wired call sites listed in
[What reads from it](#what-reads-from-it).

**After every merge, re-check:**

- `config.yaml` — upstream may have reset the `softwareupdate` block to `FracktalWorks/ControlCenter`.
- `_default.profile` — upstream may have reset `model:`.
- `resource.qrc` — upstream may have re-added the Fracktal artwork (see below).
- `resource_rc.py` — if `resource.qrc` changed at all, recompile.

```bash
# Fast post-merge audit: anything here that isn't a comment is a regression.
grep -rn "Fracktal\|fracktal" --include=*.py --include=*.ui --include=*.qrc \
     --include=*.yaml --include=*.profile octoprint_ControlCenter/ \
     | grep -v resource_rc.py
```

### Fracktal artwork is intentionally not compiled in

The Fracktal PNGs are still **on disk** — so merges from `production` stay clean
— but they are **unregistered from `resource.qrc`**, so they never enter the
Addiwise binary. Shipping a competitor's mark inside an OEM product would be
wrong even unused. `resource.qrc` carries a comment explaining this; if a merge
re-adds those `<file>` lines, remove them again and recompile.

---

## Releasing

Versioning is handled by `versioneer` and driven entirely by git tags.

```bash
git tag 1.2.3
git push origin 1.2.3
gh release create 1.2.3 --repo FracktalWorks/AddiwiseControlCenter \
   --title "1.2.3" --notes "..."
```

Units then see the update on their next check. Verify the archive URL in the
release resolves, since that's what pip actually installs:

```
https://github.com/FracktalWorks/AddiwiseControlCenter/archive/1.2.3.zip
```

> Version tags are per-repo. Addiwise release numbers are independent of
> Fracktal's — don't assume `1.2.3` here matches `1.2.3` upstream.

---

## Deploying to a unit

The plugin installs into OctoPrint on the printer's Raspberry Pi:

```bash
ssh pi@<printer-ip>
source ~/oprint/bin/activate   # OctoPrint's venv
pip install --upgrade https://github.com/FracktalWorks/AddiwiseControlCenter/archive/<tag>.zip
sudo systemctl restart octoprint
```

`resource_rc.py` is ~19 MB of compiled artwork and **must be committed** — the
`resources` directory is listed in `plugin_additional_data` in `setup.py`, and
the UI fails at import with `ModuleNotFoundError: No module named 'ui.resources'`
without it.

---

## Adding a new OEM build

1. Branch from `production` (not from this branch — you don't want Addiwise art).
2. Copy `branding.py` across and edit every value.
3. Run `make_brand_assets.py` with the new artwork and a new `--prefix`.
4. Update `resource.qrc` + recompile; update `config.yaml` and `_default.profile`.
5. Create `FracktalWorks/<Oem>ControlCenter`, public, matching the existing
   naming convention.

If you find yourself editing a third file to change a name, that string belongs
in `BRAND` instead.
