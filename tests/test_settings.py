import pytest
from chemvista.scene_objects import SceneManager
from chemvista.render_settings import RenderSettings, ScalarFieldRenderSettings


@pytest.fixture
def scene_with_objects(test_files):
    scene = SceneManager()
    mol_name = scene.load_molecule(test_files['xyz'])[0]
    field_names = scene.load_molecule_from_cube(test_files['cube'])
    return scene, mol_name, field_names


def test_molecule_settings_update(scene_with_objects):
    scene, mol_name, _ = scene_with_objects

    # Get molecule object
    mol_obj = scene.get_object_by_name(mol_name)

    # Create new settings
    new_settings = RenderSettings()
    new_settings.show_hydrogens = False
    new_settings.show_numbers = True

    # Update settings through SceneManager
    scene.update_settings(mol_name, new_settings)

    # Check if settings were updated
    assert mol_obj.render_settings.show_hydrogens == False
    assert mol_obj.render_settings.show_numbers == True


def test_scalar_field_settings_update(scene_with_objects):
    scene, _, field_names = scene_with_objects
    field_name = field_names[-1]  # Get scalar field name

    # Get scalar field object
    field_obj = scene.get_object_by_name(field_name)

    # Create new settings
    new_settings = ScalarFieldRenderSettings()
    new_settings.isosurface_value = 0.5
    new_settings.opacity = 0.7
    new_settings.color = 'red'

    # Update settings through SceneManager
    scene.update_settings(field_name, new_settings)

    # Check if settings were updated
    assert field_obj.render_settings.isosurface_value == 0.5
    assert field_obj.render_settings.opacity == 0.7
    assert field_obj.render_settings.color == 'red'
