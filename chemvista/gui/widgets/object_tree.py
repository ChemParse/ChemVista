from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from typing import Optional, Dict, List
from .item_widgets import TreeItemFactory
import logging
from ...scene_objects import SceneObject, ScalarFieldObject, MoleculeObject, TrajectoryObject
from ...tree_structure import TreeSignals

# Create logger
logger = logging.getLogger("chemvista.ui.tree")


class ObjectTreeWidget(QTreeWidget):
    # Use TreeSignals from tree_structure for these operations
    # emits UUID - keep this one as it's UI specific
    selection_changed = pyqtSignal(str)
    # Add the missing signals
    visibility_changed = pyqtSignal(str, bool)
    settings_requested = pyqtSignal(str)
    structure_changed = pyqtSignal()

    def __init__(self, scene_manager, parent=None):
        super().__init__(parent)
        self.scene_manager = scene_manager
        self.setHeaderHidden(True)
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.setExpandsOnDoubleClick(True)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)

        # Initialize the UUID to QTreeWidgetItem mapping
        self._uuid_items = {}
        self._processing_drop = False

        # Connect to scene manager signals
        if hasattr(self.scene_manager, '_signals'):
            signals = self.scene_manager._signals
            if hasattr(signals, 'node_added'):
                signals.node_added.connect(self._refresh_tree)
            if hasattr(signals, 'node_removed'):
                signals.node_removed.connect(self._refresh_tree)
            if hasattr(signals, 'node_changed'):
                signals.node_changed.connect(self._update_node_display)
            if hasattr(signals, 'visibility_changed'):
                signals.visibility_changed.connect(self._on_visibility_changed)
            if hasattr(signals, 'structure_changed'):
                signals.structure_changed.connect(self._force_refresh_tree)

        # Connect selection signals
        self.itemSelectionChanged.connect(self._on_selection_changed)

        # Initial tree build
        self._refresh_tree()

    def _on_selection_changed(self):
        """Handle selection changes"""
        selected_uuid = self.get_selected_uuid()
        if selected_uuid:
            self.selection_changed.emit(selected_uuid)

    def canDropMimeData(self, data, action, row, column, parent):
        """Check if drop operation is valid"""
        if not parent:
            return True  # Allow drops at root level

        # Get parent item's UUID
        parent_item = self.itemFromIndex(parent)
        if not parent_item:
            return True

        parent_widget = self.itemWidget(parent_item, 0)
        if not parent_widget or not hasattr(parent_widget, 'uuid'):
            return True

        parent_uuid = parent_widget.uuid
        parent_obj = self.scene_manager.get_object_by_uuid(parent_uuid)

        # If parent is a trajectory, only allow molecule drops
        if isinstance(parent_obj, TrajectoryObject):
            # Check if we're trying to drop scalar fields
            for item in self.selectedItems():
                widget = self.itemWidget(item, 0)
                if not widget or not hasattr(widget, 'uuid'):
                    continue

                item_uuid = widget.uuid
                source_obj = self.scene_manager.get_object_by_uuid(item_uuid)
                if isinstance(source_obj, ScalarFieldObject):
                    logger.warning(f"Cannot add scalar field to trajectory")
                    return False

        return True

    def dropEvent(self, event):
        """Handle drop event and update scene structure"""
        self._processing_drop = True

        # Validate drop operation first
        target_item = self.itemAt(event.pos())
        if target_item:
            target_widget = self.itemWidget(target_item, 0)
            if target_widget and hasattr(target_widget, 'uuid'):
                target_uuid = target_widget.uuid
                target_obj = self.scene_manager.get_object_by_uuid(target_uuid)

                # Check for invalid drops (e.g., scalar field into trajectory)
                if isinstance(target_obj, TrajectoryObject):
                    for item in self.selectedItems():
                        item_widget = self.itemWidget(item, 0)
                        if not item_widget or not hasattr(item_widget, 'uuid'):
                            continue
                        source_uuid = item_widget.uuid
                        source_obj = self.scene_manager.get_object_by_uuid(
                            source_uuid)
                        if isinstance(source_obj, ScalarFieldObject):
                            logger.warning(
                                f"Blocked attempt to drop scalar field into trajectory")
                            event.ignore()
                            self._processing_drop = False
                            return

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
            if (isinstance(field_obj, ScalarFieldObject) and
                isinstance(parent_obj, MoleculeObject) and
                    hasattr(parent_obj.molecule, 'scalar_fields')):

                # Check if this field is in the molecule's scalar_fields dictionary
                for key, sf in parent_obj.molecule.scalar_fields.items():
                    if sf == field_obj.scalar_field:
                        return True
        except Exception as e:
            logger.error(f"Error in _is_scalar_field_of_molecule: {e}")

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

        # Log the entire tree after changes
        try:
            self.scene_manager.log_tree_changes(
                "Tree structure updated after drag-and-drop")
        except AttributeError:
            logger.info("Tree structure updated after drag-and-drop")

        # Emit structure changed signal if available
        if hasattr(self.scene_manager, '_signals') and hasattr(self.scene_manager._signals, 'structure_changed'):
            self.scene_manager._signals.structure_changed.emit()
        else:
            # Force a refresh if no signal available
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
            if obj in parent_obj.children:
                parent_obj.children.remove(obj)
                parent_obj.children.insert(new_index, obj)

                logger.info(
                    f"Reordering: Moved '{obj.name}' to position {new_index} under parent '{parent_obj.name}'")
        else:
            # Reordering top-level objects
            if hasattr(self.scene_manager, 'root') and obj in self.scene_manager.root.children:
                self.scene_manager.root.children.remove(obj)
                self.scene_manager.root.children.insert(new_index, obj)
                logger.info(
                    f"Reordering: Moved '{obj.name}' to position {new_index} at root level")

    def _handle_scalar_field_detaching(self, field_uuid: str, mol_uuid: str):
        """Handle scalar field being detached from its molecule"""
        field_obj = self.scene_manager.get_object_by_uuid(field_uuid)
        mol_obj = self.scene_manager.get_object_by_uuid(mol_uuid)

        if not isinstance(field_obj, ScalarFieldObject) or not isinstance(mol_obj, MoleculeObject):
            return

        # Find and remove field from molecule's scalar_fields dictionary
        key_to_remove = None
        for key, sf in mol_obj.molecule.scalar_fields.items():
            if sf == field_obj.scalar_field:
                key_to_remove = key
                break

        if key_to_remove:
            logger.info(
                f"Detaching scalar field '{key_to_remove}' from molecule '{mol_obj.name}'")
            del mol_obj.molecule.scalar_fields[key_to_remove]

    def _update_parent_child_relationship(self, uuid: str, old_parent_uuid: str, new_parent_uuid: str):
        """Update the parent-child relationship in the scene"""
        obj = self.scene_manager.get_object_by_uuid(uuid)

        # Move the node using the scene manager's move method
        if hasattr(self.scene_manager, 'root') and hasattr(self.scene_manager.root, 'move'):
            new_parent = self.scene_manager.root if new_parent_uuid is None else self.scene_manager.get_object_by_uuid(
                new_parent_uuid)
            self.scene_manager.root.move(obj, new_parent)
            return

        # Manual fallback if move method not available
        # Remove from old parent
        if old_parent_uuid:
            old_parent = self.scene_manager.get_object_by_uuid(old_parent_uuid)
            if obj in old_parent.children:
                old_parent.children.remove(obj)
                obj.parent = None
        elif hasattr(self.scene_manager, 'root') and obj in self.scene_manager.root.children:
            self.scene_manager.root.children.remove(obj)
            obj.parent = None

        # Add to new parent
        if new_parent_uuid:
            new_parent = self.scene_manager.get_object_by_uuid(new_parent_uuid)

            # Check if the new parent can accept this object
            if isinstance(obj, ScalarFieldObject) and not hasattr(new_parent, 'children'):
                QMessageBox.warning(None, "Invalid Move",
                                    f"Cannot add scalar field '{obj.name}' as child of non-container object")
                self._refresh_tree()  # Revert the tree view
                return

            if hasattr(new_parent, 'children'):
                new_parent.children.append(obj)
                obj.parent = new_parent
        elif hasattr(self.scene_manager, 'root'):
            self.scene_manager.root.children.append(obj)
            obj.parent = self.scene_manager.root

    def _refresh_tree(self):
        """Rebuild the entire tree"""
        self.clear()
        self._uuid_items.clear()

        if not self.scene_manager:
            return

        # Build tree from the root node
        if hasattr(self.scene_manager, 'root'):
            root = self.scene_manager.root
            # Add all root children
            for obj in root.children:
                self._add_node(obj)

    def _add_node(self, node, parent_item=None):
        """Add a node to the tree"""
        # Create tree widget item
        tree_item = QTreeWidgetItem()

        # Add to parent or root
        if parent_item:
            parent_item.addChild(tree_item)
        else:
            self.addTopLevelItem(tree_item)

        # Create the widget for this item using the factory
        item_widget = TreeItemFactory.create_item_for_object(node, self)
        item_widget.uuid = node.uuid
        item_widget._toggle_visibility(force_state=node.visible)

        # Connect signals
        item_widget.visibility_changed.connect(
            lambda visible, uuid=node.uuid: self._on_item_visibility_changed(uuid, visible))
        item_widget.settings_clicked.connect(
            lambda uuid=node.uuid: self._on_settings_clicked(uuid))

        # Set the widget to the tree item
        self.setItemWidget(tree_item, 0, item_widget)
        self._uuid_items[node.uuid] = tree_item

        # Set expanded by default
        tree_item.setExpanded(True)

        # Recursively add children
        if hasattr(node, 'children'):
            for child in node.children:
                self._add_node(child, tree_item)

    def _update_node_display(self, uuid):
        """Update a single node's display without rebuilding entire tree"""
        if uuid in self._uuid_items:
            obj = self.scene_manager.get_object_by_uuid(uuid)
            if not obj:
                return

            item = self._uuid_items[uuid]
            widget = self.itemWidget(item, 0)

            # Update name and visibility
            if widget:
                if widget.name != obj.name:
                    widget.name = obj.name
                    widget.name_label.setText(obj.name)

                if widget.is_visible != obj.visible:
                    widget._toggle_visibility(force_state=obj.visible)

    def _on_item_visibility_changed(self, identifier, visible):
        """Handle visibility changes triggered from the UI"""
        logger.debug(f"UI visibility toggle for {identifier}: {visible}")
        if hasattr(self.scene_manager, '_signals') and hasattr(self.scene_manager._signals, 'visibility_changed'):
            self.scene_manager._signals.visibility_changed.emit(
                identifier, visible)
        else:
            # Fallback if signals not available
            self.scene_manager.set_visibility(identifier, visible)

    def _on_visibility_changed(self, uuid: str, visible: bool):
        """Update item visibility state from scene manager events"""
        if uuid in self._uuid_items:
            item = self._uuid_items[uuid]
            widget = self.itemWidget(item, 0)

            # Only update if the state differs
            if widget and widget.is_visible != visible:
                logger.debug(
                    f"Updating widget {widget.name} visibility from scene: {visible}")

                # Temporarily block signals to prevent loops
                blocked = widget.blockSignals(True)
                widget._toggle_visibility(force_state=visible)
                widget.blockSignals(blocked)

    def _on_settings_clicked(self, uuid):
        """Handle settings button click"""
        # Look for a node_changed signal to emit
        if hasattr(self.scene_manager, '_signals') and hasattr(self.scene_manager._signals, 'node_changed'):
            self.scene_manager._signals.node_changed.emit(uuid)
        else:
            # Fallback to old behavior if needed
            logger.debug(f"Settings requested for {uuid}")

    def get_selected_uuid(self) -> Optional[str]:
        """Get UUID of selected item"""
        current = self.currentItem()
        if not current:
            return None

        widget = self.itemWidget(current, 0)
        if widget and hasattr(widget, 'uuid'):
            return widget.uuid

        return None
