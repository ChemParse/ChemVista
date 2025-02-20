from PyQt5.QtWidgets import QListWidget, QListWidgetItem
from PyQt5.QtCore import pyqtSignal, Qt
from .item_widgets import MoleculeListItem


class ObjectListWidget(QListWidget):
    selection_changed = pyqtSignal()
    visibility_changed = pyqtSignal(int, bool)
    settings_requested = pyqtSignal(int)

    def __init__(self, scene_manager, parent=None):
        super().__init__(parent)
        self.scene_manager = scene_manager

        # Connect to scene manager signals
        self.scene_manager.object_added.connect(self._on_object_added)
        self.scene_manager.object_removed.connect(self._on_object_removed)
        self.scene_manager.object_changed.connect(self._on_object_changed)
        self.scene_manager.visibility_changed.connect(
            self._on_visibility_changed)

        # Initialize list with existing objects
        self._refresh_list()

    def _refresh_list(self):
        """Refresh the entire list"""
        self.clear()
        for obj in self.scene_manager.objects:
            self._add_item(obj.name, obj.visible)

    def _add_item(self, name: str, visible: bool = True):
        """Add a new item to the list with custom widget"""
        item = QListWidgetItem(self)
        self.addItem(item)

        widget = MoleculeListItem(name)
        widget.visibility_changed.connect(lambda v, idx=self.row(
            item): self.visibility_changed.emit(idx, v))
        widget.settings_clicked.connect(lambda idx=self.row(
            item): self.settings_requested.emit(idx))

        # Set initial visibility state
        if not visible:
            widget._toggle_visibility()  # This will update the icon and emit signal

        item.setSizeHint(widget.sizeHint())
        self.setItemWidget(item, widget)

    def _on_object_added(self, name: str):
        """Handle new object added to scene"""
        obj = self.scene_manager.get_object_by_name(name)
        self._add_item(name, obj.visible)

    def _on_object_removed(self, name: str):
        """Handle object removed from scene"""
        for i in range(self.count()):
            item = self.item(i)
            if self.itemWidget(item).name == name:
                self.takeItem(i)
                break

    def _on_object_changed(self, name: str):
        """Handle object changes"""
        self._refresh_list()

    def _on_visibility_changed(self, name: str, visible: bool):
        """Handle visibility changes from scene manager"""
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if widget.name == name and widget.is_visible != visible:
                widget._toggle_visibility()

    def get_selected_index(self):
        """Get currently selected item index"""
        current = self.currentItem()
        return self.row(current) if current else None
