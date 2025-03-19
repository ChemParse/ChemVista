import pytest
import pathlib
import numpy as np
from chemvista.scene_manager import SceneManager
from chemvista.tree_structure import TreeNode, TreeSignals
from nx_ase import Molecule, ScalarField
import pyvista as pv
from PyQt5.QtCore import QObject
from chemvista.scene_objects import (
    SceneObject, MoleculeObject, ScalarFieldObject, TrajectoryObject
)
from chemvista.renderer.render_settings import MoleculeRenderSettings
import logging


@pytest.fixture
def signals(qtbot):
    """Create TreeSignals for testing"""
    # Using qtbot ensures we have a QApplication running
    return TreeSignals()


@pytest.fixture
def scene(test_plotter, signals):
    """Create SceneManager with test plotter and signals"""
    manager = SceneManager(tree_signals=signals)

    manager.plotter = test_plotter
    return manager


def test_load_molecule(scene: SceneManager, test_files):
    """Test loading molecule from XYZ file"""
    uuid = scene.load_xyz(test_files['molecule_1'])
    assert len(scene.root_objects) == 1
    obj = scene.get_object_by_uuid(uuid)
    assert isinstance(obj, MoleculeObject)
    assert len(obj.molecule.positions) > 0


def test_load_cube_as_molecule(scene: SceneManager, test_files):
    """Test loading cube file as molecule with field"""
    uuid = scene.load_molecule_from_cube(test_files['scalar_filed_cube'])
    assert len(scene.root_objects) == 1  # Only one root object (molecule)

    # Check molecule
    mol_obj = scene.get_object_by_uuid(uuid)
    assert isinstance(mol_obj, MoleculeObject)

    # Check field (should be a child of the molecule)
    assert len(mol_obj.children) == 1
    field_obj = mol_obj.children[0]
    assert isinstance(field_obj, ScalarFieldObject)
    assert field_obj.parent == mol_obj


def test_load_cube_as_field(scene: SceneManager, test_files):
    """Test loading cube file as scalar field only"""
    uuid = scene.load_scalar_field_from_cube(test_files['scalar_filed_cube'])
    assert len(scene.root_objects) == 1
    obj = scene.get_object_by_uuid(uuid)
    assert isinstance(obj, ScalarFieldObject)


def test_visibility_control(scene: SceneManager, test_files):
    """Test object visibility control"""
    uuid = scene.load_xyz(test_files['molecule_1'])
    obj = scene.get_object_by_uuid(uuid)
    assert obj.visible  # Should be visible by default

    # Directly update visibility in the object without using the plotter
    success = scene.root.set_visibility(uuid, False)
    assert success
    assert not obj.visible

    scene.root.set_visibility(uuid, True)
    assert obj.visible


def test_render_molecule(scene: SceneManager, test_files, test_plotter):
    """Test molecule rendering"""
    uuid = scene.load_xyz(test_files['molecule_1'])
    scene.render(test_plotter)
    # Just verify no exceptions are raised
    assert True


def test_render_scalar_field(scene: SceneManager, test_files, test_plotter):
    """Test scalar field rendering"""
    uuid = scene.load_scalar_field_from_cube(test_files['scalar_filed_cube'])
    scene.render(test_plotter)
    # Just verify no exceptions are raised
    assert True


def test_settings_update(scene: SceneManager, test_files):
    """Test updating render settings"""
    uuid = scene.load_xyz(test_files['molecule_1'])
    obj = scene.get_object_by_uuid(uuid)

    # Modify settings
    obj.render_settings.show_hydrogens = False
    obj.render_settings.show_numbers = True

    # Verify changes
    assert not obj.render_settings.show_hydrogens
    assert obj.render_settings.show_numbers


def test_tree_signals(scene: SceneManager, signals):
    """Test TreeSignals"""
    assert isinstance(signals, QObject)
    assert hasattr(signals, 'node_added')
    assert hasattr(signals, 'node_removed')
    assert hasattr(signals, 'node_changed')
    assert hasattr(signals, 'visibility_changed')
    assert hasattr(signals, 'tree_structure_changed')


def test_signals_emission(scene: SceneManager, signals, test_files):
    """Test that signals are properly emitted"""
    # Track signal emissions
    added_signals = []
    visibility_signals = []

    signals.node_added.connect(lambda x: added_signals.append(x))
    signals.visibility_changed.connect(
        lambda x, v: visibility_signals.append((x, v)))

    # Load molecule should emit node_added
    uuid = scene.load_xyz(test_files['molecule_1'])
    assert len(added_signals) >= 1
    assert uuid in added_signals

    # Toggle visibility should emit visibility_changed
    # Instead of using scene.set_visibility which tries to update the plotter,
    # use the root's set_visibility method directly
    scene.root.set_visibility(uuid, False)
    assert len(visibility_signals) >= 1
    assert (uuid, False) in visibility_signals


class TestSceneManager:
    """Tests for the SceneManager class"""

    @pytest.fixture
    def signals(self, qtbot):
        """Create TreeSignals for testing"""
        # Using qtbot ensures we have a QApplication running
        return TreeSignals()

    @pytest.fixture
    def scene(self, signals):
        """Create a scene manager for testing"""
        return SceneManager(tree_signals=signals)

    def test_initialization(self, scene):
        """Test SceneManager initialization"""
        assert scene.root is not None
        assert isinstance(scene.root, TreeNode)
        assert scene.root.node_type == "root"  # Verify the node type
        assert len(scene.root_objects) == 0
        assert scene.plotter is None

    def test_root_is_not_scene_object(self, scene):
        """Verify that root is a TreeNode but not a SceneObject"""
        assert isinstance(scene.root, TreeNode)
        assert not isinstance(scene.root, SceneObject)

    def test_load_xyz(self, scene, test_files):
        """Test loading XYZ file"""
        uuid = scene.load_xyz(test_files['molecule_1'])

        obj = scene.get_object_by_uuid(uuid)
        assert isinstance(obj, MoleculeObject)
        assert obj.name == pathlib.Path(test_files['molecule_1']).stem
        assert len(scene.root_objects) == 1

    def test_load_xyz_trajectory(self, scene, test_files):
        """Test loading XYZ trajectory file"""
        # Skip if no trajectory file available
        if 'trajectory' not in test_files:
            pytest.skip("No trajectory test file available")

        uuid = scene.load_xyz(test_files['trajectory'])

        # Get the loaded object
        obj = scene.get_object_by_uuid(uuid)

        # Check if it's a trajectory object
        if isinstance(obj, TrajectoryObject):
            # If it's a trajectory, verify it has children
            assert len(obj.children) > 0
            # All children should be molecule objects
            assert all(isinstance(child, MoleculeObject)
                       for child in obj.children)
        else:
            # If not a trajectory, it should be a molecule
            assert isinstance(obj, MoleculeObject)

    def test_load_molecule_from_cube(self, scene, test_files):
        """Test loading molecule from cube file"""
        cube_file = test_files['scalar_filed_cube']

        uuid = scene.load_molecule_from_cube(cube_file)

        mol_obj = scene.get_object_by_uuid(uuid)
        assert isinstance(mol_obj, MoleculeObject)
        assert mol_obj.name == pathlib.Path(cube_file).stem

        # Should have a scalar field child
        assert len(mol_obj.children) == 1
        field_obj = mol_obj.children[0]
        assert isinstance(field_obj, ScalarFieldObject)
        assert field_obj.name.endswith('_field')

    def test_render(self, scene, test_files, test_plotter):
        """Test rendering objects"""
        # Load an object
        scene.load_xyz(test_files['molecule_1'])

        # Render it
        plotter = scene.render(test_plotter)

        # Check that something was rendered
        assert plotter.renderer.GetActors().GetNumberOfItems() > 0


def test_load_trajectory(scene: SceneManager, test_files):
    """Test loading a trajectory file"""
    # Skip if no trajectory file available
    if 'trajectory' not in test_files:
        pytest.skip("No trajectory test file available")

    uuid = scene.load_xyz(test_files['trajectory'])

    # Get the loaded object
    obj = scene.get_object_by_uuid(uuid)

    # If it's a trajectory, check its children
    if isinstance(obj, TrajectoryObject):
        # Children should all be molecules
        assert len(obj.children) > 0
        assert all(isinstance(child, MoleculeObject) for child in obj.children)
    else:
        # If it's just a molecule, that's fine too
        assert isinstance(obj, MoleculeObject)


def test_directory_creation_removed(scene):
    """Test that directory creation has been removed"""
    with pytest.raises(AttributeError):
        scene.create_directory("Test Directory")


def test_object_settings_update(scene: SceneManager, signals, test_files):
    """Test updating object settings"""
    uuid = scene.load_xyz(test_files['molecule_1'])
    obj = scene.get_object_by_uuid(uuid)

    # Capture signal
    settings_changed = []
    signals.render_changed.connect(lambda uuid: settings_changed.append(uuid))

    # Update settings
    new_settings = MoleculeRenderSettings(alpha=0.5)
    scene.update_settings(uuid, new_settings)

    # Check signal was emitted
    assert len(settings_changed) > 0
    assert settings_changed[0] == uuid

    # Check settings were updated
    obj = scene.get_object_by_uuid(uuid)
    assert obj.render_settings.alpha == 0.5


def test_tree_formatting(scene: SceneManager, test_files):
    """Test tree formatting function"""
    # Load a molecule
    mol_uuid = scene.load_xyz(test_files['molecule_1'])

    # Get tree representation
    tree_str = scene.root.format_tree()

    # Basic checks
    assert "Tree Structure:" in tree_str
    assert "Scene" in tree_str
    assert scene.get_object_by_uuid(mol_uuid).name in tree_str


def test_log_tree_changes(scene: SceneManager, test_files, caplog):
    """Test logging tree changes"""
    # Configure logging to capture at INFO level
    caplog.set_level(logging.INFO)

    # Load a molecule
    scene.load_xyz(test_files['molecule_1'])

    # Log tree changes
    scene.log_tree_changes("Test Message")

    # Check log
    assert "Test Message" in caplog.text
    assert "Tree Structure:" in caplog.text


def test_node_path_operations(scene: SceneManager, test_files):
    """Test node path operations"""
    # Load a molecule with a scalar field
    mol_uuid = scene.load_molecule_from_cube(test_files['scalar_filed_cube'])
    mol_obj = scene.get_object_by_uuid(mol_uuid)
    field_obj = mol_obj.children[0]

    # Check paths
    assert str(mol_obj.path) == f'/Scene/{mol_obj.name}'
    assert str(field_obj.path) == f'/Scene/{mol_obj.name}/{field_obj.name}'

    # Check parent path relationship
    assert field_obj.path.parent().name == mol_obj.name


def test_find_by_path(scene: SceneManager, test_files):
    """Test finding nodes by path"""
    # Load a molecule with a scalar field
    mol_uuid = scene.load_molecule_from_cube(test_files['scalar_filed_cube'])
    mol_obj = scene.get_object_by_uuid(mol_uuid)
    field_obj = mol_obj.children[0]

    # Find by path
    found_mol = scene.root.get_by_path(str(mol_obj.path))
    found_field = scene.root.get_by_path(str(field_obj.path))

    # Verify found objects
    assert found_mol == mol_obj
    assert found_field == field_obj


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
