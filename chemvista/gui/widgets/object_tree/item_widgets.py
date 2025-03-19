import logging
import pathlib

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from ....scene_objects import (MoleculeObject, ScalarFieldObject,
                               TrajectoryObject)
from ....tree_structure import TreeNode
# Import the compiled resources
from ...resources import icons_rc
from ...widgets.settings_dialog import (RenderSettingsDialog,
                                        ScalarFieldSettingsDialog)

# Create logger
logger = logging.getLogger(
    "chemvista.ui.widgets.object_tree_widget.item_widgets")


class ObjectTreeItem(QWidget):
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

    def __init__(self, name: str, obj_type: str, obj: TreeNode, parent=None):
        super().__init__(parent)
        self.name = name
        self.obj = obj
        self.is_visible = True
        self.uuid = self.obj.uuid

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
        if self.visible:
            self._set_vis_on()
        else:
            self._set_vis_off()
        self.vis_button.clicked.connect(self._handle_visibility_click)
        self.vis_button.setFlat(True)
        layout.addWidget(self.vis_button)

        # Settings button
        self.settings_button = QPushButton()
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.setToolTip("Open settings")
        self.settings_button.setIcon(QIcon(self.COG_ICON))
        self.settings_button.clicked.connect(self._settings_clicked)
        self.settings_button.setFlat(True)
        layout.addWidget(self.settings_button)

        self.setLayout(layout)

    @property
    def visible(self):
        """Get the visibility state"""
        return self.obj.visible

    @visible.setter
    def visible(self, value):
        """Set the visibility state"""
        self.obj.visible = value

    def _set_vis_on(self):
        self.vis_button.setIcon(QIcon(self.EYE_ICON_OPEN))

    def _set_vis_off(self):
        self.vis_button.setIcon(QIcon(self.EYE_ICON_CLOSED))

    def _toggle_visibility(self, force_state):
        """Toggle visibility with optional forced state"""

        logger.debug(f"Visibility toggled for {self.name}: {force_state}")
        # Update the icon based on the new state
        if force_state:
            self._set_vis_on()
        else:
            self._set_vis_off()

        self.visible = force_state

    def _handle_visibility_click(self):
        """Handle visibility button click"""
        self._toggle_visibility(not self.visible)

    def _settings_clicked(self):
        """Handle settings button click"""
        logger.debug(f"Settings clicked for {self.name}")

        if isinstance(self.obj, ScalarFieldObject):
            dialog = ScalarFieldSettingsDialog(self.obj.render_settings, self)
            if dialog.exec_():
                self.obj.render_settings = dialog.get_settings()
                logger.debug(f"Updated scalar field settings for {self.name}")

        elif isinstance(self.obj, MoleculeObject):
            dialog = RenderSettingsDialog(self.obj.render_settings, self)
            if dialog.exec_():
                self.obj.render_settings = dialog.get_settings()
                logger.debug(
                    f"Updated molecule render settings for {self.name}")

        elif isinstance(self.obj, TrajectoryObject):
            # For trajectories, we use the same dialog as molecules
            dialog = RenderSettingsDialog(self.obj.render_settings, self)
            if dialog.exec_():
                self.obj.render_settings = dialog.get_settings()
                logger.debug(
                    f"Updated trajectory render settings for {self.name}")

        else:
            logger.debug(f"No settings dialog available for {self.name}")


class MoleculeTreeItem(ObjectTreeItem):
    def __init__(self, name: str, obj, parent=None):
        super().__init__(name, 'molecule', obj=obj, parent=parent)
        # Molecule-specific functionality could be added here


class ScalarFieldTreeItem(ObjectTreeItem):
    def __init__(self, name: str, obj, parent=None):
        super().__init__(name, 'scalar_field', obj=obj, parent=parent)
        # ScalarField-specific functionality could be added here


class TrajectoryTreeItem(ObjectTreeItem):
    def __init__(self, name: str, obj, parent=None):
        super().__init__(name, 'trajectory', obj=obj, parent=parent)
        # Trajectory-specific functionality could be added here


class DirectoryTreeItem(ObjectTreeItem):
    def __init__(self, name: str, obj, parent=None):
        super().__init__(name, 'directory', obj=obj, parent=parent)
        # Directory-specific functionality could be added here


class UnknownTreeItem(ObjectTreeItem):
    def __init__(self, name: str, obj, parent=None):
        super().__init__(name, 'unknown', obj=obj, parent=parent)
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

        if isinstance(obj, MoleculeObject):
            return MoleculeTreeItem(obj.name, obj, parent)
        elif isinstance(obj, ScalarFieldObject):
            return ScalarFieldTreeItem(obj.name, obj, parent)
        elif isinstance(obj, TrajectoryObject):
            return TrajectoryTreeItem(obj.name, obj, parent)
        elif hasattr(obj, 'children'):  # Directory/container type object
            return DirectoryTreeItem(obj.name, obj, parent)
        else:
            return UnknownTreeItem(obj.name, obj, parent)
