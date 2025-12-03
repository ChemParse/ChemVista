import logging
import pathlib
import uuid
from dataclasses import dataclass
from typing import (Any, Dict, Generic, Iterator, List, Optional, Tuple,
                    TypeVar, Union)

import numpy as np
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

    def remove_child(self, child: SceneObject, send_signals: bool = True) -> SceneObject:
        """Remove child and also update the molecule data"""

        child = super().remove_child(child, send_signals=False)

        scalar_field = self.molecule.scalar_fields.pop(child.name, None)

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
    """Represents a trajectory object with multiple frames and animation support"""

    def __init__(self, name: str, trajectory: Trajectory, parent=None, visible=True, signals: Optional[TreeSignals] = None):
        super().__init__(name=name, node_type="trajectory",
                         parent=parent, visible=visible, signals=signals)
        self.trajectory = trajectory
        self._render_settings = TrajectoryRenderSettings()
        self.data = trajectory
        self._current_frame = 0
        self._is_playing = False
        self._loop = True
        self._fps = 10

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

    # ==================== Frame Management ====================

    @property
    def num_frames(self) -> int:
        """Get the total number of frames in the trajectory"""
        return len(list(self._children.values()))

    @property
    def current_frame(self) -> int:
        """Get the current frame index"""
        return self._current_frame

    @current_frame.setter
    def current_frame(self, value: int):
        """Set the current frame index"""
        self.set_frame(value)

    @property
    def fps(self) -> int:
        """Get the frames per second for animation playback"""
        return self._fps

    @fps.setter
    def fps(self, value: int):
        """Set the frames per second for animation playback"""
        self._fps = max(1, min(60, value))  # Clamp between 1 and 60

    @property
    def loop(self) -> bool:
        """Get whether animation should loop"""
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        """Set whether animation should loop"""
        self._loop = value

    @property
    def is_playing(self) -> bool:
        """Check if animation is currently playing"""
        return self._is_playing

    def get_frame(self, index: int) -> Optional['MoleculeObject']:
        """Get the MoleculeObject at the specified frame index"""
        frames = list(self._children.values())
        if 0 <= index < len(frames):
            return frames[index]
        return None

    def set_frame(self, index: int, send_signals: bool = True) -> bool:
        """
        Set the current frame, updating visibility of all frame children.

        Args:
            index: Frame index to display (0-based)
            send_signals: Whether to emit render_changed signal

        Returns:
            True if frame was changed successfully, False otherwise
        """
        frames = list(self._children.values())
        num_frames = len(frames)

        if num_frames == 0:
            return False

        # Handle wrapping for loop mode
        if self._loop:
            index = index % num_frames
        else:
            index = max(0, min(index, num_frames - 1))

        if index == self._current_frame and frames[index].visible:
            return True  # Already at this frame

        self._current_frame = index

        # Update visibility: only the current frame is visible
        for i, frame in enumerate(frames):
            frame._visible = (i == index)

        logger.debug(f"Trajectory '{self.name}': switched to frame {index}/{num_frames - 1}")

        if send_signals and self._signals:
            self._signals.render_changed.emit(self.uuid)

        return True

    def next_frame(self, send_signals: bool = True) -> bool:
        """
        Advance to the next frame.

        Returns:
            True if advanced, False if at end and not looping
        """
        frames = list(self._children.values())
        num_frames = len(frames)

        if num_frames == 0:
            return False

        next_idx = self._current_frame + 1

        if next_idx >= num_frames:
            if self._loop:
                next_idx = 0
            else:
                return False  # At end, not looping

        return self.set_frame(next_idx, send_signals)

    def previous_frame(self, send_signals: bool = True) -> bool:
        """
        Go to the previous frame.

        Returns:
            True if moved back, False if at start and not looping
        """
        frames = list(self._children.values())
        num_frames = len(frames)

        if num_frames == 0:
            return False

        prev_idx = self._current_frame - 1

        if prev_idx < 0:
            if self._loop:
                prev_idx = num_frames - 1
            else:
                return False  # At start, not looping

        return self.set_frame(prev_idx, send_signals)

    def first_frame(self, send_signals: bool = True) -> bool:
        """Go to the first frame"""
        return self.set_frame(0, send_signals)

    def last_frame(self, send_signals: bool = True) -> bool:
        """Go to the last frame"""
        return self.set_frame(self.num_frames - 1, send_signals)

    # ==================== Interpolation ====================

    def get_interpolated_positions(self, t: float) -> Optional[np.ndarray]:
        """
        Get interpolated atom positions at time t.

        Args:
            t: Time value where 0.0 = first frame, num_frames-1 = last frame.
               Can be fractional for interpolation between frames.

        Returns:
            numpy array of shape (num_atoms, 3) with interpolated positions,
            or None if trajectory is empty.
        """
        frames = list(self._children.values())
        num_frames = len(frames)

        if num_frames == 0:
            return None

        if num_frames == 1:
            return frames[0].molecule.positions.copy()

        # Clamp or wrap t based on loop setting
        if self._loop:
            t = t % num_frames
        else:
            t = max(0.0, min(t, num_frames - 1))

        # Get the two frames to interpolate between
        frame_idx = int(t)
        alpha = t - frame_idx  # Fractional part

        if frame_idx >= num_frames - 1:
            # At or past last frame
            if self._loop and alpha > 0:
                # Interpolate between last and first frame
                pos1 = frames[num_frames - 1].molecule.positions
                pos2 = frames[0].molecule.positions
            else:
                return frames[num_frames - 1].molecule.positions.copy()
        else:
            pos1 = frames[frame_idx].molecule.positions
            pos2 = frames[frame_idx + 1].molecule.positions

        # Linear interpolation
        return pos1 * (1.0 - alpha) + pos2 * alpha

    def get_frame_molecule_at_time(self, t: float) -> Optional['Molecule']:
        """
        Get a molecule with interpolated positions at time t.

        Creates a copy of the first frame's molecule with interpolated positions.

        Args:
            t: Time value for interpolation

        Returns:
            Molecule object with interpolated positions, or None if empty
        """
        from nx_ase import Molecule

        frames = list(self._children.values())
        if not frames:
            return None

        positions = self.get_interpolated_positions(t)
        if positions is None:
            return None

        # Create a copy of the first frame's molecule
        base_mol = frames[0].molecule
        mol_copy = base_mol.copy()
        mol_copy.positions = positions

        return mol_copy

    # ==================== Animation Playback ====================

    def play(self):
        """Start animation playback (requires external timer integration)"""
        self._is_playing = True
        logger.info(f"Trajectory '{self.name}': playback started at {self._fps} fps")

    def pause(self):
        """Pause animation playback"""
        self._is_playing = False
        logger.info(f"Trajectory '{self.name}': playback paused at frame {self._current_frame}")

    def stop(self):
        """Stop animation and reset to first frame"""
        self._is_playing = False
        self.first_frame()
        logger.info(f"Trajectory '{self.name}': playback stopped")

    def toggle_playback(self):
        """Toggle between play and pause"""
        if self._is_playing:
            self.pause()
        else:
            self.play()

    def animation_step(self, send_signals: bool = True) -> bool:
        """
        Advance animation by one frame if playing.
        Call this from a timer callback.

        Returns:
            True if animation should continue, False if it should stop
        """
        if not self._is_playing:
            return False

        if not self.next_frame(send_signals):
            # Reached end and not looping
            self._is_playing = False
            return False

        return True

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
