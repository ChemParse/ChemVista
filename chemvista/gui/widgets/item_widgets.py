from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon
import pathlib
import logging

# Import the compiled resources
from ..resources import icons_rc  # Add this import

# Create logger
logger = logging.getLogger("chemvista.widgets")


class ObjectTreeItem(QWidget):
    visibility_changed = pyqtSignal(bool)
    settings_clicked = pyqtSignal()

    UNKNOWN_ICON = ":/icons/icons/circle-outline.svg"

    TYPE_ICON_MAP = {
        'molecule': ":/icons/icons/molecule.svg",
        'scalar_field': ":/icons/icons/sine-wave.svg",
        'trajectory': ":/icons/icons/chart-timeline-variant.svg",
        'directory': ":/icons/icons/folder-outline.svg"
    }

    EYE_ICON_OPEN = ":/icons/icons/eye-outline.svg"
    EYE_ICON_CLOSED = ":/icons/icons/eye-off-outline.svg"
    COG_ICON = ":/icons/icons/cog-outline.svg"

    def __init__(self, name: str, obj_type: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.is_visible = True
        self._toggling_visibility = False  # Flag to prevent recursive calls
        self.uuid = None  # Will be set from ObjectTreeWidget

        # Log widget creation with type
        logger.debug(f"Creating widget for {name} with type {obj_type}")

        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)

        # Set a minimum size to ensure visibility
        self.setMinimumHeight(30)

        # Set background color to ensure visibility
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(palette)

        # Type icon - enhanced icon map
        # Get icon path with fallback to default
        icon_path = self.TYPE_ICON_MAP.get(
            obj_type, self.UNKNOWN_ICON)

        logger.debug(f'object type: {obj_type}, icon path: {icon_path}')

        type_icon = QLabel()
        type_icon.setPixmap(QIcon(icon_path).pixmap(24, 24))
        layout.addWidget(type_icon)

        # Name label
        self.name_label = QLabel(name)
        layout.addWidget(self.name_label)

        # Add stretch to push buttons to the right
        layout.addStretch()

        # Visibility toggle button
        self.vis_button = QPushButton()
        self.vis_button.setFixedSize(24, 24)
        self.vis_button.setToolTip("Toggle visibility")
        self.vis_button.setIcon(QIcon(self.EYE_ICON_OPEN))
        self.vis_button.clicked.connect(self._handle_visibility_click)
        self.vis_button.setFlat(True)
        layout.addWidget(self.vis_button)

        # Settings button
        self.settings_button = QPushButton()
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.setToolTip("Open settings")
        self.settings_button.setIcon(QIcon(self.COG_ICON))
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
                self.vis_button.setIcon(QIcon(self.EYE_ICON_OPEN))
            else:
                self.vis_button.setIcon(
                    QIcon(self.EYE_ICON_CLOSED))

            # Debug output
            print(
                f"Widget {self.name} visibility: {prev_state} -> {self.is_visible}")

            # Only emit signal if state actually changed
            if prev_state != self.is_visible:
                self.visibility_changed.emit(self.is_visible)
        finally:
            self._toggling_visibility = False


class MoleculeTreeItem(ObjectTreeItem):
    def __init__(self, name: str, parent=None):
        super().__init__(name, 'molecule', parent)
        # Molecule-specific functionality could be added here


class ScalarFieldTreeItem(ObjectTreeItem):
    def __init__(self, name: str, parent=None):
        super().__init__(name, 'scalar_field', parent)
        # ScalarField-specific functionality could be added here


class TrajectoryTreeItem(ObjectTreeItem):
    def __init__(self, name: str, parent=None):
        super().__init__(name, 'trajectory', parent)
        # Trajectory-specific functionality could be added here


class DirectoryTreeItem(ObjectTreeItem):
    def __init__(self, name: str, parent=None):
        super().__init__(name, 'directory', parent)
        # Directory-specific functionality could be added here


class UnknownTreeItem(ObjectTreeItem):
    def __init__(self, name: str, parent=None):
        super().__init__(name, 'unknown', parent)
        # Unknown type functionality could be added here


class TreeItemFactory:
    """Factory class for creating appropriate tree item widgets based on object type"""

    @staticmethod
    def create_item_for_object(obj, parent=None):
        """
        Create appropriate tree item widget based on object type

        Args:
            obj: The scene object to create an item for
            parent: Optional parent widget

        Returns:
            ObjectTreeItem: The appropriate tree item widget
        """
        from ...scene_objects import MoleculeObject, ScalarFieldObject, TrajectoryObject

        if isinstance(obj, MoleculeObject):
            return MoleculeTreeItem(obj.name, parent)
        elif isinstance(obj, ScalarFieldObject):
            return ScalarFieldTreeItem(obj.name, parent)
        elif isinstance(obj, TrajectoryObject):
            return TrajectoryTreeItem(obj.name, parent)
        elif hasattr(obj, 'children'):  # Directory/container type object
            return DirectoryTreeItem(obj.name, parent)
        else:
            return UnknownTreeItem(obj.name, parent)
