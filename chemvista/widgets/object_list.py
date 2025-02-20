from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PyQt5.QtCore import pyqtSignal
from .item_widgets import MoleculeListItem


class ObjectListWidget(QWidget):
    selection_changed = pyqtSignal(int)
    visibility_changed = pyqtSignal(int, bool)
    settings_requested = pyqtSignal(int)

    def __init__(self, scene_manager, parent=None):
        super().__init__(parent)
        self.scene_manager = scene_manager

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.itemSelectionChanged.connect(
            self._on_selection_changed)
        layout.addWidget(self.list_widget)

        # Connect to scene manager signals
        self.scene_manager.object_added.connect(self._on_object_added)
        self.scene_manager.object_removed.connect(self._on_object_removed)

        self.setLayout(layout)

    def _on_object_added(self, scene_obj):
        item = QListWidgetItem(self.list_widget)
        widget = MoleculeListItem(scene_obj.name)

        # Connect widget signals
        index = self.list_widget.count() - 1
        widget.visibility_changed.connect(
            lambda visible: self.visibility_changed.emit(index, visible))
        widget.settings_clicked.connect(
            lambda: self.settings_requested.emit(index))

        # Set item size and add widget
        self.list_widget.addItem(item)
        item.setSizeHint(widget.sizeHint())
        self.list_widget.setItemWidget(item, widget)

    def _on_object_removed(self, index):
        self.list_widget.takeItem(index)

    def _on_selection_changed(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            index = self.list_widget.row(selected_items[0])
            self.selection_changed.emit(index)

    def get_selected_index(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            return self.list_widget.row(selected_items[0])
        return None
