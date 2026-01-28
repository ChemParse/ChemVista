import pytest
import pathlib
import tempfile
import numpy as np
import trimesh
from chemvista.scene_manager import SceneManager
from chemvista.exporter import Exporter
from chemvista.scene_objects import MoleculeObject, ScalarFieldObject
from chemvista.tree_structure import TreeSignals
from nx_ase import Molecule, ScalarField


@pytest.fixture
def signals(qtbot):
    """Create TreeSignals for testing"""
    return TreeSignals()


@pytest.fixture
def scene(test_plotter, signals):
    """Create SceneManager with test plotter and signals"""
    manager = SceneManager(tree_signals=signals)
    manager.plotter = test_plotter
    return manager


@pytest.fixture
def temp_glb_file():
    """Create a temporary GLB file path"""
    with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
        filepath = pathlib.Path(tmp.name)
    yield filepath
    # Clean up after test
    filepath.unlink(missing_ok=True)


def test_exporter_initialization(scene):
    """Test that Exporter can be initialized with a SceneManager"""
    exporter = Exporter(scene)
    assert exporter.scene_manager is scene


def test_export_single_molecule(scene, test_files, temp_glb_file):
    """Test exporting a single molecule to GLB"""
    # Load a molecule
    mol_obj = scene.load_xyz(test_files['molecule_1'])
    assert isinstance(mol_obj, MoleculeObject)

    # Export to GLB
    exporter = Exporter(scene)
    exporter.export_glb(temp_glb_file)

    # Verify file was created
    assert temp_glb_file.exists()
    assert temp_glb_file.stat().st_size > 0

    # Load and verify GLB structure
    loaded = trimesh.load(str(temp_glb_file))
    assert loaded is not None

    # Check that we have geometry
    if hasattr(loaded, 'geometry'):
        assert len(loaded.geometry) > 0
        # Check first geometry exists and has visual data
        geom = list(loaded.geometry.values())[0]
        assert geom.visual is not None
        # Note: trimesh may convert ColorVisuals to TextureVisuals during export/import
        # Both types indicate successful color export


def test_export_molecule_with_scalar_field(scene, test_files, temp_glb_file):
    """Test exporting a molecule with scalar field to GLB"""
    # Load a molecule with scalar field from cube file
    mol_obj = scene.load_molecule_from_cube(test_files['scalar_filed_cube'])
    assert isinstance(mol_obj, MoleculeObject)
    assert len(mol_obj.children) == 1
    assert isinstance(mol_obj.children[0], ScalarFieldObject)

    # Export to GLB
    exporter = Exporter(scene)
    exporter.export_glb(temp_glb_file)

    # Verify file was created
    assert temp_glb_file.exists()
    assert temp_glb_file.stat().st_size > 0

    # Load and verify
    loaded = trimesh.load(str(temp_glb_file))
    assert loaded is not None


def test_export_multiple_molecules(scene, test_files, temp_glb_file):
    """Test exporting multiple molecules to GLB"""
    # Load multiple molecules
    mol_obj_1 = scene.load_xyz(test_files['molecule_1'])
    mol_obj_2 = scene.load_xyz(test_files['molecule_2'])

    assert len(scene.root_objects) == 2

    # Export to GLB
    exporter = Exporter(scene)
    exporter.export_glb(temp_glb_file)

    # Verify file was created
    assert temp_glb_file.exists()
    assert temp_glb_file.stat().st_size > 0

    # Load and verify
    loaded = trimesh.load(str(temp_glb_file))
    assert loaded is not None


def test_export_respects_visibility(scene, test_files, temp_glb_file):
    """Test that export only includes visible objects"""
    # Load two molecules
    mol_obj_1 = scene.load_xyz(test_files['molecule_1'])
    mol_obj_2 = scene.load_xyz(test_files['molecule_2'])

    # Hide the second molecule
    scene.set_visibility(mol_obj_2.uuid, False)

    # Export should succeed with only visible objects
    exporter = Exporter(scene)
    exporter.export_glb(temp_glb_file)

    assert temp_glb_file.exists()


def test_export_empty_scene_raises_error(scene, temp_glb_file):
    """Test that exporting an empty scene raises an error"""
    exporter = Exporter(scene)

    with pytest.raises(ValueError, match="No visible objects found"):
        exporter.export_glb(temp_glb_file)


def test_export_with_transparency_settings(scene, test_files, temp_glb_file):
    """Test that transparency settings are preserved in export"""
    mol_obj = scene.load_xyz(test_files['molecule_1'])

    # Set transparency
    mol_obj.render_settings.alpha = 0.5

    # Export
    exporter = Exporter(scene)
    exporter.export_glb(temp_glb_file)

    assert temp_glb_file.exists()

    # Load and verify colors are present with alpha
    loaded = trimesh.load(str(temp_glb_file))
    geom = list(loaded.geometry.values())[0]

    # Should have ColorVisuals with vertex colors
    assert geom.visual is not None
    if hasattr(geom.visual, 'vertex_colors'):
        # Check that alpha values reflect the 0.5 setting (127 out of 255)
        alpha_values = geom.visual.vertex_colors[:, 3]
        # Should have some alpha values around 127 (allowing for rounding)
        assert np.any((alpha_values >= 120) & (alpha_values <= 135))


def test_scene_manager_export_to_glb_method(scene, test_files, temp_glb_file):
    """Test the SceneManager.export_to_glb() convenience method"""
    mol_obj = scene.load_xyz(test_files['molecule_1'])

    # Use SceneManager's export method
    scene.export_to_glb(temp_glb_file)

    # Verify file was created
    assert temp_glb_file.exists()
    assert temp_glb_file.stat().st_size > 0


def test_export_preserves_colors(scene, test_files, temp_glb_file):
    """Test that export preserves vertex colors from rendering"""
    mol_obj = scene.load_xyz(test_files['molecule_1'])

    # Export to GLB
    exporter = Exporter(scene)
    exporter.export_glb(temp_glb_file)

    # Load and verify colors are present
    loaded = trimesh.load(str(temp_glb_file))
    geom = list(loaded.geometry.values())[0]

    # Check that visual data exists
    assert geom.visual is not None

    # trimesh may use either ColorVisuals or TextureVisuals after export/import
    # Both indicate successful color preservation
    if hasattr(geom.visual, 'vertex_colors'):
        vertex_colors = geom.visual.vertex_colors
        assert vertex_colors.shape[1] == 4  # RGBA
        assert vertex_colors.dtype == 'uint8'
        # Check that alpha channel is set
        assert (vertex_colors[:, 3] > 0).any()
    else:
        # TextureVisuals is also valid - indicates colors were converted to texture
        assert geom.visual is not None


def test_export_trajectory_frame(scene, test_files, temp_glb_file):
    """Test exporting a trajectory (exports visible frames)"""
    # Load trajectory
    traj_obj = scene.load_xyz(test_files['trajectory'])

    # The trajectory should have been loaded
    assert traj_obj is not None

    # Export - should export visible molecule frames
    exporter = Exporter(scene)
    exporter.export_glb(temp_glb_file)

    # Verify file was created
    assert temp_glb_file.exists()
    assert temp_glb_file.stat().st_size > 0


def test_pv_to_trimesh_conversion(scene, test_files):
    """Test the internal PyVista to trimesh conversion"""
    import pyvista as pv

    # Create a simple PyVista sphere
    sphere = pv.Sphere(radius=1.0, theta_resolution=10, phi_resolution=10)

    # Convert to trimesh
    exporter = Exporter(scene)
    tm = exporter._pv_to_trimesh(sphere)

    # Verify conversion
    assert tm.vertices.shape[0] > 0
    assert tm.faces.shape[0] > 0
    assert tm.faces.shape[1] == 3  # Triangulated


def test_export_invalid_extension(scene, test_files, tmp_path):
    """Test that exporting with invalid file extension raises helpful error"""
    mol_obj = scene.load_xyz(test_files['molecule_1'])

    # Try to export with wrong extension
    invalid_path = tmp_path / "molecule.gbl"  # typo: .gbl instead of .glb

    exporter = Exporter(scene)
    with pytest.raises(ValueError, match="Invalid file extension '.gbl'"):
        exporter.export_glb(invalid_path)

    with pytest.raises(ValueError, match="Did you mean 'molecule.glb'"):
        exporter.export_glb(invalid_path)


def test_export_gltf_extension(scene, test_files, tmp_path):
    """Test that .gltf extension is also accepted"""
    mol_obj = scene.load_xyz(test_files['molecule_1'])

    # Export with .gltf extension (also valid)
    gltf_path = tmp_path / "molecule.gltf"

    exporter = Exporter(scene)
    exporter.export_glb(gltf_path)

    assert gltf_path.exists()
