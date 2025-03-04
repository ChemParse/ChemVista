import pytest
from PyQt5.QtWidgets import QApplication
from pytestqt.plugin import QtBot
import sys
import pyvista as pv
import vtk
import pathlib
from chemvista.main_window import ChemVistaApp


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
        'xyz': base_path / 'mpf_motor.xyz',
        'cube': base_path / 'C2H4.eldens.cube',
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
