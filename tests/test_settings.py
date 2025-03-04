import pytest
from chemvista.scene_objects import SceneManager
from chemvista.render_settings import RenderSettings, ScalarFieldRenderSettings


@pytest.fixture
def scene_with_objects(test_plotter, test_files):
    """Create a scene with molecule and scalar field objects"""
    scene = SceneManager()
    scene.plotter = test_plotter
    mol_uuid = scene.load_molecule(test_files['xyz'])[0]
    field_uuids = scene.load_molecule_from_cube(test_files['cube'])
    return scene, mol_uuid, field_uuids


def test_molecule_settings_update(scene_with_objects):
    scene, mol_uuid, _ = scene_with_objects

    # Get molecule object
    mol_obj = scene.get_object_by_uuid(mol_uuid)

    # Create new settings
    settings = RenderSettings()
    settings.show_hydrogens = False
    settings.bond_radius = 0.2
    settings.show_numbers = True

    # Update settings
    scene.update_settings(mol_uuid, settings)

    # Verify settings were applied
    assert not mol_obj.render_settings.show_hydrogens
    assert mol_obj.render_settings.bond_radius == 0.2
    assert mol_obj.render_settings.show_numbers


def test_scalar_field_settings_update(scene_with_objects):
    scene, _, field_uuids = scene_with_objects
    field_uuid = field_uuids[-1]  # Get scalar field name

    # Get scalar field object
    field_obj = scene.get_object_by_uuid(field_uuid)

    # Create new settings
    settings = ScalarFieldRenderSettings()
    settings.opacity = 0.7
    settings.n_contours = 5
    settings.colormap = 'viridis'

    # Update settings
    scene.update_settings(field_uuid, settings)

    # Verify settings were applied
    assert field_obj.render_settings.opacity == 0.7
    assert field_obj.render_settings.n_contours == 5
    assert field_obj.render_settings.colormap == 'viridis'
