import pytest
import numpy as np
from PyQt5.QtCore import QObject
from chemvista.scene_objects import (SceneObject, ScalarFieldObject, MoleculeObject, TrajectoryObject
                                     )
from nx_ase import Molecule, ScalarField, Trajectory


class TestSceneObject:
    """Tests for the base SceneObject class"""

    def test_scene_object_creation(self):
        """Test creating a basic scene object"""
        obj = SceneObject("test_object", data={
                          "key": "value"}, node_type="specific_node_type")

        # Check basic properties
        assert obj.name == "test_object"
        assert obj.data == {"key": "value"}
        assert obj.node_type == "specific_node_type"
        assert obj.visible is True
        assert obj.parent is None
        assert len(obj.children) == 0
        assert isinstance(obj.uuid, str)

    def test_scene_object_hierarchy(self):
        """Test parent-child relationships"""
        parent = SceneObject("parent")
        child1 = SceneObject("child1")
        child2 = SceneObject("child2")
        parent.add_child(child1)
        parent.add_child(child2)

        assert len(parent.children) == 2
        assert child1 in parent.children
        assert child2 in parent.children

        # Check paths
        assert str(parent.path) == "/parent"
        assert str(child1.path) == "/parent/child1"
        assert str(child2.path) == "/parent/child2"

    def test_scene_manager_property(self):
        """Test scene_manager property inheritance"""
        # Create a mock scene manager
        class MockSceneManager(QObject):
            pass

        manager = MockSceneManager()

        # Create hierarchy
        root = SceneObject("root")

        level1 = SceneObject("level1")
        level2 = SceneObject("level2")
        level1.add_child(level2)
        root.add_child(level1)


class TestScalarFieldObject:
    """Tests for ScalarFieldObject class"""

    def test_scalar_field_object_creation(self, test_objects):
        """Test creating a scalar field object"""
        scalar_field = test_objects['scalar_field']
        sf_obj = ScalarFieldObject("test_field", scalar_field)

        # Check basic properties
        assert sf_obj.name == "test_field"
        assert sf_obj.scalar_field is scalar_field
        assert sf_obj.node_type == "scalar_field"
        assert sf_obj.visible is True

        # Check render settings
        assert hasattr(sf_obj, "render_settings")

    def test_scalar_field_cant_have_children(self, test_objects):
        """Test that scalar fields can't have children"""
        scalar_field = test_objects['scalar_field']
        sf_obj = ScalarFieldObject("test_field", scalar_field)
        child = SceneObject("child")

        # Attempt to add child should fail
        can_add, msg = sf_obj._can_add_child(child)
        assert can_add is False
        assert "cannot have children" in msg

        # Direct add_child call should also fail
        success, msg = sf_obj.add_child(child)
        assert success is False
        assert "cannot have children" in msg

    def test_from_cube_file(self, test_files):
        """Test creating from a cube file"""
        cube_path = test_files['scalar_filed_cube']
        if not cube_path.exists():
            pytest.skip(f"Test file {cube_path} not found")

        sf_obj = ScalarFieldObject.from_cube_file(cube_path)
        assert sf_obj.name == cube_path.stem
        assert hasattr(sf_obj, "scalar_field")
        assert sf_obj.node_type == "scalar_field"


class TestMoleculeObject:
    """Tests for MoleculeObject class"""

    def test_molecule_object_creation(self, test_objects):
        """Test creating a molecule object"""
        molecule = test_objects['molecule_1']
        mol_obj = MoleculeObject("test_molecule", molecule)

        # Check basic properties
        assert mol_obj.name == "test_molecule"
        assert mol_obj.molecule is molecule
        assert mol_obj.node_type == "molecule"
        assert mol_obj.visible is True

        # Check render settings
        assert hasattr(mol_obj, "render_settings")

    def test_molecule_scalar_field_children(self, test_objects):
        """Test adding scalar fields to molecules"""
        molecule = test_objects['molecule_1']
        scalar_field = test_objects['scalar_field']

        mol_obj = MoleculeObject("test_molecule", molecule)
        sf_obj = ScalarFieldObject("density", scalar_field)

        # Add scalar field as child
        success, msg = mol_obj.add_child(sf_obj)
        assert success is True
        assert len(mol_obj.children) == 1
        assert sf_obj in mol_obj.children

        # Check that scalar field was also added to molecule's scalar_fields dict
        assert "density" in mol_obj.molecule.scalar_fields
        assert mol_obj.molecule.scalar_fields["density"] is scalar_field

        # Try adding a non-scalar field (should fail)
        another_obj = SceneObject("another")
        success, msg = mol_obj.add_child(another_obj)
        assert success is False
        assert "can only have scalar fields" in msg

        # Try adding a duplicate name (should fail)
        sf_obj2 = ScalarFieldObject("density", scalar_field)
        success, msg = mol_obj.add_child(sf_obj2)
        assert success is False
        assert "already exists" in msg

    def test_molecule_remove_scalar_field(self, test_objects):
        """Test removing scalar fields from molecules"""
        molecule = test_objects['molecule_1']
        scalar_field = test_objects['scalar_field']

        mol_obj = MoleculeObject("test_molecule", molecule)
        sf_obj = ScalarFieldObject("density", scalar_field)

        mol_obj.add_child(sf_obj)
        assert "density" in mol_obj.molecule.scalar_fields

        # Remove scalar field
        removed = mol_obj.remove_child(sf_obj)
        assert removed is sf_obj
        assert len(mol_obj.children) == 0
        assert "density" not in mol_obj.molecule.scalar_fields

        # Test removing by UUID
        mol_obj.add_child(sf_obj)
        removed = mol_obj.remove_child(sf_obj.uuid)
        assert removed is sf_obj
        assert "density" not in mol_obj.molecule.scalar_fields

    def test_from_xyz_file(self, test_files):
        """Test creating from an xyz file"""
        xyz_path = test_files['molecule_1']
        if not xyz_path.exists():
            pytest.skip(f"Test file {xyz_path} not found")

        mol_obj = MoleculeObject.from_xyz_file(xyz_path)
        assert mol_obj.name == xyz_path.stem
        assert hasattr(mol_obj, "molecule")
        assert len(mol_obj.molecule) > 0  # Should have atoms

    def test_from_cube_file(self, test_files):
        """Test creating from a cube file"""
        cube_path = test_files['scalar_filed_cube']
        if not cube_path.exists():
            pytest.skip(f"Test file {cube_path} not found")

        mol_obj = MoleculeObject.from_cube_file(cube_path)
        assert mol_obj.name == cube_path.stem
        assert hasattr(mol_obj, "molecule")
        assert len(mol_obj.children) == 1
        assert mol_obj.children[0].name == f"{cube_path.stem}_field"


class TestTrajectoryObject:
    """Tests for TrajectoryObject class"""

    def test_trajectory_object_creation(self, test_objects):
        """Test creating a trajectory object"""
        trajectory = test_objects['trajectory']
        traj_obj = TrajectoryObject("test_trajectory", trajectory)

        # Check basic properties
        assert traj_obj.name == "test_trajectory"
        assert traj_obj.trajectory is trajectory
        assert traj_obj.node_type == "trajectory"
        assert traj_obj.data is trajectory
        assert traj_obj.visible is True

        # Check render settings
        assert hasattr(traj_obj, "render_settings")

    def test_trajectory_molecule_children(self, test_objects):
        """Test adding molecules to trajectories"""
        trajectory = test_objects['trajectory']
        molecule = test_objects['molecule_1']

        traj_obj = TrajectoryObject("test_trajectory", trajectory)
        mol_obj = MoleculeObject("new_frame", molecule)

        # Add molecule as child
        success, msg = traj_obj.add_child(mol_obj)
        assert success is True
        assert mol_obj in traj_obj.children

        # Try adding a non-molecule (should fail)
        another_obj = SceneObject("another")
        success, msg = traj_obj.add_child(another_obj)
        assert success is False
        assert "can only have molecules" in msg

        # Try adding with specified position
        mol_obj2 = MoleculeObject("positioned_frame", molecule)
        success, msg = traj_obj.add_child(mol_obj2, position=0)
        assert success is True
        assert traj_obj.children[0] == mol_obj2

    def test_from_xyz_file(self, test_files):
        """Test creating from an xyz file with multiple frames"""
        traj_path = test_files['trajectory']
        if not traj_path.exists():
            pytest.skip(f"Test file {traj_path} not found")

        traj_obj = TrajectoryObject.from_xyz_file(traj_path)

        assert traj_obj.name == traj_path.stem
        assert hasattr(traj_obj, "trajectory")
        assert len(traj_obj.children) > 0

        # Check that frame names are correct pattern
        for child in traj_obj.children:
            assert child.name.startswith("Frame_")
            assert isinstance(child, MoleculeObject)

    def test_trajectory_frame_navigation(self, test_files):
        """Test trajectory frame navigation and animation controls"""
        traj_path = test_files['trajectory']
        if not traj_path.exists():
            pytest.skip(f"Test file {traj_path} not found")

        traj_obj = TrajectoryObject.from_xyz_file(traj_path)
        num_frames = traj_obj.num_frames

        # Test initial state
        assert traj_obj.current_frame == 0
        assert traj_obj.num_frames == num_frames
        assert traj_obj.fps == 10  # Default
        assert traj_obj.loop is True  # Default
        assert traj_obj.is_playing is False

        # Test set_frame
        traj_obj.set_frame(1, send_signals=False)
        assert traj_obj.current_frame == 1
        # Check only frame 1 is visible
        frames = list(traj_obj.children)
        for i, frame in enumerate(frames):
            assert frame.visible == (i == 1)

        # Test next_frame
        traj_obj.next_frame(send_signals=False)
        assert traj_obj.current_frame == 2

        # Test previous_frame
        traj_obj.previous_frame(send_signals=False)
        assert traj_obj.current_frame == 1

        # Test first_frame
        traj_obj.set_frame(5, send_signals=False)
        traj_obj.first_frame(send_signals=False)
        assert traj_obj.current_frame == 0

        # Test last_frame
        traj_obj.last_frame(send_signals=False)
        assert traj_obj.current_frame == num_frames - 1

        # Test looping at end
        traj_obj.loop = True
        traj_obj.next_frame(send_signals=False)
        assert traj_obj.current_frame == 0  # Wrapped around

        # Test looping at start
        traj_obj.previous_frame(send_signals=False)
        assert traj_obj.current_frame == num_frames - 1  # Wrapped around

        # Test non-looping behavior
        traj_obj.loop = False
        traj_obj.last_frame(send_signals=False)
        result = traj_obj.next_frame(send_signals=False)
        assert result is False  # Should fail, at end
        assert traj_obj.current_frame == num_frames - 1  # Should stay at end

        traj_obj.first_frame(send_signals=False)
        result = traj_obj.previous_frame(send_signals=False)
        assert result is False  # Should fail, at start
        assert traj_obj.current_frame == 0  # Should stay at start

    def test_trajectory_playback_controls(self, test_files):
        """Test trajectory play/pause/stop controls"""
        traj_path = test_files['trajectory']
        if not traj_path.exists():
            pytest.skip(f"Test file {traj_path} not found")

        traj_obj = TrajectoryObject.from_xyz_file(traj_path)

        # Test play
        traj_obj.play()
        assert traj_obj.is_playing is True

        # Test pause
        traj_obj.pause()
        assert traj_obj.is_playing is False

        # Test toggle
        traj_obj.toggle_playback()
        assert traj_obj.is_playing is True
        traj_obj.toggle_playback()
        assert traj_obj.is_playing is False

        # Test stop (should reset to first frame)
        traj_obj.set_frame(5, send_signals=False)
        traj_obj.play()
        traj_obj.stop()
        assert traj_obj.is_playing is False
        assert traj_obj.current_frame == 0

        # Test animation_step
        traj_obj.play()
        initial_frame = traj_obj.current_frame
        result = traj_obj.animation_step(send_signals=False)
        assert result is True
        assert traj_obj.current_frame == initial_frame + 1

        # Test animation_step when not playing
        traj_obj.pause()
        frame_before = traj_obj.current_frame
        result = traj_obj.animation_step(send_signals=False)
        assert result is False
        assert traj_obj.current_frame == frame_before  # Should not change

    def test_trajectory_fps_setting(self, test_files):
        """Test FPS setting bounds"""
        traj_path = test_files['trajectory']
        if not traj_path.exists():
            pytest.skip(f"Test file {traj_path} not found")

        traj_obj = TrajectoryObject.from_xyz_file(traj_path)

        # Test normal fps
        traj_obj.fps = 30
        assert traj_obj.fps == 30

        # Test clamping to minimum
        traj_obj.fps = 0
        assert traj_obj.fps == 1

        # Test clamping to maximum
        traj_obj.fps = 100
        assert traj_obj.fps == 60

    def test_trajectory_interpolation(self, test_files):
        """Test smooth interpolation between frames"""
        import numpy as np

        traj_path = test_files['trajectory']
        if not traj_path.exists():
            pytest.skip(f"Test file {traj_path} not found")

        traj_obj = TrajectoryObject.from_xyz_file(traj_path)
        num_frames = traj_obj.num_frames

        if num_frames < 2:
            pytest.skip("Need at least 2 frames for interpolation test")

        # Get positions from frames
        frames = list(traj_obj.children)
        pos0 = frames[0].molecule.positions.copy()
        pos1 = frames[1].molecule.positions.copy()

        # Test interpolation at t=0 (should be first frame)
        interp_pos = traj_obj.get_interpolated_positions(0.0)
        assert interp_pos is not None
        np.testing.assert_array_almost_equal(interp_pos, pos0)

        # Test interpolation at t=1 (should be second frame)
        interp_pos = traj_obj.get_interpolated_positions(1.0)
        np.testing.assert_array_almost_equal(interp_pos, pos1)

        # Test interpolation at t=0.5 (should be halfway between)
        interp_pos = traj_obj.get_interpolated_positions(0.5)
        expected = pos0 * 0.5 + pos1 * 0.5
        np.testing.assert_array_almost_equal(interp_pos, expected)

        # Test get_frame_molecule_at_time
        interp_mol = traj_obj.get_frame_molecule_at_time(0.5)
        assert interp_mol is not None
        np.testing.assert_array_almost_equal(interp_mol.positions, expected)

        # Test clamping for non-looping mode
        traj_obj.loop = False
        interp_pos = traj_obj.get_interpolated_positions(num_frames + 10)
        last_pos = frames[-1].molecule.positions.copy()
        np.testing.assert_array_almost_equal(interp_pos, last_pos)

        # Test looping mode
        traj_obj.loop = True
        # t = num_frames should wrap to t = 0 (modulo num_frames)
        interp_pos = traj_obj.get_interpolated_positions(float(num_frames))
        np.testing.assert_array_almost_equal(interp_pos, pos0)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
