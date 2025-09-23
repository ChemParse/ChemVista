import pytest
from chemvista.scene_manager import SceneManager
from chemvista.renderer.render_settings import MoleculeRenderSettings, ScalarFieldRenderSettings


@pytest.fixture
def scene_with_objects(test_plotter, test_files):
    """Create a scene with molecule and scalar field objects"""
    scene = SceneManager()
    scene.plotter = test_plotter
    mol_obj = scene.load_xyz(test_files['molecule_1'])
    field_obj = scene.load_molecule_from_cube(test_files['scalar_filed_cube'])
    return scene, mol_obj, field_obj


def test_molecule_settings_update(scene_with_objects):
    scene, mol_obj, _ = scene_with_objects

    # Create new settings
    settings = MoleculeRenderSettings()
    settings.show_hydrogens = False
    settings.show_numbers = True

    # Update settings
    scene.update_settings(mol_obj.uuid, settings)

    # Verify settings were applied
    assert not mol_obj.render_settings.show_hydrogens
    assert mol_obj.render_settings.show_numbers


def test_scalar_field_settings_update(scene_with_objects):
    scene, _, field_obj = scene_with_objects
    
    # The field_obj from the fixture is actually a MoleculeObject with ScalarFieldObject children
    # Get the actual scalar field object (the child)
    field_obj = field_obj.children[0]

    # Create new settings
    settings = ScalarFieldRenderSettings()
    settings.opacity = 0.7
    settings.isosurface_value = 0.2
    settings.color = 'red'

    # Update settings
    scene.update_settings(field_obj.uuid, settings)

    # Verify settings were applied
    assert field_obj.render_settings.opacity == 0.7
    assert field_obj.render_settings.isosurface_value == 0.2
    assert field_obj.render_settings.color == 'red'
