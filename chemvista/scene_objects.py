import pyvista as pv
from nx_ase import Molecule, ScalarField, Path
import pathlib
import uuid
from typing import Union, Optional, List, Dict, Iterator, Tuple
from dataclasses import dataclass
from .renderer import MoleculeRenderer, ScalarFieldRenderer
from .render_settings import RenderSettings, ScalarFieldRenderSettings
from PyQt5.QtCore import QObject, pyqtSignal
import logging

# Create a logger for this module
logger = logging.getLogger("chemvista.scene")


@dataclass
class ObjectPath:
    """Represents a path to an object in the scene tree"""
    parts: List[str]

    def __str__(self) -> str:
        return '/'.join(self.parts)

    @classmethod
    def from_string(cls, path_str: str) -> 'ObjectPath':
        return cls(path_str.strip('/').split('/'))


class SceneNode:
    """Base class for all scene objects with tree structure support"""

    def __init__(self, name: str):
        self.name = name
        self.uuid = str(uuid.uuid4())
        self.visible = True
        self.parent = None
        self._path_cache = None

    @property
    def path(self) -> ObjectPath:
        """Get full path to this node"""
        if self._path_cache is None:
            parts = []
            current = self
            while current is not None:
                parts.append(current.name)
                current = current.parent
            self._path_cache = ObjectPath(list(reversed(parts)))
        return self._path_cache

    def _invalidate_path_cache(self):
        """Invalidate path cache for this node and all children"""
        self._path_cache = None
        if hasattr(self, 'children'):
            for child in self.children:
                child._invalidate_path_cache()


class SceneObject(SceneNode):
    def __init__(self, name: str, molecule: Molecule):
        super().__init__(name)
        self.molecule = molecule
        self.render_settings = RenderSettings()
        self.children = []  # Add children list for scalar fields


class ScalarFieldObject(SceneNode):
    def __init__(self, name: str, scalar_field: ScalarField):
        super().__init__(name)
        self.scalar_field = scalar_field
        self.render_settings = ScalarFieldRenderSettings()


class SceneManager(QObject):
    # Signals
    object_added = pyqtSignal(str)  # emits object UUID
    object_removed = pyqtSignal(str)  # emits object UUID
    object_changed = pyqtSignal(str)  # emits object UUID
    # emits object UUID and visibility state
    visibility_changed = pyqtSignal(str, bool)
    structure_changed = pyqtSignal()  # Emitted when hierarchy changes

    def __init__(self):
        super().__init__()
        self.root_objects = []  # Top-level objects
        self._uuid_map = {}  # Maps UUIDs to objects
        self.molecule_renderer = MoleculeRenderer()
        self.scalar_field_renderer = ScalarFieldRenderer()
        self.plotter = None

    def __del__(self):
        """Cleanup resources"""
        if self.plotter is not None:
            try:
                self.plotter.close()
            except (AttributeError, RuntimeError):
                # Handle case where plotter or renderer might be invalid
                pass

    def create_plotter(self, off_screen: bool = False) -> pv.Plotter:
        """Create a new plotter or return existing one"""
        if self.plotter is None:
            self.plotter = pv.Plotter(off_screen=off_screen)
        return self.plotter

    def load_molecule(self, filepath: Union[str, pathlib.Path]) -> List[str]:
        """Load molecules from XYZ file and return UUIDs"""
        filepath = pathlib.Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File {filepath} not found")
        path = Path.load(filepath)
        if len(path) == 1:
            molecule = path[0]
            return [self.add_object(filepath.stem, molecule)]

        return [self.add_object(f"{filepath.stem}_{i}", molecule) for i, molecule in enumerate(path)]

    def load_molecule_from_cube(self, filepath: Union[str, pathlib.Path]) -> List[str]:
        """Load both molecule and its scalar field from cube file"""
        filepath = pathlib.Path(filepath)
        molecule = Molecule.load_from_cube(filepath)

        # Add molecule first
        mol_name = filepath.name
        mol_uuid = self.add_object(mol_name, molecule)
        uuids = [mol_uuid]

        # Then add scalar fields as children of the molecule
        for field_name, scalar_field in molecule.scalar_fields.items():
            field_uuid = self.add_object(
                field_name, scalar_field, parent=mol_uuid)
            uuids.append(field_uuid)

        return uuids

    def load_scalar_field(self, filepath: Union[str, pathlib.Path]) -> str:
        """Load scalar field from cube file"""
        filepath = pathlib.Path(filepath)
        scalar_field = ScalarField.load_cube(filepath)
        field_name = f"{filepath.stem}_field"
        return self.add_object(field_name, scalar_field)

    def add_object(self, name: str, obj: Union[Molecule, ScalarField], parent: Optional[str] = None) -> str:
        """Add object to scene with optional parent and return its UUID"""
        if isinstance(obj, Molecule):
            scene_obj = SceneObject(name, obj)
        elif isinstance(obj, ScalarField):
            scene_obj = ScalarFieldObject(name, obj)
        else:
            raise ValueError(f"Unsupported object type: {type(obj)}")

        # Register UUID
        self._uuid_map[scene_obj.uuid] = scene_obj

        if parent:
            parent_obj = self.get_object_by_uuid(parent)
            if hasattr(parent_obj, 'children'):
                parent_obj.children.append(scene_obj)
                scene_obj.parent = parent_obj
            else:
                raise ValueError(
                    "Cannot add child to an object that doesn't support children")
        else:
            self.root_objects.append(scene_obj)

        self.object_added.emit(scene_obj.uuid)
        self.structure_changed.emit()
        return scene_obj.uuid

    def remove_object(self, uuid: str) -> None:
        """Remove object and its children from scene"""
        obj = self.get_object_by_uuid(uuid)

        # Remove all children from UUID map
        if hasattr(obj, 'children'):
            for child in obj.children:
                self.remove_object(child.uuid)

        # Remove object itself from parent or root
        if obj.parent:
            obj.parent.children.remove(obj)
        else:
            self.root_objects.remove(obj)

        # Remove from UUID map
        self._uuid_map.pop(uuid, None)

        # Emit signals
        self.object_removed.emit(uuid)
        self.structure_changed.emit()

    def get_object(self, index: int) -> Union[SceneObject, ScalarFieldObject]:
        """Get object by index (for backward compatibility)"""
        return self.root_objects[index]

    def get_object_by_name(self, name: str) -> Union[SceneObject, ScalarFieldObject]:
        """Get object by name (for backward compatibility)"""
        for obj in self._uuid_map.values():
            if obj.name == name:
                return obj
        raise KeyError(f"Object with name '{name}' not found")

    def get_object_by_uuid(self, uuid: str) -> Union[SceneObject, ScalarFieldObject]:
        """Get object by UUID"""
        if uuid not in self._uuid_map:
            raise KeyError(f"Object with UUID {uuid} not found")
        return self._uuid_map[uuid]

    def set_visibility(self, uuid_or_name: str, visible: bool) -> None:
        """Set object visibility"""
        try:
            # Try as UUID first
            obj = self.get_object_by_uuid(uuid_or_name)
        except KeyError:
            # Fall back to name lookup for backward compatibility
            obj = self.get_object_by_name(uuid_or_name)

        obj.visible = visible
        self.visibility_changed.emit(
            obj.uuid if hasattr(obj, 'uuid') else uuid_or_name,
            visible
        )

    def update_settings(self, uuid_or_name: str, settings: Union[RenderSettings, ScalarFieldRenderSettings]) -> None:
        """Update object render settings"""
        try:
            # Try as UUID first
            obj = self.get_object_by_uuid(uuid_or_name)
        except KeyError:
            # Fall back to name lookup for backward compatibility
            obj = self.get_object_by_name(uuid_or_name)

        obj.render_settings = settings
        self.object_changed.emit(
            obj.uuid if hasattr(obj, 'uuid') else uuid_or_name)

    def render(self, plotter: Optional[pv.Plotter] = None, **kwargs) -> pv.Plotter:
        """Render all visible objects"""
        if plotter is None:
            if self.plotter is not None:
                self.plotter.close()
            plotter = pv.Plotter(**kwargs) if kwargs else self.create_plotter()

        plotter.clear()

        def render_objects(objects):
            for obj in objects:
                if not obj.visible:
                    continue

                if hasattr(obj, 'molecule'):
                    self.molecule_renderer.render(
                        molecule=obj.molecule,
                        plotter=plotter,
                        settings=vars(obj.render_settings)
                    )
                elif hasattr(obj, 'scalar_field'):
                    self.scalar_field_renderer.render(
                        field=obj.scalar_field,
                        plotter=plotter,
                        settings=vars(obj.render_settings)
                    )

                if hasattr(obj, 'children'):
                    render_objects(obj.children)

        render_objects(self.root_objects)
        plotter.reset_camera()
        return plotter

    @property
    def objects(self):
        """Return all objects (for backward compatibility)"""
        return list(self._uuid_map.values())

    def iter_tree(self) -> Iterator[Tuple[ObjectPath, Union[SceneObject, ScalarFieldObject]]]:
        """Iterate over all objects in the tree, yielding (path, object) pairs"""
        def _iter_node(node):
            yield node.path, node
            if hasattr(node, 'children'):
                for child in node.children:
                    yield from _iter_node(child)

        for root in self.root_objects:
            yield from _iter_node(root)

    def format_tree(self, include_details: bool = True) -> str:
        """Format the tree structure for display or logging

        Args:
            include_details: Whether to include detailed object information

        Returns:
            A formatted string representation of the tree
        """
        lines = ["Tree:"]

        def _print_node(node, prefix="", is_last=True):
            # Visibility indicator
            vis_indicator = "[✓]" if node.visible else "[✗]"

            # Get node type and identifier
            if hasattr(node, 'molecule'):
                node_type = "Molecule"
                if include_details:
                    details = f"[{len(node.molecule)} atoms]"
                else:
                    details = ""
            elif hasattr(node, 'scalar_field'):
                node_type = "ScalarField"
                if include_details:
                    # Safer way to get scalar field details
                    try:
                        if hasattr(node.scalar_field, 'grid') and hasattr(node.scalar_field.grid, 'shape'):
                            details = f"[{node.scalar_field.grid.shape} grid]"
                        elif hasattr(node.scalar_field, 'shape'):
                            details = f"[{node.scalar_field.shape} grid]"
                        elif hasattr(node.scalar_field, 'values') and hasattr(node.scalar_field.values, 'shape'):
                            details = f"[{node.scalar_field.values.shape} values]"
                        else:
                            details = "[scalar field]"
                    except Exception:
                        details = "[scalar field]"
                else:
                    details = ""
            else:
                node_type = "Unknown"
                details = ""

            # Create the formatted line
            if include_details:
                node_info = f"{node.name} {vis_indicator} {node_type} (id:{node.uuid[:8]}...) {details}"
            else:
                node_info = f"{node.name} {vis_indicator} {node_type}"

            lines.append(f"{prefix}{'└── ' if is_last else '├── '}{node_info}")

            # Process children if any
            if hasattr(node, 'children'):
                children = node.children
                for i, child in enumerate(children):
                    _print_node(child,
                                prefix + ("    " if is_last else '│   '),
                                i == len(children) - 1)

        # Process all root objects
        for i, root in enumerate(self.root_objects):
            _print_node(root, is_last=(i == len(self.root_objects) - 1))

        return "\n".join(lines) if len(lines) > 1 else "Tree: <empty>"

    def log_tree_changes(self, message: str = "Tree structure changed"):
        """Log tree structure changes with the current tree"""
        logger.info(f"TREE CHANGE: {message}")
        logger.info(self.format_tree(include_details=True))
