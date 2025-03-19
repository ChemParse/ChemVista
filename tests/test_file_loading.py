import pytest
import pathlib
from PyQt5.QtWidgets import QApplication
import sys
from chemvista.gui.main_window import ChemVistaApp
from nx_ase import Molecule, ScalarField
import numpy as np

# Create QApplication instance for testing
app = QApplication(sys.argv)


@pytest.fixture
def test_files():
    base_path = pathlib.Path(__file__).parent / 'data'
    return {
        'xyz': base_path / 'mpf_motor.xyz',
        'cube': base_path / 'C2H4.eldens.cube',
        'trajectory': base_path / 'mpf_motor_trajectory.xyz'
    }


@pytest.fixture
def chem_vista_app():
    app = ChemVistaApp()
    yield app
    app.close()


def test_load_xyz(chem_vista_app, test_files):
    """Test loading an XYZ file"""

    uuid = chem_vista_app.scene_manager.load_xyz(test_files['xyz'])
    assert len(chem_vista_app.scene_manager.root.children) == 1
    obj = chem_vista_app.scene_manager.get_object_by_uuid(uuid)
    assert obj is not None
    assert hasattr(obj, 'molecule')
    assert len(obj.molecule.positions) > 0


def test_load_cube_as_scalar_field(chem_vista_app, test_files):
    """Test loading a cube file as scalar field only"""
    uuid = chem_vista_app.scene_manager.load_scalar_field_from_cube(
        test_files['cube'])
    assert len(chem_vista_app.scene_manager.root.children) == 1
    obj = chem_vista_app.scene_manager.get_object_by_uuid(uuid)
    assert hasattr(obj, 'scalar_field')
    assert obj.scalar_field is not None


def test_load_cube_as_molecule(chem_vista_app, test_files):
    """Test loading a cube file as molecule with field"""
    uuid = chem_vista_app.scene_manager.load_molecule_from_cube(
        test_files['cube'])

    assert len(chem_vista_app.scene_manager.root.children) == 1
    molecule_obj = chem_vista_app.scene_manager.get_object_by_uuid(uuid)
    assert hasattr(molecule_obj, 'molecule')
    children = molecule_obj.children
    assert len(children) == 1
    scalar_field = children[0]
    assert hasattr(scalar_field, 'scalar_field')
    assert scalar_field.scalar_field is not None


def test_load_trajectory(chem_vista_app, test_files):
    """Test loading a trajectory XYZ file"""
    # Skip if file doesn't exist
    if not test_files['trajectory'].exists():
        pytest.skip(f"Trajectory file not found: {test_files['trajectory']}")

    uuid = chem_vista_app.scene_manager.load_xyz(
        test_files['trajectory'])

    trajectory_obj = chem_vista_app.scene_manager.get_object_by_uuid(uuid)
    assert trajectory_obj is not None
    assert hasattr(trajectory_obj, 'trajectory')
    assert len(trajectory_obj.trajectory) == 10
    assert len(trajectory_obj.children) == 10

    assert all(hasattr(obj, 'molecule') for obj in trajectory_obj.children)


def test_load_and_render(chem_vista_app, test_files):
    """Test loading and rendering a file"""
    uuid = chem_vista_app.scene_manager.load_xyz(test_files['xyz'])

    # Call the scene_manager render method directly instead of on the app
    chem_vista_app.scene_manager.render()
    assert chem_vista_app.scene_manager.plotter is not None


def test_invalid_xyz_file(chem_vista_app):
    """Test loading a non-existent XYZ file"""
    with pytest.raises(Exception):
        chem_vista_app.scene_manager.load_xyz(
            pathlib.Path('nonexistent.xyz'))


def test_invalid_cube_file(chem_vista_app):
    """Test loading a non-existent cube file"""
    with pytest.raises(Exception):
        chem_vista_app.scene_manager.load_scalar_field(
            pathlib.Path('nonexistent.cube'))
