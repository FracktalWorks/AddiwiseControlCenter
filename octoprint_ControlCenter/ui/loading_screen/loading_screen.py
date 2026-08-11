import os
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QLabel, QProgressBar
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QMovie, QPixmap
from utils.helpers import check_ui_elements
from utils.logger import get_logger
from branding import BRAND
# Add resource import
import ui.resources.resource_rc

class LoadingScreen(QWidget):
    def __init__(self, main_window):
        super(LoadingScreen, self).__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.main_window = main_window
        
        try:
            # Use relative path from the current module's directory
            ui_file_path = os.path.join(os.path.dirname(__file__), "loading_screen.ui")
            uic.loadUi(ui_file_path, self)
            self.logger.info("LoadingScreen UI loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load LoadingScreen UI file: {e}")

        """ ---------- Initialize UI components ---------- """
        
        # Find and initialize UI components from the loading_screen.ui
        self.loading = self.findChild(QLabel, "loading")
        self.loadingProgressBar = self.findChild(QProgressBar, "loadingProgressBar")

        
        # Validate that all components were found
        all_components = [
            self.loading,
            self.loadingProgressBar
        ]
        
        # Use the helper function to check and report missing widgets
        check_ui_elements(self, all_components, "LoadingScreen")

        # Apply whitelabel artwork over the .ui's design-time pixmaps so a
        # rebrand only touches branding.py + resource.qrc, never the .ui files.
        self._apply_branding()

        # Initialize component states
        self.loadingProgressBar.setValue(0)
        self.loadingProgressBar.setMinimum(0)
        self.loadingProgressBar.setMaximum(100)
        
        self.loading.setText("Initializing...")
        
        self.logger.info("LoadingScreen components initialized successfully")

    def _apply_branding(self):
        """Swap the splash logos for the ones declared in branding.BRAND.

        The logo label is sized to the scaled pixmap instead of the .ui's fixed
        400x60 box, because OEM lockups differ in aspect ratio (Addiwise is
        3.3:1, the original Fracktal mark 6.6:1) and scaledContents would
        squash them. Fitting inside BRAND["logo_max_size"] keeps any future
        artwork undistorted without further code changes.

        Silently keeps whatever the .ui shipped with if an asset is missing
        from the compiled Qt resources -- a broken rebrand should degrade to
        the old logo, not to a blank splash screen.
        """
        max_w, max_h = BRAND["logo_max_size"]
        logos = [
            ("Logo", BRAND["logo_transparent"], True),
            ("controlCenterLogo", BRAND["logo_text"], False),
        ]
        for widget_name, resource_path, refit in logos:
            label = self.findChild(QLabel, widget_name)
            if label is None:
                continue
            pixmap = QPixmap(resource_path)
            if pixmap.isNull():
                self.logger.warning(
                    f"Branding asset not found in resources: {resource_path} "
                    f"-- keeping the pixmap baked into loading_screen.ui"
                )
                continue
            if refit:
                pixmap = pixmap.scaled(
                    max_w, max_h,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                # setFixedSize overrides the .ui's min/max size, which would
                # otherwise clamp the label back to 60px tall and clip the logo.
                label.setScaledContents(False)
                label.setFixedSize(pixmap.size())
                label.setAlignment(Qt.AlignCenter)
            label.setPixmap(pixmap)

    def update_progress(self, value, message="Loading..."):
        """Update the progress bar and loading message"""
        self.loadingProgressBar.setValue(value)
        self.loading.setText(message)
        # Force GUI update
        self.repaint()
        self.logger.info(f"Progress updated: {value}% - {message}")