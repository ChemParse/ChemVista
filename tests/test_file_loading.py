import pytest
import pathlib
from PyQt5.QtWidgets import QApplication
import sys
from chemvista.main_window import ChemVistaApp
from nx_ase import Molecule, ScalarField

# Create QApplication instance for testing
app = QApplication(sys.argv)


@pytest.fixture
def test_files():
    base_path = pathlib.Path(__file__).parent / 'data'
    return {
        'xyz': base_path / 'mpf_motor.xyz',
        'cube': base_path / 'C2H4.eldens.cube'
    }


@pytest.fixture
def chem_vista_app():
    app = ChemVistaApp(debug=False)
    yield app
    app.close()


def test_load_xyz_file(chem_vista_app, test_files):
    """Test loading an XYZ file"""
    chem_vista_app.scene_manager.load_molecule(test_files['xyz'])
    assert len(chem_vista_app.scene_manager.objects) == 1
    obj = chem_vista_app.scene_manager.objects[0]
    assert isinstance(obj.molecule, Molecule)


def test_load_cube_as_molecule(chem_vista_app, test_files):
    """Test loading a cube file as molecule with field"""
    names = chem_vista_app.scene_manager.load_molecule_from_cube(
        test_files['cube'])
    assert len(names) == 2
    assert len(chem_vista_app.scene_manager.objects) == 2


def test_load_cube_as_scalar_field(chem_vista_app, test_files):
    """Test loading a cube file as scalar field only"""
    name = chem_vista_app.scene_manager.load_scalar_field(test_files['cube'])
    assert len(chem_vista_app.scene_manager.objects) == 1
    obj = chem_vista_app.scene_manager.get_object_by_name(name)
    assert isinstance(obj.scalar_field, ScalarField)


def test_invalid_xyz_file(chem_vista_app):
    """Test loading a non-existent XYZ file"""
    with pytest.raises(Exception):
        chem_vista_app._load_molecule_from_xyz(pathlib.Path('nonexistent.xyz'))


def test_invalid_cube_file(chem_vista_app):
    """Test loading a non-existent cube file"""
    with pytest.raises(Exception):
        chem_vista_app._load_scalar_field(pathlib.Path('nonexistent.cube'))
