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
    @property
    def render_settings(self):
        return self._render_settings

    @render_settings.setter
    def render_settings(self, value):
        self._render_settings = value
        if self.signals:
            self.signals.render_changed.emit(self.uuid)


class ScalarFieldObject(SceneObject):
    def __init__(self, name: str, scalar_field: ScalarField, parent=None, visible=True, signals: Optional[TreeSignals] = None):
        super().__init__(name=name, data=scalar_field,
                         node_type="scalar_field", parent=parent, visible=visible, signals=signals)
        self.scalar_field = scalar_field
        self._render_settings = ScalarFieldRenderSettings()

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
        self._render_settings = MoleculeRenderSettings()

    def _can_add_child(self, child):
        """Override to restrict children to scalar fields"""
        if not isinstance(child, ScalarFieldObject):
            return False, 'Molecule objects can only have scalar fields as children'

        if child.name in [c.name for c in self.children]:
            return False, f'A child with name {child.name} already exists'

        return True, ""

    def add_child(self, child: SceneObject, position: Optional[int] = None, send_signals: bool = True) -> Tuple[bool, str]:
        """Add a scalar field to molecule and maintain data relationship"""

        success, msg = super().add_child(
            child=child, position=position, send_signals=False)
        if not success:
            return success, msg

        # If it's a scalar field, update the molecule's data
        if isinstance(child, ScalarFieldObject):
            self.molecule.scalar_fields[child.name] = child.scalar_field
        else:
            # This should never happen due to the _can_add_child check, but just in case
            raise NotImplementedError(
                "Only ScalarFieldObjects can be added as children to MoleculeObject")

        if send_signals and self._signals:
            self._signals.node_added.emit(child.uuid)
            self._signals.tree_structure_changed.emit()

        return success, msg

    def remove_child(self, child: SceneObject, send_signals: bool = True):
        """Remove child and also update the molecule data"""

        child = super().remove_child(child, send_signals=False)

        child = self.molecule.scalar_fields.pop(child.name, None)

        if send_signals and self._signals:
            self._signals.node_removed.emit(child.uuid)
            self._signals.tree_structure_changed.emit()

        return child

    def reorder_child(self, child: SceneObject, new_position: int, send_signals=True):
        """Reorder the child with the given UUID to the new position"""

        success, msg = super().reorder_child(child, new_position, send_signals=False)
        if not success:
            return success, msg

        # Get current positions of scalar fields in both children and molecule
        children_list = list(self._children.values())
        old_position = children_list.index(child.name)

        items = list(self.molecule.scalar_fields.items())
        item = items.pop(old_position)
        items.insert(new_position, item)
        self.molecule.scalar_fields = dict(items)

        if not success:
            raise ValueError('Failed to reorder children: ' + msg)

        if send_signals and self._signals:
            self._signals.tree_structure_changed.emit()

        return True, f'Successfully reordered {child.name} to position {new_position}'

    @classmethod
    def from_molecule(cls, molecule: Molecule, name: str, parent=None, visible=True, signals: Optional[TreeSignals] = None, send_signals=True) -> 'MoleculeObject':
        molecule_object = cls(name, molecule, parent, visible, signals)
        for scalar_field_name, scalar_field in molecule.scalar_fields.items():
            scalar_field_object = ScalarFieldObject(
                scalar_field_name, scalar_field, molecule_object, visible, signals)
            molecule_object._children[scalar_field_object.uuid] = scalar_field_object

        if send_signals and molecule_object._signals:
            molecule_object._signals.tree_structure_changed

        return molecule_object

    @classmethod
    def from_xyz_file(cls, path: Union[str, pathlib.Path], name: Optional[str] = None, parent=None, visible=True, signals: Optional[TreeSignals] = None, send_signals=True) -> 'MoleculeObject':
        molecule = Molecule.load(path)
        if name is None:
            name = pathlib.Path(path).stem
        return cls.from_molecule(molecule, name, parent, visible, signals, send_signals=send_signals)

    @classmethod
    def from_cube_file(cls, path: Union[str, pathlib.Path], name: Optional[str] = None, parent=None, visible=True, signals: Optional[TreeSignals] = None, send_signals=True) -> 'MoleculeObject':
        if name is None:
            name = pathlib.Path(path).stem

        scalar_field_name = name+'_field'
        molecule = Molecule.load_from_cube(path, name=scalar_field_name)
        return cls.from_molecule(molecule, name, parent, visible, signals, send_signals=send_signals)


class TrajectoryObject(SceneObject):
    """Represents a trajectory object with multiple frames"""

    def __init__(self, name: str, trajectory: Trajectory, parent=None, visible=True, signals: Optional[TreeSignals] = None):
        super().__init__(name=name, node_type="trajectory",
                         parent=parent, visible=visible, signals=signals)
        self.trajectory = trajectory
        self._render_settings = TrajectoryRenderSettings()
        self.data = trajectory

    def _can_add_child(self, child):
        """Override to restrict children to molecules"""
        if not isinstance(child, MoleculeObject):
            return False, 'Trajectory objects can only have molecules as children'

        if child.name in [c.name for c in self.children]:
            return False, f'A molecule with name {child.name} already exists in this trajectory'

        return True, ""

    def add_child(self, child: SceneObject, position: Optional[int] = None, send_signals: bool = True) -> Tuple[bool, str]:
        """Add a molecule to trajectory and maintain data relationship"""

        success, msg = super().add_child(
            child=child, position=position, send_signals=False)
        if not success:
            return success, msg

        # If it's a molecule, update the trajectory's data
        if isinstance(child, MoleculeObject):
            if position is None or position >= len(self.trajectory):
                self.trajectory.append(child.molecule)
            else:
                self.trajectory.insert(position, child.molecule)
        else:
            # This should never happen due to the _can_add_child check, but just in case
            raise NotImplementedError(
                "Only MoleculeObjects can be added as children to TrajectoryObject")

        if send_signals and self._signals:
            self._signals.node_added.emit(child.uuid)
            self._signals.tree_structure_changed.emit()

        return success, msg

    def remove_child(self, child: SceneObject, send_signals: bool = True):
        """Remove child and also update the trajectory data"""

        child = super().remove_child(child, send_signals=False)

        # Find the index of the child in the trajectory
        for i, molecule in enumerate(self.trajectory):
            if molecule is child.molecule:
                self.trajectory.remove_image(i)
                break

        if send_signals and self._signals:
            self._signals.node_removed.emit(child.uuid)
            self._signals.tree_structure_changed.emit()

        return child

    def reorder_child(self, child: SceneObject, new_position: int, send_signals=True):
        """Reorder the child with the given UUID to the new position"""

        success, msg = super().reorder_child(child, new_position, send_signals=False)
        if not success:
            return success, msg

        # Get current positions of molecules
        children_list = list(self._children.values())
        old_position = children_list.index(child)

        # Update trajectory data order
        molecule = self.trajectory[old_position]
        self.trajectory.remove_image(old_position)
        self.trajectory.insert(new_position, molecule)

        if send_signals and self._signals:
            self._signals.tree_structure_changed.emit()

        return True, f'Successfully reordered {child.name} to position {new_position}'

    @classmethod
    def from_trajectory(cls, trajectory, name, parent=None, visible=True, signals: Optional[TreeSignals] = None, send_signals=True) -> 'TrajectoryObject':
        logger.info(
            f"Creating trajectory {name} object with {len(trajectory)} frames")
        trajectory_object = cls(name, trajectory, parent, visible, signals)
        # Create molecule objects for each frame
        for i, image in enumerate(trajectory):
            image_name = f'Frame_{i}'
            logger.debug(
                f"Creating molecule object for {image_name} with signals {signals}")
            molecule_object = MoleculeObject.from_molecule(
                molecule=image, name=image_name, parent=trajectory_object, visible=i == 0, signals=signals, send_signals=False)
            trajectory_object._children[molecule_object.uuid] = molecule_object

        if send_signals and trajectory_object._signals:
            trajectory_object._signals.tree_structure_changed.emit()

        return trajectory_object

    @classmethod
    def from_xyz_file(cls, path, name: Optional[str] = None, parent=None, visible=True, signals: Optional[TreeSignals] = None, send_signals=True) -> 'TrajectoryObject':
        trajectory = Trajectory.load(path)

        logger.info(f"Loaded trajectory with {len(trajectory)} frames")

        if name is None:
            name = pathlib.Path(path).stem

        return cls.from_trajectory(trajectory, name,  parent, visible, signals, send_signals=send_signals)
