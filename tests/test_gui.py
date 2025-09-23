import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QPushButton, QFileDialog, QAction
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
import pathlib
from chemvista.gui.main_window import ChemVistaApp
from chemvista.scene_manager import SceneManager


@pytest.fixture
def test_files():
    base_path = pathlib.Path(__file__).parent / 'data'
    return {
        'xyz': base_path / 'mpf_motor.xyz',
        'cube': base_path / 'C2H4.eldens.cube'
    }


@pytest.fixture
def app(qapp):
    """Create ChemVistaApp instance for testing with mocked GUI components"""
    # Use the same mock approach as chem_vista_app
    from unittest.mock import patch
    from PyQt5.QtWidgets import QWidget
    from unittest.mock import MagicMock
    
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
    
    with patch('chemvista.gui.scene.QtInteractor', MockQtInteractor):
        app = ChemVistaApp()
        yield app
        # Cleanup after test
        try:
            if hasattr(app, 'scene_manager') and app.scene_manager.plotter is not None:
                # Don't try to close the mock plotter
                pass
        except (AttributeError, RuntimeError):
            pass


def test_app_creation(app):
    """Test that the application is created correctly"""
    assert hasattr(app, 'scene_manager')
    # Changed from object_tree_widget
    assert hasattr(app, 'object_list_widget')


def test_scene_manager_integration(app):
    """Test that GUI properly integrates with SceneManager"""
    assert app.scene_manager is not None
    assert isinstance(app.scene_manager, SceneManager)
    assert app.scene_manager.plotter == app.plotter
