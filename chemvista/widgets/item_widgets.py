from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon
import pathlib
# Import the compiled resources
from ..resources import icons_rc  # Add this import


class BaseItemWidget(QWidget):
    visibility_changed = pyqtSignal(bool)
    settings_clicked = pyqtSignal()

    def __init__(self, name: str, obj_type: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.is_visible = True
        self._toggling_visibility = False  # Flag to prevent recursive calls

        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)

        # Set a minimum size to ensure visibility
        self.setMinimumHeight(30)

        # Set background color to ensure visibility
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(palette)

        # Type icon
        type_icon_map = {
            'molecule': ":/icons/icons/molecule.svg",
            'scalar_field': ":/icons/icons/sine-wave.svg",
            'trajectory': ":/icons/icons/chart-timeline-variant.svg"
        }
        type_icon = QLabel()
        type_icon.setPixmap(QIcon(type_icon_map.get(
            obj_type, type_icon_map['molecule'])).pixmap(24, 24))
        layout.addWidget(type_icon)

        # Name label
        self.label = QLabel(name)
        layout.addWidget(self.label)

        # Add stretch to push buttons to the right
        layout.addStretch()

        # Visibility toggle button
        self.vis_button = QPushButton()
        self.vis_button.setFixedSize(24, 24)
        self.vis_button.setToolTip("Toggle visibility")
        self.vis_button.setIcon(QIcon(":/icons/icons/eye-outline.svg"))
        self.vis_button.clicked.connect(self._handle_visibility_click)
        self.vis_button.setFlat(True)
        layout.addWidget(self.vis_button)

        # Settings button
        self.settings_button = QPushButton()
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.setToolTip("Open settings")
        self.settings_button.setIcon(QIcon(":/icons/icons/cog-outline.svg"))
        self.settings_button.clicked.connect(self.settings_clicked.emit)
        self.settings_button.setFlat(True)
        layout.addWidget(self.settings_button)

        self.setLayout(layout)

    def _handle_visibility_click(self):
        """Handle visibility button click manually"""
        if not self._toggling_visibility:
            self._toggle_visibility(force_state=not self.is_visible)

    def _toggle_visibility(self, force_state=None):
        """Toggle visibility with optional forced state"""
        self._toggling_visibility = True

        try:
            prev_state = self.is_visible

            # Update the state
            if force_state is not None:
                self.is_visible = force_state
            else:
                self.is_visible = not self.is_visible

            # Update the icon based on the new state
            if self.is_visible:
                self.vis_button.setIcon(QIcon(":/icons/icons/eye-outline.svg"))
            else:
                self.vis_button.setIcon(
                    QIcon(":/icons/icons/eye-off-outline.svg"))

            # Debug output
            print(
                f"Widget {self.name} visibility: {prev_state} -> {self.is_visible}")

            # Only emit signal if state actually changed
            if prev_state != self.is_visible:
                self.visibility_changed.emit(self.is_visible)
        finally:
            self._toggling_visibility = False


class ObjectTreeItem(BaseItemWidget):
    """Tree widget item for both molecules and scalar fields"""

    def __init__(self, name: str, obj_type: str = 'molecule', parent=None):
        super().__init__(name, obj_type, parent)


# Keep MoleculeListItem for backward compatibility
class MoleculeListItem(BaseItemWidget):
    """Deprecated: Use ObjectTreeItem instead"""

    def __init__(self, name: str, obj_type: str = 'molecule', parent=None):
        super().__init__(name, obj_type, parent)
