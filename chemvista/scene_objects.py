import logging
import pathlib
import uuid
from dataclasses import dataclass
from typing import (Any, Dict, Generic, Iterator, List, Optional, Tuple,
                    TypeVar, Union)

import pyvista as pv
from nx_ase import Molecule, ScalarField, Trajectory
from PyQt5.QtCore import QObject, pyqtSignal

from .renderer import MoleculeRenderer, ScalarFieldRenderer
from .renderer.render_settings import (MoleculeRenderSettings,
                                       ScalarFieldRenderSettings,
                                       TrajectoryRenderSettings)
from .tree_structure import NodePath, TreeNode, TreeSignals

# Create a logger for this module
logger = logging.getLogger("chemvista.scene")

T = TypeVar('T')  # Generic type for scene object data


class SceneObject(TreeNode[T]):
    pass


class ScalarFieldObject(SceneObject):
    def __init__(self, name: str, scalar_field: ScalarField, parent=None, visible=True, signals: Optional[TreeSignals] = None):
        super().__init__(name=name, data=scalar_field,
                         node_type="scalar_field", parent=parent, visible=visible, signals=signals)
        self.scalar_field = scalar_field
        self.render_settings = ScalarFieldRenderSettings()

    def _can_add_child(self, child):
        return False, 'Scalar field objects cannot have children'

    @classmethod
    def from_cube_file(cls, path: Union[str, pathlib.Path], name: Optional[str] = None, parent=None, visible=True) -> 'ScalarFieldObject':
        scalar_field = ScalarField.load_cube(path)
        if name is None:
            name = pathlib.Path(path).stem
        return cls(name, scalar_field, parent, visible)


class MoleculeObject(SceneObject):
    def __init__(self, name: str, molecule: Molecule, parent=None, visible=True, signals: Optional[TreeSignals] = None):
        super().__init__(name=name, data=molecule,
                         node_type="molecule", parent=parent, visible=visible, signals=signals)
        self.molecule = molecule
        self.render_settings = MoleculeRenderSettings()

    def _can_add_child(self, child):
        """Override to restrict children to scalar fields"""
        if not isinstance(child, ScalarFieldObject):
            return False, 'Molecule objects can only have scalar fields as children'

        if child.name in [c.name for c in self.children]:
            return False, f'A child with name {child.name} already exists'

        return True, ""

    def add_child(self, child: SceneObject, position: Optional[int] = None) -> Tuple[bool, str]:
        """Add a scalar field to molecule and maintain data relationship"""
        # First check if we can add this child
        can_add, msg = self._can_add_child(child)
        if not can_add:
            return False, msg

        # If it's a scalar field, add to the molecule's data structure
        if isinstance(child, ScalarFieldObject):
            # Add to parent using the TreeNode implementation
            success, msg = self._add_child_to_tree(child, position)
            if not success:
                return success, msg

            # Also add to molecule's scalar_fields dict
            self.molecule.scalar_fields[child.name] = child.scalar_field
            return True, "Scalar field added to molecule"

        return False, "Only scalar fields can be added to molecules"

    def remove_child(self, child):
        """Remove child and also update the molecule data"""
        if isinstance(child, str):
            # Find the child by UUID
            child_obj = None
            for c in self.children:
                if c.uuid == child:
                    child_obj = c
                    break

            if not child_obj:
                return None
            child = child_obj

        # If it's a scalar field, remove from molecule's data
        if isinstance(child, ScalarFieldObject):
            self.molecule.scalar_fields.pop(child.name, None)

        # Use parent class to remove the child properly
        return super().remove_child(child)

    @classmethod
    def from_xyz_file(cls, path: Union[str, pathlib.Path], name: Optional[str] = None, parent=None, visible=True, signals: Optional[TreeSignals] = None) -> 'MoleculeObject':
        molecule = Molecule.load(path)
        if name is None:
            name = pathlib.Path(path).stem
        return cls(name, molecule, parent, visible, signals)

    @classmethod
    def from_cube_file(cls, path: Union[str, pathlib.Path], name: Optional[str] = None, parent=None, visible=True, signals: Optional[TreeSignals] = None) -> 'MoleculeObject':
        if name is None:
            name = pathlib.Path(path).stem

        scalar_field_name = name+'_field'
        molecule = Molecule.load_from_cube(path, name=scalar_field_name)
        molecule_object = cls(name, molecule, parent, visible, signals)

        # Create scalar field object for the molecule
        scalar_field = molecule.scalar_fields[scalar_field_name]
        scalar_field_object = ScalarFieldObject(
            scalar_field_name, scalar_field, molecule_object, visible, signals)

        molecule_object._add_child_to_tree(scalar_field_object)

        return molecule_object


class TrajectoryObject(SceneObject):
    """Represents a trajectory object with multiple frames"""

    def __init__(self, name: str, trajectory: Trajectory, parent=None, visible=True, signals: Optional[TreeSignals] = None):
        super().__init__(name=name, node_type="trajectory",
                         parent=parent, visible=visible, signals=signals)
        self.trajectory = trajectory
        self.render_settings = TrajectoryRenderSettings()
        self.data = trajectory

    def _can_add_child(self, child):
        """Override to restrict children to molecules"""
        if not isinstance(child, MoleculeObject):
            return False, 'Trajectory objects can only have molecules as children'

        if child.name in [c.name for c in self.children]:
            return False, f'A molecule with name {child.name} already exists in this trajectory'

        return True, ""

    def add_child(self, child: SceneObject, position: Optional[int] = None) -> Tuple[bool, str]:
        """Add a molecule to trajectory and maintain data relationship"""
        # First check if we can add this child
        can_add, msg = self._can_add_child(child)
        if not can_add:
            return False, msg

        # If it's a molecule, add to the trajectory's data
        if isinstance(child, MoleculeObject):
            # Determine position within trajectory
            if position is None:
                position = len(self.children)

            # Add to parent using the TreeNode implementation
            success, msg = self._add_child_to_tree(child, position)
            if not success:
                return success, msg

            if position == len(self.trajectory):
                self.trajectory.append(child.molecule)
            else:
                # Also update the trajectory data structure
                self.trajectory.insert(position, child.molecule)
            return True, f"Molecule added to trajectory at position {position}"

        return False, "Only molecules can be added to trajectories"

    def remove_child(self, child):
        """Remove child and update trajectory data"""
        if isinstance(child, str):
            # Find the child by UUID
            child_obj = None
            for i, c in enumerate(self.children):
                if c.uuid == child:
                    child_obj = c
                    idx = i
                    break

            if not child_obj:
                return None
            child = child_obj

        # Find the index of the child in the children list
        try:
            idx = self.children.index(child)
            # Remove from trajectory data structure
            if idx < len(self.trajectory):
                self.trajectory.remove_image(idx)
        except ValueError:
            pass

        # Use parent class to remove the child properly
        return super().remove_child(child)

    @classmethod
    def from_trajectory(cls, trajectory, name, parent=None, visible=True, signals: Optional[TreeSignals] = None) -> 'TrajectoryObject':
        trajectory_object = cls(name, trajectory, parent, visible)
        # Create molecule objects for each frame
        for i, image in enumerate(trajectory):
            image_name = f'Frame_{i}'

            molecule_object = MoleculeObject(
                image_name, image, trajectory_object, visible=i == 0, signals=signals)
            trajectory_object._add_child_to_tree(molecule_object)

        return trajectory_object

    @classmethod
    def from_xyz_file(cls, path, name: Optional[str] = None, parent=None, visible=True, signals: Optional[TreeSignals] = None) -> 'TrajectoryObject':
        trajectory = Trajectory.load(path)

        logger.info(f"Loaded trajectory with {len(trajectory)} frames")

        if name is None:
            name = pathlib.Path(path).stem

        return cls.from_trajectory(trajectory, name,  parent, visible, signals)
