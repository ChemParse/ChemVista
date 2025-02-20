import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QPushButton, QFileDialog
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
import pathlib
from chemvista.main_window import ChemVistaApp
from chemvista.scene_objects import SceneManager


@pytest.fixture
def test_files():
    base_path = pathlib.Path(__file__).parent / 'data'
    return {
        'xyz': base_path / 'mpf_motor.xyz',
        'cube': base_path / 'C2H4.eldens.cube'
    }


@pytest.fixture
def app(qapp, test_plotter):
    """Create application instance with a fresh SceneManager and plotter"""
    scene = SceneManager()
    scene.plotter = test_plotter
    window = ChemVistaApp(scene_manager=scene, debug=False)
    yield window
    window.close()


def test_file_open_xyz(app, test_files, monkeypatch):
    """Test opening XYZ file through GUI"""
    def mock_get_filename(*args, **kwargs):
        return str(test_files['xyz']), 'XYZ files (*.xyz)'
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', mock_get_filename)
    app.open_file()
    assert len(app.scene_manager.objects) == 1


def test_file_open_cube(app, test_files, monkeypatch):
    """Test opening cube file through GUI"""
    def mock_get_filename(*args, **kwargs):
        return str(test_files['cube']), 'Cube files (*.cube)'

    def mock_question(*args, **kwargs):
        return QMessageBox.Yes  # This simulates clicking "As Molecule + Field"

    monkeypatch.setattr(QFileDialog, 'getOpenFileName', mock_get_filename)
    monkeypatch.setattr(QMessageBox, 'question', mock_question)

    app.open_file()
    assert len(app.scene_manager.objects) == 2


def test_visibility_toggle(app, test_files, test_plotter):
    """Test visibility toggle in GUI"""
    app.scene_manager.load_molecule(test_files['xyz'])
    obj = app.scene_manager.objects[0]
    assert obj.visible

    app.on_visibility_changed(0, False)
    assert not obj.visible

    # Test rendering after visibility change
    app.scene_manager.render(test_plotter)


def test_settings_dialog(app, test_files, qtbot):
    """Test settings dialog interaction"""
    # Load a molecule
    app.scene_manager.load_molecule(test_files['xyz'])

    # Open settings dialog and ensure it appears
    def check_dialog():
        app.on_settings_requested(0)
        dialog = app.findChild(QDialog)
        if dialog is not None:
            # Click Save button when dialog is found
            save_button = dialog.findChild(QPushButton, "Save")
            if save_button is not None:
                qtbot.mouseClick(save_button, Qt.LeftButton)
                return True
        return False

    # Try multiple times with delay
    qtbot.waitUntil(check_dialog, timeout=1000)

    # Verify settings were updated (object_changed signal was emitted)
    assert len(app.scene_manager.objects) > 0  # Just verify the object exists


def test_object_list(app, test_files):
    """Test object list widget"""
    # Load some objects
    app.scene_manager.load_molecule(test_files['xyz'])
    app.scene_manager.load_scalar_field(test_files['cube'])

    # Check object list widget
    assert app.object_list_widget.count() == 2


def test_scene_manager_integration(app):
    """Test that GUI properly integrates with SceneManager"""
    assert app.scene_manager is not None
    assert isinstance(app.scene_manager, SceneManager)
    assert app.scene_manager.plotter == app.plotter


def test_object_list_sync(app, test_files):
    """Test that object list stays in sync with SceneManager"""
    initial_count = app.object_list_widget.count()

    # Add object through SceneManager
    name = app.scene_manager.load_molecule(test_files['xyz'])

    # Check that GUI updated
    assert app.object_list_widget.count() == initial_count + 1

    # Toggle visibility
    app.scene_manager.set_visibility(name, False)
    # Would need to check if GUI reflects visibility change
