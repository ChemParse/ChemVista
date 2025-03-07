import pytest
from PyQt5.QtWidgets import QApplication
from pytestqt.plugin import QtBot
import sys
import pyvista as pv
import vtk
import pathlib
import tempfile
from chemvista.gui.main_window import ChemVistaApp
from nx_ase import Molecule
from nx_ase import Trajectory
from nx_ase import ScalarField


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for the entire test session"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def qtbot(qapp):
    """Create a QtBot instance"""
    return QtBot(qapp)


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment for each test"""
    # Use offscreen rendering for tests
    pv.OFF_SCREEN = True

    # Create a new VTK output window to suppress errors
    output_window = vtk.vtkFileOutputWindow()
    output_window.SetFileName("/dev/null")
    vtk.vtkOutputWindow.SetInstance(output_window)

    # Use dummy rendering backend for tests
    plotter = pv.Plotter(off_screen=True)
    yield plotter
    try:
        plotter.close()
    except (AttributeError, RuntimeError):
        pass


@pytest.fixture
def test_plotter():
    """Provide a fresh plotter for each test"""
    plotter = pv.Plotter(off_screen=True)
    yield plotter
    try:
        plotter.close()
    except (AttributeError, RuntimeError):
        pass


@pytest.fixture
def test_files():
    """Shared test files fixture"""
    base_path = pathlib.Path(__file__).parent / 'data'
    return {
        'molecule_1': base_path / 'mpf_motor.xyz',
        'molecule_2': base_path / 'C6H6.xyz',
        'molecule_3': base_path / 'mpf_motor.xyz',
        'scalar_filed_cube': base_path / 'C2H4.eldens.cube',
        'trajectory': base_path / 'mpf_motor_trajectory.xyz'
    }


@pytest.fixture
def chem_vista_app(qapp):
    """Create ChemVistaApp instance for testing"""
    app = ChemVistaApp()
    yield app
    # Clean up
    try:
        if app.scene_manager.plotter is not None:
            app.scene_manager.plotter.close()
    except (AttributeError, RuntimeError):
        pass


@pytest.fixture
def test_objects(test_files):
    """Create test objects from test files"""

    molecule_1 = Molecule.load(test_files['molecule_1'])
    molecule_2 = Molecule.load(test_files['molecule_2'])
    molecule_3 = Molecule.load(test_files['molecule_3'])

    scalar_field = ScalarField.load_cube(
        test_files['scalar_filed_cube'])

    trajectory = Trajectory.load(test_files['trajectory'])

    # Create a molecule with scalar field
    molecule_with_field = Molecule.load_from_cube(
        test_files['scalar_filed_cube'])

    return {
        'molecule_1': molecule_1,
        'molecule_2': molecule_2,
        'molecule_3': molecule_3,
        'scalar_field': scalar_field,
        'trajectory': trajectory,
        'molecule_with_field': molecule_with_field
    }


@pytest.fixture
def ensure_trajectory_file():
    """Create a guaranteed multi-frame trajectory file for testing"""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as tmp:
        filepath = pathlib.Path(tmp.name)

    # Create a simple trajectory with two frames
    mol1 = Molecule(symbols=['C', 'O'],
                    positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.2]])

    mol2 = Molecule(symbols=['C', 'O'],
                    positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.3]])

    # Save to temporary file
    traj = Trajectory([mol1, mol2])
    traj.save(filepath)

    yield filepath

    # Clean up
    filepath.unlink(missing_ok=True)
