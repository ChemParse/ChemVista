import pyvista as pv
from nx_ase import Molecule, ScalarField, Trajectory
import pathlib
import uuid
from typing import Union, Optional, List, Dict, Iterator, Tuple
from .renderer import MoleculeRenderer, ScalarFieldRenderer
from .renderer.render_settings import MoleculeRenderSettings, ScalarFieldRenderSettings
from .tree_structure import TreeSignals, TreeNode
import logging
from .scene_objects import (
    SceneObject, ScalarFieldObject, MoleculeObject,
    TrajectoryObject
)

# Create a logger for this module
logger = logging.getLogger("chemvista.manager")


class SceneManager():
    """Manages the scene graph and provides operations on scene objects"""

    def __init__(self, signals=None):
        super().__init__()
        self.molecule_renderer = MoleculeRenderer()
        self.scalar_field_renderer = ScalarFieldRenderer()
        self.plotter = None

        # Create a generic root node (not a SceneObject)
        self.root = TreeNode(name="Scene", node_type="root")

        # Create tree signals
        self._signals = signals
        self.root._signals = self._signals

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

    @property
    def root_objects(self):
        """Get all root level objects"""
        return self.root.children

    def load_xyz(self, filepath: Union[str, pathlib.Path]) -> str:
        """Load molecule or trajectory from XYZ file and return UUID"""
        filepath = pathlib.Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File {filepath} not found")

        path = Trajectory.load(filepath)

        # If there's only one frame, treat it as a regular molecule
        if len(path) == 1:
            molecule = path[0]
            mol_obj = MoleculeObject(
                name=filepath.stem, molecule=molecule, visible=True, signals=self._signals)

            success, message = self.root.add_child(mol_obj)
            if not success:
                logger.error("Failed to add molecule to scene: " + message)
                raise RuntimeError(
                    "Failed to add molecule to scene: " + message)
            logger.info(f"Loaded molecule from {filepath}")
            return mol_obj.uuid

        # If there are multiple frames, create a trajectory object
        logger.info(
            f"Loading trajectory with {len(path)} frames from {filepath}")

        # Create trajectory object using from_xyz_file
        # (this already creates molecule children internally)
        traj_obj = TrajectoryObject.from_trajectory(
            path, name=filepath.stem, signals=self._signals)

        # Add to root AFTER registration
        success, message = self.root.add_child(traj_obj)
        if not success:
            logger.error("Failed to add trajectory to scene: " + message)
            raise RuntimeError("Failed to add trajectory to scene: " + message)

        return traj_obj.uuid

    def load_molecule_from_cube(self, filepath: Union[str, pathlib.Path]) -> str:
        """Load both molecule and its scalar field from cube file"""
        filepath = pathlib.Path(filepath)
        logger.info(f"Loading molecule with scalar field from {filepath}")

        if not filepath.exists():
            logger.error(f"File {filepath} not found")
            raise FileNotFoundError(f"File {filepath} not found")

        # Create molecule object with integrated scalar field
        # (this creates scalar field children internally)
        mol_obj = MoleculeObject.from_cube_file(
            filepath, name=filepath.stem, signals=self._signals)

        # Register the molecule and all its scalar field children
        success, message = self.root.add_child(mol_obj)

        if not success:
            raise RuntimeError("Failed to add molecule to scene: " + message)

        # Collect all UUIDs (molecule and scalar fields)
        return mol_obj.uuid

    def load_scalar_field_from_cube(self, filepath: Union[str, pathlib.Path]) -> str:
        """Load scalar field from cube file"""
        filepath = pathlib.Path(filepath)

        field_obj = ScalarFieldObject.from_cube_file(filepath)

        # Add to root AFTER registration
        success, message = self.root.add_child(field_obj)
        if not success:
            raise RuntimeError(
                "Failed to add scalar field to scene: " + message)

        return field_obj.uuid

    def create_trajectory(self, name: str, parent_uuid: Optional[str] = None) -> str:
        """Create an empty trajectory container"""
        parent = self.root if parent_uuid is None else self.get_object_by_uuid(
            parent_uuid)

        traj = Trajectory()
        traj_obj = TrajectoryObject(name, traj)

        success, message = parent.add_child(traj_obj)

        if not success:
            raise RuntimeError("Failed to add trajectory to scene: " + message)

        return traj_obj.uuid

    def get_object_by_uuid(self, uuid: str) -> Union[TreeNode, SceneObject]:
        """Get object by UUID"""
        return self.root.get_object_by_uuid(uuid)

    def get_object_by_name(self, name: str) -> Optional[Union[TreeNode, SceneObject]]:
        """Find an object by name (first match)"""
        return self.root.get_object_by_name(name)

    def find_objects_by_type(self, obj_type: str) -> List[Union[TreeNode, SceneObject]]:
        """Find all objects of a given type"""
        return self.root.find_objects_by_type(obj_type)

    def set_visibility(self, uuid: str, visible: bool) -> None:
        """Set object visibility"""
        # Use the TreeNode visibility method directly
        self.root.set_visibility(uuid, visible)

    def update_settings(self, uuid: str, settings) -> None:
        """Update render settings for an object"""
        obj = self.get_object_by_uuid(uuid)
        if hasattr(obj, 'render_settings'):
            obj.render_settings = settings
            self._signals.node_changed.emit(uuid)

    def render(self, plotter: Optional[pv.Plotter] = None, **kwargs) -> pv.Plotter:
        """Render all visible objects"""
        if plotter is None:
            if self.plotter is not None:
                self.plotter.clear()
            plotter = self.plotter or self.create_plotter(**kwargs)

        # Use the TreeNode's iter_visible to efficiently render only visible nodes
        for obj in self.root.iter_visible():
            # Skip root node
            if obj == self.root:
                continue

            # Render based on object type
            if isinstance(obj, MoleculeObject):
                self.molecule_renderer.render(
                    molecule=obj.molecule,
                    plotter=plotter,
                    settings=vars(obj.render_settings)
                )
            elif isinstance(obj, ScalarFieldObject):
                self.scalar_field_renderer.render(
                    field=obj.scalar_field,
                    plotter=plotter,
                    settings=vars(obj.render_settings)
                )

        plotter.reset_camera()
        return plotter

    def log_tree_changes(self, message: str = ""):
        """Log the current tree structure"""
        if message:
            logger.info(f"Tree Change: {message}")
        logger.info("\n" + self.root.format_tree())

    def delete_object(self, uuid: str) -> None:
        """Delete object by UUID"""
        obj = self.get_object_by_uuid(uuid)
        if obj is None:
            logger.warning(f"Object with UUID {uuid} not found")
            return

        # Use the TreeNode method to remove the object
        self.root.remove_child(obj)
        logger.info(f"Deleted object with UUID {uuid}")

    def move_object(self, uuid: str, new_parent_uuid: str, position=None) -> None:
        """Move object to a new parent"""
        obj = self.get_object_by_uuid(uuid)
        new_parent = self.get_object_by_uuid(new_parent_uuid)

        if obj is None or new_parent is None:
            logger.error(
                f"Failed to move object with UUID {uuid} to new parent {new_parent_uuid}")
            return

        # Use the TreeNode method to move the object
        self.root.move(obj, new_parent, position)
        logger.info(
            f"Moved object with UUID {uuid} to new parent {new_parent_uuid}")
