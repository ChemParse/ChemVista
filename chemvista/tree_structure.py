import uuid
from typing import Optional, Dict, List, Iterator, Tuple, Any, TypeVar, Generic, Union
from dataclasses import dataclass, field
from PyQt5.QtCore import QObject, pyqtSignal
import logging
from .renderer.render_settings import RenderSettings

# Create logger
logger = logging.getLogger("chemvista.tree")

T = TypeVar('T')  # Generic type for node data


@dataclass
class NodePath:
    """Represents a path to a node in the tree"""
    parts: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return '/' + '/'.join(self.parts)

    @classmethod
    def from_string(cls, path_str: str) -> 'NodePath':
        return cls(path_str.strip('/').split('/'))

    def child(self, name: str) -> 'NodePath':
        """Return a new path with the given name appended"""
        return NodePath(self.parts + [name])

    def parent(self) -> Optional['NodePath']:
        """Return the parent path or None if this is the root"""
        if not self.parts:
            return None
        return NodePath(self.parts[:-1])

    @property
    def name(self) -> str:
        """Get the last part of the path"""
        if not self.parts:
            return ""
        return self.parts[-1]


class TreeSignals(QObject):
    """Signals for tree events to avoid multiple inheritance issues"""
    node_added = pyqtSignal(str)  # emits node UUID
    node_removed = pyqtSignal(str)  # emits node UUID
    node_changed = pyqtSignal(str)  # emits node UUID
    # emits node UUID and visibility state
    visibility_changed = pyqtSignal(str, bool)

    render_changed = pyqtSignal(str)  # emits when render settings change

    # emits when tree structure changes (moves, etc)
    tree_structure_changed = pyqtSignal()


class TreeNode(Generic[T]):
    """Base class for all tree nodes with efficient operations"""

    def __init__(self, name: str, data: Optional[T] = None, node_type: str = "generic",
                 parent: Optional['TreeNode'] = None, visible: bool = True, signals=None):
        self._name = name  # Use private attribute for name
        self.data = data
        self.node_type = node_type
        self.uuid = str(uuid.uuid4())
        self._visible = visible
        self._parent = parent
        self._children: Dict[str, 'TreeNode'] = {}
        self._path_cache: Optional[NodePath] = None
        self._signals = None
        self.signals = signals

    @property
    def visible(self) -> bool:
        """Get visibility state"""
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        """Set visibility state"""
        self._visible = value
        if self.signals:
            self._signals.visibility_changed.emit(self.uuid, value)
            self._signals.render_changed.emit(self.uuid)

    @property
    def signals(self):
        """Get the signals object"""
        return self._signals

    @signals.setter
    def signals(self, value):
        """Set the signals object"""
        self._signals = value

    @property
    def name(self) -> str:
        """Get the node name"""
        return self._name

    @name.setter
    def name(self, value: str):
        """Set node name and invalidate path cache"""
        self._name = value
        self._invalidate_path_cache()

    @property
    def parent(self) -> Optional['TreeNode']:
        """Get the parent node"""
        return self._parent

    @parent.setter
    def parent(self, new_parent: Optional['TreeNode']):
        """Set the parent node with proper cleanup"""
        # Remove from old parent if exists
        if self._parent and self in self._parent._children.values():
            self._parent._remove_child_internal(self)

        # Set new parent
        self._parent = new_parent

        # Add to new parent's children if it exists
        if new_parent:
            new_parent._add_child_internal(self)

        # Invalidate path cache
        self._invalidate_path_cache()

        # Call hook for subclasses to handle parent change
        self._on_parent_changed()

    def _on_parent_changed(self):
        """Hook for subclasses to handle parent change"""
        pass

    @property
    def children(self) -> List['TreeNode']:
        """Get list of first level children"""
        return list(self._children.values())

    @property
    def path(self) -> NodePath:
        """Get path to this node"""
        if self._path_cache is None:
            parts = []
            current = self
            while current is not None:
                parts.append(current.name)
                current = current._parent
            self._path_cache = NodePath(list(reversed(parts)))
        return self._path_cache

    def _invalidate_path_cache(self):
        """Invalidate path cache for this node and all children"""
        self._path_cache = None
        for child in self._children.values():
            child._invalidate_path_cache()

    def _can_add_child(self, child: 'TreeNode') -> Tuple[bool, str]:
        """Check if a child can be added - subclasses can override to restrict by type"""
        return True, ""

    def add_child(self, child: 'TreeNode', position: Optional[int] = None, send_signals: bool = True) -> Tuple[bool, str]:
        """
        Add a child to this node with optional position, returns success and message

        Args:
            child: The child node to add
            position: Optional position index (None means append to end)
            send_signals: Whether to emit signals after the operation (default: True)

        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.debug(f"Adding child {child.name} to {self.name}")

        # Check if child can be added (allow subclasses to restrict by type)
        can_add, msg = self._can_add_child(child)
        if not can_add:
            return False, msg

        # Basic add if position not specified
        if position is None:
            # Add the child directly
            if child.uuid in self._children:
                return False, "Child already exists in this parent"

            child._parent = self
            self._children[child.uuid] = child
            child._invalidate_path_cache()

            # Emit signals if requested
            if send_signals and self._signals:
                self._signals.node_added.emit(child.uuid)
                self._signals.tree_structure_changed.emit()

            return True, "Node added"

        # Handle positioned add
        children_list = list(self._children.values())
        if 0 <= position <= len(children_list):
            # First check if child is already in children
            if child.uuid in self._children:
                return False, "Child already exists in this parent"

            # Add the child
            child._parent = self
            self._children[child.uuid] = child
            child._invalidate_path_cache()

            # Then reorder by rebuilding the list and dictionary
            children_list = list(self._children.values())
            # Remove and reinsert at the right position
            children_list.remove(child)
            children_list.insert(position, child)

            # Rebuild dictionary to maintain order
            self._children = {node.uuid: node for node in children_list}

            # Emit signals if requested
            if send_signals and self._signals:
                self._signals.node_added.emit(child.uuid)
                self._signals.tree_structure_changed.emit()

            return True, f"Node added at position {position}"

        return False, f"Invalid position {position}"

    def remove_child(self, child: Union['TreeNode', str], send_signals: bool = True) -> Optional['TreeNode']:
        """
        Remove a child from this node, returns the removed child or None if not found

        Args:
            child: The child node or its UUID to remove
            send_signals: Whether to emit signals after the operation (default: True)

        Returns:
            The removed TreeNode or None if not found
        """
        # Handle string UUID as argument
        if isinstance(child, str):
            child_obj = self._children.get(child)
            if not child_obj:
                return None
            child = child_obj

        # Check if the child exists in our children dictionary
        if child.uuid not in self._children:
            return None

        # Remove from children
        del self._children[child.uuid]

        # Remove parent reference
        child._parent = None

        # Emit signals if requested and signals object exists
        if send_signals and self._signals and hasattr(child, 'uuid'):
            self._signals.node_removed.emit(child.uuid)
            self._signals.tree_structure_changed.emit()

        return child

    def move(self, child_obj: Union['TreeNode', str], new_parent: Union['TreeNode', 'str'],
             position: Optional[int] = None) -> Tuple[bool, str]:
        """Move a child to a new parent with optional position, returns success and message"""
        # Handle string UUID as argument
        if isinstance(child_obj, str):
            child_obj = self.get_object_by_uuid(child_obj)
            if not child_obj:
                logger.warning(f"Child node {child_obj} not found")
                return False, "Child node not found"
        current_parent = child_obj.parent

        if isinstance(new_parent, str):
            new_parent = self.get_object_by_uuid(new_parent)
            if not new_parent:
                logger.warning(f"Parent node {new_parent} not found")
                return False, "Parent node not found"

        logger.debug(
            f"Moving node {child_obj.name} ({child_obj.uuid}) to {new_parent.name} ({new_parent.uuid}) with position {position}")

        if new_parent == current_parent:
            logger.debug(
                f"Node {child_obj.name} already belongs to target parent {new_parent.name}, reordering instead of moving")
            return new_parent.reorder_child(child_obj, position)

        # Check if new parent can accept this child
        can_add, msg = new_parent._can_add_child(child_obj)
        if not can_add:
            logger.warning(
                f"Cannot move node to target: {msg}")
            return False, f"Cannot move to target: {msg}"

        # Remove from current parent without sending signals
        if current_parent:
            current_parent.remove_child(child_obj, send_signals=False)

        # Add to new parent
        success, add_msg = new_parent.add_child(
            child_obj, position, send_signals=True)

        if success:
            logger.debug(
                f"Node {child_obj.name} moved successfully to {new_parent.name}")
            logger.debug(f'{child_obj.parent = }')
            logger.debug(
                f'New parent children = {[child.name for child in new_parent.children]}')
            logger.debug(
                f'Old parent children = {[child.name for child in current_parent.children]}' if current_parent else 'No old parent')
            logger.debug(self.format_tree())
            return success, f"Node moved successfully to {new_parent.name}"

        else:
            logger.warning(
                f"Failed to move node: {add_msg}")
            return success, f"Failed to move node: {add_msg}"

    def set_visibility(self, uuid_or_node: Union[str, 'TreeNode'], visible: bool) -> bool:
        """Set visibility of a node by UUID or reference"""
        # Handle string UUID
        if isinstance(uuid_or_node, str):
            node = self.get_object_by_uuid(uuid_or_node)
            if node is None:
                return False
        else:
            node = uuid_or_node

        # Set visibility
        if node.visible != visible:
            node.visible = visible
            # Emit signal if exists
            if self._signals:
                self._signals.visibility_changed.emit(node.uuid, visible)
                self._signals.render_changed.emit(node.uuid)
            return True
        return False

    def update_settings(self, settings: RenderSettings) -> None:
        """Update render settings for an object"""
        logger.debug(
            f"Updating settings for {self.name} with settings: {settings}")
        if hasattr(self, 'render_settings'):
            if settings != self.render_settings:
                logger.debug(
                    f"Settings changed")
                self.render_settings = settings
                if self._signals:
                    logger.debug(
                        f"Emitting render changed signal for {self.name}")
                    self._signals.render_changed.emit(self.uuid)
            else:
                logger.debug(
                    f"Settings unchanged for {self.name} as the settings are the same")
        else:
            logger.warning(
                f"Cannot update settings for {self.name}: no render settings")

    def find_by_path(self, path: Union[str, NodePath]) -> Optional['TreeNode']:
        """Find a node by its path"""
        if isinstance(path, str):
            path = NodePath.from_string(path)

        # Root path or empty path returns self
        if not path.parts or (len(path.parts) == 1 and path.parts[0] == self.name):
            return self

        # Validate the root part matches this node
        if path.parts[0] != self.name:
            return None

        # Navigate down the tree
        current = self
        for part in path.parts[1:]:
            found = False
            for child in current.children:
                if child.name == part:
                    current = child
                    found = True
                    break
            if not found:
                return None

        return current

    def __contains__(self, item: Union[str, 'TreeNode', NodePath]) -> bool:
        """
        Check if a node exists in the tree. Supports:
        - Node objects directly
        - UUID strings
        - NodePath objects or path strings

        This allows for syntax like: `if node in tree` or `if uuid in tree`
        """
        # Case 1: Check for TreeNode object directly
        if isinstance(item, TreeNode):
            # Check if this is the item
            if item == self:
                return True
            # Check if it's a direct child
            if item.uuid in self._children:
                return True
            # Recursively check children
            return any(item in child for child in self.children)

        # Case 2: Check for UUID string
        elif isinstance(item, str):
            # Check if this node has the UUID
            if self.uuid == item:
                return True
            # Check if it's a direct child
            if item in self._children:
                return True
            # Recursively check children
            return any(item in child for child in self.children)

        # Case 3: Check for NodePath
        elif isinstance(item, (NodePath, str)):
            path = item if isinstance(
                item, NodePath) else NodePath.from_string(item)
            return self.find_by_path(path) is not None

        # Not found or unsupported type
        return False

    def get_object_by_uuid(self, uuid_str: str) -> Optional['TreeNode']:
        """
        Find a node by its UUID in the tree

        Args:
            uuid_str: UUID string to search for

        Returns:
            The node with the matching UUID or None if not found
        """
        # Check if this node has the UUID
        if self.uuid == uuid_str:
            return self

        # Check direct children first for performance
        if uuid_str in self._children:
            return self._children[uuid_str]

        # Recursive search in children
        for child in self.children:
            result = child.get_object_by_uuid(uuid_str)
            if result is not None:
                return result

        # Not found
        return None

    def get_object_by_name(self, name: str) -> Optional['TreeNode']:
        """
        Find an object by name (first match)

        Args:
            name: Name to search for

        Returns:
            First node with matching name or None if not found
        """
        # Check self first
        if self.name == name:
            return self

        # Search through all nodes in tree
        for path, obj in self.iter_tree():
            if obj.name == name:
                return obj

        return None

    def find_objects_by_type(self, obj_type: str) -> List['TreeNode']:
        """
        Find all objects of a given type

        Args:
            obj_type: Type of node to find

        Returns:
            List of nodes matching the specified type
        """
        results = []

        # Check self first
        if self.node_type == obj_type:
            results.append(self)

        # Then search all descendants
        for path, obj in self.iter_tree():
            if obj != self and obj.node_type == obj_type:
                results.append(obj)

        return results

    def iter_tree(self) -> Iterator[Tuple[NodePath, 'TreeNode']]:
        """Iterate over all nodes in the tree"""
        yield self.path, self
        for child in self.children:
            yield from child.iter_tree()

    def iter_visible(self) -> Iterator['TreeNode']:
        """Iterate over all visible nodes in the tree"""
        if self.visible:
            yield self
            for child in self.children:
                yield from child.iter_visible()

    def format_tree(self, include_details: bool = True) -> str:
        """Create a string representation of the tree"""
        lines = ["Tree Structure:"]

        def _print_node(node, prefix="", is_last=True):
            # Visibility indicator
            vis_indicator = "[✓]" if node.visible else "[✗]"

            # Create node representation
            type_label = node.node_type

            # Determine details based on node attributes
            detail = ""
            if hasattr(node, 'is_directory') and node.is_directory:
                if hasattr(node, 'is_trajectory') and node.is_trajectory:
                    detail = f"[{len(node.children)} frames]" if hasattr(
                        node, 'children') else ""
                else:
                    detail = f"[{len(node.children)} items]" if hasattr(
                        node, 'children') else ""

            # Format the line
            node_text = f"{node.name} {vis_indicator} {type_label}"
            if detail:
                node_text += f" {detail}"
            if include_details:
                node_text += f" (id:{node.uuid[:8]}...)"

            lines.append(f"{prefix}{'└── ' if is_last else '├── '}{node_text}")

            # Process children
            children = node.children
            for i, child in enumerate(children):
                _print_node(child,
                            prefix + ("    " if is_last else '│   '),
                            i == len(children) - 1)

        # Start with root node
        _print_node(self)

        # Fix: use proper string join
        return "\n".join(lines) if len(lines) > 1 else "Tree: < empty >"

    def reorder_child(self, child: 'TreeNode', new_position: int | None, send_signals: bool = True) -> Tuple[bool, str]:
        """
        Reorder a child within its current parent.

        Args:
            child: TreeNode object
            new_position: New position index for the child
            send_signals: Whether to emit signals after the operation

        Returns:
            Tuple of (success, message)
        """

        # Verify child belongs to this parent
        if child.uuid not in self._children:
            return False, "Child does not belong to this parent"

        # Get current list of children
        children_list = list(self._children.values())
        new_position = new_position or len(children_list) - 1

        # Check if position is valid
        if not (0 <= new_position < len(children_list)):
            return False, f"Invalid position {new_position}, valid range is 0-{len(children_list)-1}"

        # Get current position
        current_position = children_list.index(child)

        # If position is the same, no change needed
        if current_position == new_position:
            return True, "Child already at requested position"

        # Remove from current position and insert at new position
        children_list.remove(child)
        children_list.insert(new_position, child)

        # Rebuild dictionary to maintain order
        self._children = {node.uuid: node for node in children_list}

        # Emit signal if requested and signals object exists
        if send_signals and self._signals:
            self._signals.tree_structure_changed.emit()

        return True, f"Child moved from position {current_position} to {new_position}"
