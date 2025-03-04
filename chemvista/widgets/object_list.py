from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from typing import Optional, Dict, List
from .item_widgets import ObjectTreeItem
import logging

# Create logger
logger = logging.getLogger("chemvista.ui.tree")


class ObjectTreeWidget(QTreeWidget):
    selection_changed = pyqtSignal(str)  # emits UUID
    visibility_changed = pyqtSignal(str, bool)  # emits UUID and visibility
    settings_requested = pyqtSignal(str)  # emits UUID
    structure_changed = pyqtSignal()  # emits when drag-drop changes structure

    def __init__(self, scene_manager, parent=None):
        super().__init__(parent)
        self.scene_manager = scene_manager
        self.setHeaderHidden(True)
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.setExpandsOnDoubleClick(True)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.MoveAction)

        # Initialize the UUID to QTreeWidgetItem mapping
        self._uuid_items = {}
        self._processing_drop = False

        # Connect to scene manager signals - use hasattr to check if the signal exists
        self.scene_manager.object_added.connect(self._refresh_tree)
        self.scene_manager.object_removed.connect(self._refresh_tree)
        if hasattr(self.scene_manager, 'structure_changed'):
            self.scene_manager.structure_changed.connect(self._refresh_tree)
        self.scene_manager.visibility_changed.connect(
            self._on_visibility_changed)

        # Connect selection signals
        self.itemSelectionChanged.connect(self._on_selection_changed)

        self._refresh_tree()

    def _on_selection_changed(self):
        """Handle selection changes"""
        selected_uuid = self.get_selected_uuid()
        if selected_uuid:
            self.selection_changed.emit(selected_uuid)

    def dropEvent(self, event):
        """Handle drop event and update scene structure"""
        self._processing_drop = True
        # Get the items being dragged
        dragged_items = self.selectedItems()
        if not dragged_items:
            event.ignore()
            self._processing_drop = False
            return

        # Store UUIDs and parent UUIDs before the drag operation changes the tree
        before_drag_info = {}
        for item in dragged_items:
            widget = self.itemWidget(item, 0)
            if not hasattr(widget, 'uuid'):
                continue

            uuid = widget.uuid
            parent_item = item.parent()
            parent_uuid = None
            if parent_item:
                parent_widget = self.itemWidget(parent_item, 0)
                if hasattr(parent_widget, 'uuid'):
                    parent_uuid = parent_widget.uuid

            before_drag_info[uuid] = {
                'parent_uuid': parent_uuid,
                'old_index': parent_item.indexOfChild(item) if parent_item else self.indexOfTopLevelItem(item),
                'was_scalar_field_of_molecule': self._is_scalar_field_of_molecule(uuid, parent_uuid),
                'is_visible': widget.is_visible  # Store visibility state
            }

        # Let Qt handle the standard drop operation
        super().dropEvent(event)

        # Update scene structure based on new tree structure
        try:
            self._update_structure_after_drop(before_drag_info)
            self.structure_changed.emit()
        except Exception as e:
            logger.error(f"Error updating scene structure: {e}")

        self._processing_drop = False

    def _is_scalar_field_of_molecule(self, field_uuid: str, parent_uuid: str) -> bool:
        """Check if the scalar field belongs to the molecule's scalar_fields dict"""
        if not parent_uuid:
            return False

        try:
            field_obj = self.scene_manager.get_object_by_uuid(field_uuid)
            parent_obj = self.scene_manager.get_object_by_uuid(parent_uuid)

            # Check if this is a scalar field and belongs to a molecule
            if (hasattr(field_obj, 'scalar_field') and
                hasattr(parent_obj, 'molecule') and
                    hasattr(parent_obj.molecule, 'scalar_fields')):

                # Check if this field is in the molecule's scalar_fields dictionary
                for key, sf in parent_obj.molecule.scalar_fields.items():
                    if sf == field_obj.scalar_field:
                        return True
        except:
            pass

        return False

    def _update_structure_after_drop(self, before_drag_info: Dict[str, Dict]):
        """Update scene structure based on tree widget structure after drop"""
        changes = []
        for uuid, info in before_drag_info.items():
            # Find the item in the tree after drop
            item = self._uuid_items.get(uuid)
            if not item:
                continue

            # Get new parent information
            new_parent_item = item.parent()
            new_parent_uuid = None
            if new_parent_item:
                new_parent_widget = self.itemWidget(new_parent_item, 0)
                if hasattr(new_parent_widget, 'uuid'):
                    new_parent_uuid = new_parent_widget.uuid

            # Get the object
            obj = self.scene_manager.get_object_by_uuid(uuid)
            old_parent_uuid = info['parent_uuid']

            # Case 1: No parent change - just reordering
            if old_parent_uuid == new_parent_uuid:
                self._handle_reordering(
                    uuid, old_parent_uuid, item, new_parent_item)
                continue

            # Case 2: Scalar field was part of a molecule but now is standalone
            if info['was_scalar_field_of_molecule'] and (new_parent_uuid is None or
                                                         not self._is_scalar_field_of_molecule(uuid, new_parent_uuid)):
                self._handle_scalar_field_detaching(uuid, old_parent_uuid)

            # Update parent-child relationship in the scene
            self._update_parent_child_relationship(
                uuid, old_parent_uuid, new_parent_uuid)

        # Log the entire tree after changes using the new format_tree method
        try:
            self.scene_manager.log_tree_changes(
                "Tree structure updated after drag-and-drop")
        except AttributeError:
            # Fall back if log_tree_changes is not available
            logger.info("Tree structure updated after drag-and-drop")
            if hasattr(self.scene_manager, 'format_tree'):
                logger.info(self.scene_manager.format_tree())
            else:
                logger.info(
                    f"Tree contains {len(self.scene_manager.root_objects)} root objects")

        # Force a complete refresh of the tree after a short delay
        # This ensures all items are properly rendered after structure changes
        QTimer.singleShot(50, self._force_refresh_tree)

    def _force_refresh_tree(self):
        """Force a complete refresh of the tree widget"""
        logger.debug("Forcing complete tree refresh")
        self._refresh_tree()

        # Ensure all items are visible and properly sized
        for i in range(self.topLevelItemCount()):
            top_item = self.topLevelItem(i)
            self._ensure_item_visible(top_item)

    def _ensure_item_visible(self, item):
        """Ensure an item and all its children are properly displayed"""
        # Update the item's size hint to match its widget
        widget = self.itemWidget(item, 0)
        if widget:
            item.setSizeHint(0, widget.sizeHint())

        # Process all child items
        for i in range(item.childCount()):
            self._ensure_item_visible(item.child(i))

    def _handle_reordering(self, uuid: str, parent_uuid: str, item: QTreeWidgetItem, parent_item: Optional[QTreeWidgetItem]):
        """Handle reordering of items within the same parent"""
        # Get the new index
        if parent_item:
            new_index = parent_item.indexOfChild(item)
        else:
            new_index = self.indexOfTopLevelItem(item)

        # Reorder in the scene manager
        obj = self.scene_manager.get_object_by_uuid(uuid)

        if parent_uuid:
            parent_obj = self.scene_manager.get_object_by_uuid(parent_uuid)

            # Remove and insert at new position
            parent_obj.children.remove(obj)
            parent_obj.children.insert(new_index, obj)

            logger.info(
                f"Reordering: Moved '{obj.name}' to position {new_index} under parent '{parent_obj.name}'")
        else:
            # Reordering top-level objects
            self.scene_manager.root_objects.remove(obj)
            self.scene_manager.root_objects.insert(new_index, obj)

            logger.info(
                f"Reordering: Moved '{obj.name}' to position {new_index} at root level")

    def _handle_scalar_field_detaching(self, field_uuid: str, mol_uuid: str):
        """Handle scalar field being detached from its molecule"""
        field_obj = self.scene_manager.get_object_by_uuid(field_uuid)
        mol_obj = self.scene_manager.get_object_by_uuid(mol_uuid)

        # Find and remove field from molecule's scalar_fields dictionary
        key_to_remove = None
        for key, sf in mol_obj.molecule.scalar_fields.items():
            if sf == field_obj.scalar_field:
                key_to_remove = key
                break

        if key_to_remove:
            print(
                f"Detaching scalar field '{key_to_remove}' from molecule '{mol_obj.name}'")
            del mol_obj.molecule.scalar_fields[key_to_remove]

    def _update_parent_child_relationship(self, uuid: str, old_parent_uuid: str, new_parent_uuid: str):
        """Update the parent-child relationship in the scene"""
        obj = self.scene_manager.get_object_by_uuid(uuid)

        # Remove from old parent
        if old_parent_uuid:
            old_parent = self.scene_manager.get_object_by_uuid(old_parent_uuid)
            if obj in old_parent.children:
                old_parent.children.remove(obj)
        else:
            if obj in self.scene_manager.root_objects:
                self.scene_manager.root_objects.remove(obj)

        # Add to new parent
        if new_parent_uuid:
            new_parent = self.scene_manager.get_object_by_uuid(new_parent_uuid)

            # Check if the new parent can accept this object
            if hasattr(obj, 'scalar_field') and not hasattr(new_parent, 'children'):
                QMessageBox.warning(None, "Invalid Move",
                                    f"Cannot add scalar field '{obj.name}' as child of non-molecule object '{new_parent.name}'")
                self._refresh_tree()  # Revert the tree view
                return

            new_parent.children.append(obj)
            obj.parent = new_parent
        else:
            self.scene_manager.root_objects.append(obj)
            obj.parent = None

        # Invalidate path cache
        obj._invalidate_path_cache()

    def _refresh_tree(self):
        """Rebuild the entire tree - works with both hierarchical and flat structures"""
        self.clear()
        self._uuid_items.clear()

        # Check if we have hierarchical structure or flat structure
        if hasattr(self.scene_manager, 'root_objects') and self.scene_manager.root_objects:
            # Hierarchical structure
            self._refresh_hierarchical_tree()
        else:
            # Fall back to flat structure
            self._refresh_flat_tree()

    def _refresh_hierarchical_tree(self):
        """Rebuild tree using hierarchical structure"""
        current_expanded_state = {}

        # Save expanded state before clearing
        if self.topLevelItemCount() > 0:
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                widget = self.itemWidget(item, 0)
                if hasattr(widget, 'uuid'):
                    current_expanded_state[widget.uuid] = item.isExpanded()
                    for j in range(item.childCount()):
                        child = item.child(j)
                        child_widget = self.itemWidget(child, 0)
                        if hasattr(child_widget, 'uuid'):
                            current_expanded_state[child_widget.uuid] = child.isExpanded(
                            )

        self.clear()
        self._uuid_items.clear()

        def add_object_to_tree(obj, parent=None):
            item = QTreeWidgetItem(parent or self)
            widget = ObjectTreeItem(obj.name,
                                    'molecule' if hasattr(obj, 'children') else 'scalar_field')

            # Store the uuid directly in the widget for easier access
            widget.uuid = obj.uuid

            # Set initial visibility
            widget._toggle_visibility(force_state=obj.visible)

            # Connect signals with explicit capture of UUID
            widget.visibility_changed.connect(
                lambda visible, uuid=obj.uuid: self._on_item_visibility_changed(uuid, visible))
            widget.settings_clicked.connect(
                lambda uuid=obj.uuid: self.settings_requested.emit(uuid))

            self.setItemWidget(item, 0, widget)
            self._uuid_items[obj.uuid] = item

            # Restore expanded state if it existed
            if obj.uuid in current_expanded_state:
                item.setExpanded(current_expanded_state[obj.uuid])
            else:
                item.setExpanded(True)  # Default to expanded

            if hasattr(obj, 'children'):
                for child in obj.children:
                    add_object_to_tree(child, item)

        for obj in self.scene_manager.root_objects:
            add_object_to_tree(obj)

    def _refresh_flat_tree(self):
        """Build a flat tree from the objects list"""
        for obj in self.scene_manager.objects:
            item = QTreeWidgetItem(self)

            # Determine object type
            obj_type = 'molecule' if hasattr(
                obj, 'molecule') else 'scalar_field'

            # Create widget for this item
            widget = ObjectTreeItem(obj.name, obj_type)

            # Set UUID if available, otherwise use name
            widget.uuid = getattr(obj, 'uuid', obj.name)

            # Set visibility
            widget._toggle_visibility(force_state=obj.visible)

            # Connect signals
            widget.visibility_changed.connect(
                lambda visible, name=obj.name: self._on_item_visibility_changed(name, visible))
            widget.settings_clicked.connect(
                lambda name=obj.name: self.settings_requested.emit(name))

            self.setItemWidget(item, 0, widget)
            self._uuid_items[widget.uuid] = item

    def _on_item_visibility_changed(self, identifier, visible):
        """Handle visibility changes triggered from the UI"""
        print(f"UI visibility toggle for {identifier}: {visible}")
        self.visibility_changed.emit(identifier, visible)

    def _on_visibility_changed(self, uuid: str, visible: bool):
        """Update item visibility state from scene manager events"""
        if uuid in self._uuid_items:
            item = self._uuid_items[uuid]
            widget = self.itemWidget(item, 0)

            # Only update if the state differs
            if widget.is_visible != visible:
                print(
                    f"Updating widget {widget.name} visibility from scene: {visible}")

                # Temporarily block signals to prevent loops
                blocked = widget.blockSignals(True)
                widget._toggle_visibility(force_state=visible)
                widget.blockSignals(blocked)

    def get_selected_uuid(self) -> Optional[str]:
        """Get UUID of selected item"""
        current = self.currentItem()
        if not current:
            return None

        for uuid, item in self._uuid_items.items():
            if item == current:
                return uuid
        return None
