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
    uuid = chem_vista_app.scene_manager.load_molecule(test_files['xyz'])[0]
    obj = chem_vista_app.scene_manager.get_object_by_uuid(uuid)
    assert obj is not None
    assert hasattr(obj, 'molecule')
    assert len(obj.molecule.positions) > 0


def test_load_cube_as_scalar_field(chem_vista_app, test_files):
    """Test loading a cube file as scalar field only"""
    uuid = chem_vista_app.scene_manager.load_scalar_field(test_files['cube'])
    assert len(chem_vista_app.scene_manager.objects) == 1
    obj = chem_vista_app.scene_manager.get_object_by_uuid(uuid)
    assert hasattr(obj, 'scalar_field')
    assert obj.scalar_field is not None


def test_load_cube_as_molecule(chem_vista_app, test_files):
    """Test loading a cube file as molecule with field"""
    uuids = chem_vista_app.scene_manager.load_molecule_from_cube(
        test_files['cube'])
    assert len(uuids) == 2  # Should be molecule and field

    # First object should be molecule
    mol_obj = chem_vista_app.scene_manager.get_object_by_uuid(uuids[0])
    assert hasattr(mol_obj, 'molecule')

    # Second object should be field
    field_obj = chem_vista_app.scene_manager.get_object_by_uuid(uuids[1])
    assert hasattr(field_obj, 'scalar_field')


def test_load_trajectory(chem_vista_app, test_files):
    """Test loading a trajectory XYZ file"""
    # Skip if file doesn't exist
    if not test_files['trajectory'].exists():
        pytest.skip(f"Trajectory file not found: {test_files['trajectory']}")

    uuids = chem_vista_app.scene_manager.load_molecule(
        test_files['trajectory'])
    assert len(uuids) > 1  # Should be multiple frames

    # Verify all objects loaded correctly
    for uuid in uuids:
        obj = chem_vista_app.scene_manager.get_object_by_uuid(uuid)
        assert obj is not None
        assert hasattr(obj, 'molecule')
        assert len(obj.molecule.positions) > 0


def test_load_and_render(chem_vista_app, test_files):
    """Test loading and rendering a file"""
    uuid = chem_vista_app.scene_manager.load_molecule(test_files['xyz'])[0]

    # Call the scene_manager render method directly instead of on the app
    chem_vista_app.scene_manager.render()
    assert chem_vista_app.scene_manager.plotter is not None


def test_invalid_xyz_file(chem_vista_app):
    """Test loading a non-existent XYZ file"""
    with pytest.raises(Exception):
        chem_vista_app.scene_manager.load_molecule(
            pathlib.Path('nonexistent.xyz'))


def test_invalid_cube_file(chem_vista_app):
    """Test loading a non-existent cube file"""
    with pytest.raises(Exception):
        chem_vista_app.scene_manager.load_scalar_field(
            pathlib.Path('nonexistent.cube'))
