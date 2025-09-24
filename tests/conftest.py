import pytest
from PyQt5.QtWidgets import QApplication, QWidget
from pytestqt.plugin import QtBot
import sys
import pyvista as pv
import vtk
import pathlib
import tempfile
from chemvista.gui.main_window import ChemVistaApp
from chemvista.gui import setup_qt_environment
from chemvista.scene_manager import SceneManager
from nx_ase import Molecule
from nx_ase import Trajectory
from nx_ase import ScalarField
from unittest.mock import MagicMock, patch
import os

# Always use offscreen rendering for tests to avoid Qt display issues
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

# Also setup Qt environment for cases where offscreen isn't enough
setup_qt_environment()


@pytest.fixture(scope="session", autouse=True)
def setup_qt_for_tests():
    """Ensure Qt environment is set up before any tests run"""
    # Force offscreen mode for all tests to avoid display issues
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    # Also ensure Qt environment is properly set up
    setup_qt_environment()

# Configure PyVista for headless testing
pv.OFF_SCREEN = True


class MockQtInteractor(QWidget):
    """Mock QtInteractor that behaves like a QWidget but doesn't create VTK render window"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # Mock the plotter methods that might be called
        self.update = MagicMock()
        self.clear = MagicMock()
        self.add_mesh = MagicMock()
        self.camera = MagicMock()
        self.show = MagicMock()
        self.close = MagicMock()
        self.reset_camera = MagicMock()
        self.set_background = MagicMock()


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
    """Create a test plotter that can be used in tests without rendering"""
    plotter = pv.Plotter(off_screen=True)

    # Mock the update method to prevent rendering pipeline errors in tests
    original_update = plotter.update
    plotter.update = MagicMock(side_effect=lambda: None)

    return plotter


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
    """Create ChemVistaApp instance for testing with mocked GUI components"""
    # Mock the QtInteractor to avoid X11 issues
    with patch('chemvista.gui.scene.QtInteractor', MockQtInteractor):
        # Create the app - this will use the mocked QtInteractor
        app = ChemVistaApp()
        
        yield app
        
        # Clean up
        try:
            if hasattr(app, 'scene_manager') and app.scene_manager.plotter is not None:
                # Don't try to close the mock plotter
                pass
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
