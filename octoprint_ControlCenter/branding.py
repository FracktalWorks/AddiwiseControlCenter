"""Whitelabel branding definitions for Control Center.

Single source of truth for every OEM-specific string, asset path and update
channel in the application. Nothing else in the codebase should hardcode a
company name, support URL or logo path -- import from here instead.

To produce a new whitelabel build:
  1. Drop the OEM logo/splash PNGs into ui/resources/img/Logos/.
  2. Register them in ui/resources/resource.qrc and recompile:
         pyrcc5 resource.qrc -o resource_rc.py
  3. Edit the BRAND dict below to point at the new names, URLs and assets.

Importable from both execution contexts:
  - Touch UI (package dir on sys.path):   from branding import BRAND
  - OctoPrint plugin (package import):    from .branding import BRAND
"""

BRAND = {
    # --- Identity -----------------------------------------------------------
    # Company that ships this build. Shown in the OctoPrint plugin manager.
    "company": "Addiwise Technologies",
    # Product name shown in the UI and used as the OctoPrint plugin display name.
    "product": "Control Center",

    # --- Support ------------------------------------------------------------
    # Surfaced in error dialogs when the user needs to reach the OEM.
    "support_email": "support@addiwise.com",
    # Bare host (no scheme) -- appears inline in dialog text.
    "support_portal": "care.addiwise.com",

    # --- Update channel -----------------------------------------------------
    # GitHub repo the OctoPrint softwareupdate plugin checks for new releases.
    # Hosted under the FracktalWorks org, following the naming already used for
    # the other OEM builds (PenroseControlCenter, VolterraControlCenter).
    #
    # This repo MUST stay public: OctoPrint's softwareupdate plugin fetches
    # release metadata and the pip archive unauthenticated, so making it
    # private silently breaks updates on every unit in the field.
    "repo_user": "FracktalWorks",
    "repo_name": "AddiwiseControlCenter",

    # --- Printer profile ----------------------------------------------------
    # Default OctoPrint printer profile model string.
    "printer_series": "Addiwise Series",

    # --- Assets -------------------------------------------------------------
    # Qt resource paths. Must match files registered in resource.qrc; run
    # `pyrcc5 resource.qrc -o resource_rc.py` after changing either side.
    #
    # The splash sits on rgb(40,40,40), where the Addiwise purple (#503890)
    # only reaches 1.62:1 contrast -- illegible. Screens with a dark backdrop
    # therefore use the reversed *_white* knockouts (14.7:1), which is the same
    # treatment the original Fracktal splash artwork used.
    "logo": ":/Logos & Branding/img/Logos/addiwise_logo.png",
    "logo_transparent": ":/Logos & Branding/img/Logos/addiwise_logo_white.png",
    "mark": ":/Logos & Branding/img/Logos/addiwise_mark.png",
    "mark_transparent": ":/Logos & Branding/img/Logos/addiwise_mark_white.png",
    # Product wordmark ("CONTROL CENTER") -- unbranded, shared by every OEM.
    "logo_text": ":/Logos & Branding/img/Logos/control_center_logo_text.png",
    # Stand-in shown in the print preview when a GCODE file has no thumbnail.
    "thumbnail_placeholder": ":/Logos & Branding/img/Logos/addiwise_thumbnail.png",
    "splash_background": ":/Misc/img/Splash BG.png",

    # Bounding box (w, h) the splash logo is fitted into, aspect preserved.
    # The Addiwise lockup is 3.3:1 against Fracktal's 6.6:1, so the label is
    # resized to the scaled pixmap rather than stretched to a fixed 400x60.
    "logo_max_size": (400, 130),
}


def homepage_url():
    """Public URL for this build -- plugin homepage and update release notes."""
    return "https://github.com/{user}/{repo}".format(
        user=BRAND["repo_user"], repo=BRAND["repo_name"]
    )


def release_archive_url():
    """pip-installable archive URL template used by OctoPrint's updater."""
    return homepage_url() + "/archive/{target_version}.zip"


def release_notes_url():
    """Release notes URL template used by OctoPrint's updater."""
    return homepage_url() + "/releases/tag/{target_version}"


def support_message():
    """Standard 'contact the OEM' sentence used across error dialogs."""
    return "Contact {company} support or raise a ticket at {portal}".format(
        company=BRAND["company"], portal=BRAND["support_portal"]
    )
