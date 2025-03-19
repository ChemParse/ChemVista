from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QRect, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor
from typing import Optional, Dict, List, Union, Tuple
from .item_widgets import TreeItemFactory, ObjectTreeItem
import logging
from ....scene_objects import SceneObject, ScalarFieldObject, MoleculeObject, TrajectoryObject
from ....tree_structure import TreeSignals, TreeNode
from PyQt5.QtCore import QObject

# Create logger
logger = logging.getLogger("chemvista.ui.widgets.object_tree_widget")


class TreeWidgetSignals(QObject):
    selection_changed = pyqtSignal(str)
    structure_updated = pyqtSignal()
    settings_requested = pyqtSignal(str)
    visibility_changed = pyqtSignal(str, bool)


class ObjectTreeWidget(QTreeWidget):

    def __init__(self, scene_manager, parent=None, tree_widget_signals: Optional[TreeWidgetSignals] = None, tree_signals: Optional[TreeSignals] = None):
        super().__init__(parent)
        self.scene_manager = scene_manager
        self.root: TreeNode = scene_manager.root
        # Map UUIDs to tree items
        self._item_map: Dict[str, QTreeWidgetItem] = {}

        # Track drop position
        self._drop_indicator_position = None
        self._drop_target_item = None
        self._drawing_drop_indicator = False
        self._drop_rect = QRect()

        # Custom colors for drop indicators
        self._drop_indicator_color = QColor(50, 150, 255)  # Bright blue

        # Disable Qt's default drop indicator since we're drawing our own
        self.setDropIndicatorShown(False)

        self.setHeaderHidden(True)
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.setExpandsOnDoubleClick(True)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.MoveAction)

        # Connect selection signals
        self.itemSelectionChanged.connect(self._on_selection_changed)

        # Initialize signals objects
        self._widget_signals: TreeWidgetSignals = None
        self.widget_signals = tree_widget_signals
        self._tree_signals: TreeSignals = None
        self.tree_signals = tree_signals

        # Connect drag & drop signals
        self.itemMoved = None  # Will be set when item is being dragged
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.customContextMenuRequested.connect(self._show_context_menu)

        # Initial tree build
        self._refresh_tree()

        # Flag to manage updates - replaces the previous multiple flags
        self._updates_enabled = True

        logger.debug("Initializing ObjectTreeWidget")

    @property
    def widget_signals(self):
        """Get the widget signals object"""
        return self._widget_signals

    @widget_signals.setter
    def widget_signals(self, value):
        """Set the widget signals object"""
        self._widget_signals = value
        logger.debug("Widget signals set")

    @property
    def tree_signals(self):
        """Get the tree signals object"""
        return self._tree_signals

    @tree_signals.setter
    def tree_signals(self, value):
        """Set the tree signals object"""

        # Set and connect new signals
        self._tree_signals = value

        self._tree_signals.visibility_changed.connect(
            self._on_tree_structure_changed)
        self._tree_signals.tree_structure_changed.connect(
            self._on_tree_structure_changed)

        logger.debug("Tree signals connected")

    def enable_updates(self):
        """Enable tree structure updates"""
        logger.debug("Updates enabled")
        self._updates_enabled = True

    def disable_updates(self):
        """Disable tree structure updates"""
        logger.debug("Updates disabled")
        self._updates_enabled = False

    def update_tree(self):
        """Manually trigger a tree update"""
        logger.debug("Manual tree update triggered")
        self._refresh_tree()
        self._widget_signals.structure_updated.emit()

    def _refresh_tree(self):
        """Build or refresh the entire tree from the root node"""
        logger.debug("Starting tree refresh")
        logger.debug(self.root.format_tree())

        self.clear()
        self._item_map.clear()

        # Skip the actual root node, start with its children
        for child in self.root.children:
            self._add_node_to_tree(child)

        # Expand the first level by default
        self.expandToDepth(0)

        logger.debug(f"Tree refreshed with {len(self._item_map)} items")
        logger.debug(self.root.format_tree())

    def _add_node_to_tree(self, node: TreeNode, parent_item: Optional[QTreeWidgetItem] = None) -> QTreeWidgetItem:
        """Recursively add a node and its children to the tree"""
        # Create tree item
        if parent_item is None:
            item = QTreeWidgetItem(self)
            logger.debug(
                f"Adding top-level item: {node.name} ({node.uuid[:8]})")
        else:
            item = QTreeWidgetItem(parent_item)
            logger.debug(
                f"Adding child item: {node.name} ({node.uuid[:8]}) to parent {parent_item.text(0)}")

        # Store item in the map for quick lookup by UUID
        self._item_map[node.uuid] = item

        # Set the display text
        item.setText(0, node.name)
        item.setData(0, Qt.UserRole, node.uuid)

        # Create and set the item widget with proper type
        widget = TreeItemFactory.create_item_for_object(node, self)
        if widget:
            # Set the item widget
            self.setItemWidget(item, 0, widget)

        # Recursively add children
        for child in node.children:
            self._add_node_to_tree(child, item)

        return item

    def _on_selection_changed(self):
        """Handle selection changes in the tree"""
        selected_items = self.selectedItems()
        if selected_items:
            # Get the UUID from the selected item
            uuid = selected_items[0].data(0, Qt.UserRole)
            if uuid:
                self._widget_signals.selection_changed.emit(uuid)
                logger.debug(
                    f"Selection changed to {selected_items[0].text(0)} ({uuid[:8]})")
        else:
            logger.debug("Selection cleared")

    def _on_tree_structure_changed(self):
        """Handle tree structure changed signal from the tree model"""
        # Only process updates when enabled
        if not self._updates_enabled:
            logger.debug(
                "Tree structure change notification received while updates disabled - ignoring")
            return

        # Update the tree
        logger.debug("Tree structure changed notification received")
        logger.debug(self.root.format_tree())
        self._refresh_tree()
        self._widget_signals.structure_updated.emit()
        logger.debug("Structure update signal emitted")

    def _check_tree_consistency(self):
        """Verify tree UI matches the model structure and fix if needed"""
        # Compare current tree UI with the model structure
        # If they don't match, do another refresh

        # For now, just do a full refresh for simplicity
        # This could be optimized later
        if not self._refreshing_tree:
            logger.debug("Checking tree consistency")
            self._refresh_tree()

    def _get_drop_indicator_position(self, pos, item) -> str:
        """
        Determine more precise drop position relative to the item
        Returns: 'above', 'below', or None (meaning on the item)
        """
        if not item:
            return None  # On root if no item

        rect = self.visualItemRect(item)

        # Use more precise margins for better control
        # Max 6 pixels or 1/4 of item height
        upper_margin = min(rect.height() // 4, 6)
        # Max 6 pixels or 1/4 of item height
        lower_margin = min(rect.height() // 4, 6)

        if pos.y() < rect.top() + upper_margin:
            position = 'above'
        elif pos.y() > rect.bottom() - lower_margin:
            position = 'below'
        else:
            position = None

        return position

    def _get_relative_item(self, event) -> Tuple[QTreeWidgetItem, str]:
        """
        Determine the relative item and position based on the event
        Returns: (item, position) where position is 'above', 'below', or None
        """
        # Get the item at the event position
        item = self.itemAt(event.pos())

        # If there's no item, return (None, None)
        if not item:
            return None, None

        # Determine the position relative to the item
        position = self._get_drop_indicator_position(event.pos(), item)

        return item, position

    def _get_absolute_item_position(self, item_to_move, relative_item, position) -> Tuple[TreeNode, Union[int, None]]:
        """
        Determine the absolute position for a drop operation
        Returns: (target_node, position) where position is either None or an integer index
        """
        # Get the TreeNode corresponding to the relative item
        if not relative_item:
            # If there's no relative item, add to root
            return self.root, None

        relative_uuid = relative_item.data(0, Qt.UserRole)
        relative_node = self.root.get_object_by_uuid(relative_uuid)

        if not relative_node:
            logger.debug(
                f"Relative node not found for UUID {relative_uuid}, using root")
            return self.root, None

        # Get the TreeNode for the item being moved
        moving_uuid = item_to_move.data(0, Qt.UserRole)
        moving_node = self.root.get_object_by_uuid(moving_uuid)

        if not moving_node:
            logger.debug(f"Moving node not found for UUID {moving_uuid}")
            return None, None

        # Handle positioning based on indicator
        if position is None:
            # We're adding as a child of the relative item
            logger.debug(f"Drop position: on {relative_node.name}")
            return relative_node, None
        elif position in ('above', 'below'):
            # We're adding as a sibling above or below
            # The target node is the parent of the relative item
            parent_node = relative_node.parent if relative_node.parent else self.root

            # Calculate the index position in parent's children list
            if parent_node:
                index = parent_node.children.index(relative_node)
                if position == 'below':
                    index += 1  # Insert after the target

                # If source and target have the same parent, and we're moving below
                # an item that is further down in the list, we need to adjust the index
                if (moving_node.parent == parent_node and
                        parent_node.children.index(moving_node) < index):
                    index -= 1  # Adjust for the removal of the source node
                    logger.debug(
                        f"Adjusted index for same-parent move: {index}")

                logger.debug(
                    f"Drop position: {position} {relative_node.name} (index {index} in {parent_node.name})")
                return parent_node, index
            else:
                # Fallback if parent_node is somehow None
                logger.debug(
                    f"Parent node is None for {relative_node.name}, using root")
                return self.root, None
        else:
            # Fallback for unexpected position value
            logger.debug(
                f"Unknown drop position: {position}, defaulting to on-item (None)")
            return relative_node, None

    def dragMoveEvent(self, event):
        """Override to track drop position indicators during drag operations"""
        super().dragMoveEvent(event)

        # Use internal helper to get drop target and position
        target_item, drop_position = self._get_relative_item(event)

        # Handle drops over empty area (no target item)
        if not target_item:
            # When dropping over empty area, set position to 'root'
            logger.debug("Drag indicator: over empty area (will add to root)")
            self._drawing_drop_indicator = False
            self._drop_indicator_position = 'root'
            self._drop_target_item = None
            self.viewport().update()
            return

        # Don't log every mouse movement during drag to avoid log spam
        # Only log when position or target changes
        if (target_item != self._drop_target_item or
                drop_position != self._drop_indicator_position):
            logger.debug(
                f"Drag indicator: {drop_position} {target_item.text(0)}")

        # Store current drop position and target for use in dropEvent
        self._drop_indicator_position = drop_position
        self._drop_target_item = target_item

        # Calculate rectangle for custom drop indicator
        rect = self.visualItemRect(target_item)
        self._drop_rect = rect

        if drop_position == 'above':
            self._drop_rect.setHeight(3)
        elif drop_position == 'below':
            self._drop_rect.setTop(rect.bottom() - 2)
            self._drop_rect.setHeight(3)
        elif drop_position is None:
            # Make the entire item background highlight
            pass

        # Force a repaint to show the drop indicator
        self._drawing_drop_indicator = True
        self.viewport().update()

    def dropEvent(self, event):
        """Handle drop events for drag and drop operations"""
        logger.debug("Drop event started")

        # Get the item being dropped
        items = self.selectedItems()
        if not items:
            logger.debug("No items selected for drop")
            return

        source_item = items[0]
        source_uuid = source_item.data(0, Qt.UserRole)
        source_node = self.root.get_object_by_uuid(source_uuid)

        if not source_node:
            logger.warning(
                f"Source node not found for drop event: {source_uuid}")
            return

        # Get the relative item and position using internal helper
        relative_item, position = self._get_relative_item(event)

        # Get target node and position for the move operation
        target_node, position = self._get_absolute_item_position(
            source_item, relative_item, position)

        # Disable updates for the duration of the move operation
        self.disable_updates()

        # Perform the move operation
        success = False

        try:
            if target_node:
                # Perform the move operation
                if position is None:
                    # For None, we're adding as a child, so omit position parameter
                    logger.debug(
                        f"Moving {source_node.name} as child of {target_node.name}")
                    success, msg = self.root.move(source_node, target_node)
                else:
                    # For numerical positions, pass the position as-is
                    logger.debug(
                        f"Moving {source_node.name} to position {position} in {target_node.name}")
                    success, msg = self.root.move(
                        source_node, target_node, position)

                if success:
                    logger.debug(
                        f"Move successful: {source_node.name} to {target_node.name}")
                    # Accept the event
                    event.accept()
                else:
                    logger.warning(f"Move failed: {msg}")
                    QMessageBox.warning(self, "Move Failed", msg)
                    # Ignore the event
                    event.ignore()
            else:
                # If we can't process this drop, let Qt know
                logger.debug(
                    "Invalid move operation - source has no parent or target is invalid")
                event.ignore()
        finally:
            # Always reset drop state
            self._reset_drop_state()

            # Re-enable updates
            self.enable_updates()

            # Now manually trigger a tree update if the move was successful
            if success:
                logger.debug(
                    "Triggering manual tree update after successful move")
                self.update_tree()

            logger.debug("Drop event completed")
            logger.debug(self.root.format_tree())

    def _reset_drop_state(self):
        """Reset all drop-related state variables"""
        # Reset drop indicator state
        self._drawing_drop_indicator = False
        self._drop_indicator_position = None
        self._drop_target_item = None
        self.viewport().update()
        logger.debug("Drop state reset")

    def dragLeaveEvent(self, event):
        """Handle when drag leaves the widget area"""
        super().dragLeaveEvent(event)
        logger.debug("Drag left widget area")
        self._reset_drop_state()

    def paintEvent(self, event):
        """Override to draw custom drop indicator"""
        super().paintEvent(event)

        # Draw custom drop indicator if we're dragging
        if self._drawing_drop_indicator and self._drop_target_item and self._drop_indicator_position is not None:
            painter = QPainter(self.viewport())

            # Set up the painter
            pen = QPen(self._drop_indicator_color)
            pen.setWidth(3)
            painter.setPen(pen)

            # Different drawing based on drop position
            if self._drop_indicator_position == 'above':
                # Draw a line above the item
                painter.drawLine(
                    QPoint(self._drop_rect.left(), self._drop_rect.top()),
                    QPoint(self._drop_rect.right(), self._drop_rect.top())
                )
                # Draw small vertical lines at the ends for better visibility
                painter.drawLine(
                    QPoint(self._drop_rect.left(), self._drop_rect.top() - 3),
                    QPoint(self._drop_rect.left(), self._drop_rect.top() + 3)
                )
                painter.drawLine(
                    QPoint(self._drop_rect.right(), self._drop_rect.top() - 3),
                    QPoint(self._drop_rect.right(), self._drop_rect.top() + 3)
                )

            elif self._drop_indicator_position == 'below':
                # Draw a line below the item
                bottom = self._drop_rect.top() + 2
                painter.drawLine(
                    QPoint(self._drop_rect.left(), bottom),
                    QPoint(self._drop_rect.right(), bottom)
                )
                # Draw small vertical lines at the ends for better visibility
                painter.drawLine(
                    QPoint(self._drop_rect.left(), bottom - 3),
                    QPoint(self._drop_rect.left(), bottom + 3)
                )
                painter.drawLine(
                    QPoint(self._drop_rect.right(), bottom - 3),
                    QPoint(self._drop_rect.right(), bottom + 3)
                )

            elif self._drop_indicator_position is None:
                # Draw a rectangle around the item to indicate "adding as child"
                pen.setStyle(Qt.DashLine)
                painter.setPen(pen)
                painter.drawRect(self._drop_rect)

                # Draw a "+" icon to the right to indicate adding as child
                icon_size = min(16, self._drop_rect.height() - 4)
                icon_rect = QRect(
                    self._drop_rect.right() - icon_size - 5,
                    self._drop_rect.top() + (self._drop_rect.height() - icon_size) // 2,
                    icon_size,
                    icon_size
                )

                # Draw + symbol
                painter.drawLine(
                    QPoint(icon_rect.left() + icon_rect.width() //
                           2, icon_rect.top() + 2),
                    QPoint(icon_rect.left() + icon_rect.width() //
                           2, icon_rect.bottom() - 2)
                )
                painter.drawLine(
                    QPoint(icon_rect.left() + 2, icon_rect.top() +
                           icon_rect.height() // 2),
                    QPoint(icon_rect.right() - 2, icon_rect.top() +
                           icon_rect.height() // 2)
                )

    def edit_item_text(self, item):
        """Enter edit mode for the item text"""
        logger.debug(f"Editing item text: {item.text(0)}")
        self.editItem(item, 0)

    def _delete_item(self, uuid: str):
        """Delete an item from the tree"""
        node = self.root.get_object_by_uuid(uuid)
        if not node or not node.parent:
            logger.debug(
                f"Cannot delete node with UUID {uuid} - node not found or is root")
            return

        logger.debug(f"Requesting confirmation to delete {node.name}")
        reply = QMessageBox.question(
            self, 'Confirm Delete',
            f"Are you sure you want to delete '{node.name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # The node's parent will handle proper removal
            parent = node.parent
            logger.debug(
                f"Deleting node {node.name} from parent {parent.name}")
            parent.remove_child(node)
            logger.debug(f"Node {node.name} deleted")
        else:
            logger.debug(f"Deletion of {node.name} cancelled by user")
