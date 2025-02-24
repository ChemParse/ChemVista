import pytest
import pathlib
import numpy as np
from chemvista.scene_objects import SceneManager
from nx_ase import Molecule, ScalarField
import pyvista as pv
from PyQt5.QtCore import QObject


@pytest.fixture
def test_files():
    base_path = pathlib.Path(__file__).parent / 'data'
    return {
        'xyz': base_path / 'mpf_motor.xyz',
        'cube': base_path / 'C2H4.eldens.cube'
    }


@pytest.fixture
def scene(test_plotter):
    """Create SceneManager with test plotter"""
    manager = SceneManager()
    manager.plotter = test_plotter
    return manager


def test_load_molecule(scene, test_files):
    """Test loading molecule from XYZ file"""
    name = scene.load_molecule(test_files['xyz'])[0]
    assert len(scene.objects) == 1
    obj = scene.get_object_by_name(name)
    assert isinstance(obj.molecule, Molecule)
    assert len(obj.molecule.positions) > 0


def test_load_cube_as_molecule(scene, test_files):
    """Test loading cube file as molecule with field"""
    names = scene.load_molecule_from_cube(test_files['cube'])
    assert len(names) == 2  # Should create molecule and field
    assert len(scene.objects) == 2

    # Check molecule
    mol_obj = scene.get_object_by_name(names[0])
    assert isinstance(mol_obj.molecule, Molecule)

    # Check field
    field_obj = scene.get_object_by_name(names[1])
    assert isinstance(field_obj.scalar_field, ScalarField)


def test_load_cube_as_field(scene, test_files):
    """Test loading cube file as scalar field only"""
    name = scene.load_scalar_field(test_files['cube'])
    assert len(scene.objects) == 1
    obj = scene.get_object_by_name(name)
    assert isinstance(obj.scalar_field, ScalarField)


def test_visibility_control(scene, test_files):
    """Test object visibility control"""
    name = scene.load_molecule(test_files['xyz'])[0]
    obj = scene.get_object_by_name(name)
    assert obj.visible  # Should be visible by default

    scene.set_visibility(name, False)
    assert not obj.visible

    scene.set_visibility(name, True)
    assert obj.visible


def test_render_molecule(scene, test_files, test_plotter):
    """Test molecule rendering"""
    name = scene.load_molecule(test_files['xyz'])
    scene.render(test_plotter)
    # Just verify no exceptions are raised
    assert True


def test_render_scalar_field(scene, test_files, test_plotter):
    """Test scalar field rendering"""
    name = scene.load_scalar_field(test_files['cube'])
    scene.render(test_plotter)
    # Just verify no exceptions are raised
    assert True


def test_settings_update(scene, test_files):
    """Test updating render settings"""
    name = scene.load_molecule(test_files['xyz'])[0]
    obj = scene.get_object_by_name(name)

    # Modify settings
    obj.render_settings.show_hydrogens = False
    obj.render_settings.show_numbers = True

    # Verify changes
    assert not obj.render_settings.show_hydrogens
    assert obj.render_settings.show_numbers


def test_scene_manager_signals(scene):
    """Test SceneManager signals"""
    assert isinstance(
        scene, QObject), "SceneManager should inherit from QObject"
    assert hasattr(scene, 'object_added'), "Should have object_added signal"
    assert hasattr(
        scene, 'object_removed'), "Should have object_removed signal"
    assert hasattr(
        scene, 'object_changed'), "Should have object_changed signal"
    assert hasattr(
        scene, 'visibility_changed'), "Should have visibility_changed signal"


def test_signals_emission(scene, test_files):
    """Test that signals are properly emitted"""
    # Track signal emissions
    added_signals = []
    visibility_signals = []

    scene.object_added.connect(lambda x: added_signals.append(x))
    scene.visibility_changed.connect(
        lambda x, v: visibility_signals.append((x, v)))

    # Load molecule should emit object_added
    name = scene.load_molecule(test_files['xyz'])[0]
    assert len(added_signals) == 1
    assert added_signals[0] == name

    # Toggle visibility should emit visibility_changed
    scene.set_visibility(name, False)
    assert len(visibility_signals) == 1
    assert visibility_signals[0] == (name, False)


def test_render_with_settings(scene, test_files):
    """Test rendering with custom settings"""
    name = scene.load_molecule(test_files['xyz'])[0]

    obj = scene.get_object_by_name(name)

    # Modify settings
    obj.render_settings.show_hydrogens = False
    obj.render_settings.show_numbers = True

    # Render with modified settings
    plotter = scene.render(off_screen=True)
    assert plotter is not None
    assert len(plotter.renderer.actors) > 0


def test_multiple_objects_render(scene, test_files):
    """Test rendering multiple objects together"""
    # Load both molecule and scalar field
    mol_names = scene.load_molecule_from_cube(test_files['cube'])
    assert len(mol_names) == 2  # Should have molecule and field

    # Render all objects
    plotter = scene.render(off_screen=True)
    assert len(plotter.renderer.actors) > 0
