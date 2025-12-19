"""Tests for 3D printing export mode functionality."""

import pytest
import numpy as np
import tempfile
import pathlib
from unittest.mock import Mock, patch
from chemvista import SceneManager
from chemvista.exporter import Exporter
from nx_ase import Molecule


@pytest.fixture
def simple_molecule():
    """Create a simple H2 molecule for testing"""
    positions = np.array([[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]])
    molecule = Molecule(positions=positions, symbols=['H', 'H'])
    molecule.G.add_edge(0, 1, bond_type=1)
    return molecule


@pytest.fixture
def scene_with_molecule(simple_molecule):
    """Create a scene manager with a simple molecule"""
    scene = SceneManager()
    scene.add_molecule(simple_molecule, "H2")
    return scene


class TestPrintingModeExport:
    """Test 3D printing mode export functionality"""

    def test_export_printing_mode_flag(self, scene_with_molecule, tmp_path):
        """Test that printing_mode flag is accepted"""
        output_file = tmp_path / "test_print.glb"

        scene_with_molecule.export_to_glb(
            output_file,
            printing_mode=True,
            printing_resolution=32
        )

        assert output_file.exists()

    def test_export_visualization_mode_default(self, scene_with_molecule, tmp_path):
        """Test that visualization mode is default"""
        output_file = tmp_path / "test_viz.glb"

        scene_with_molecule.export_to_glb(output_file)

        assert output_file.exists()

    def test_printing_resolution_parameter(self, scene_with_molecule, tmp_path):
        """Test that printing_resolution parameter is accepted"""
        output_file = tmp_path / "test_res.glb"

        for resolution in [16, 32, 64]:
            scene_with_molecule.export_to_glb(
                output_file,
                printing_mode=True,
                printing_resolution=resolution
            )
            assert output_file.exists()

    def test_collect_meshes_with_printing_mode(self, scene_with_molecule):
        """Test that meshes are collected differently in printing mode"""
        exporter = Exporter(scene_with_molecule)

        viz_meshes = exporter._collect_meshes_with_colors(printing_mode=False)
        print_meshes = exporter._collect_meshes_with_colors(
            printing_mode=True,
            printing_resolution=32
        )

        assert len(viz_meshes) > 0
        assert len(print_meshes) > 0

    def test_printing_mode_opacity(self, scene_with_molecule):
        """Test that printing mode forces full opacity"""
        exporter = Exporter(scene_with_molecule)

        mol_obj = scene_with_molecule.root.children[0]
        mol_obj.render_settings.alpha = 0.5

        print_meshes = exporter._collect_meshes_with_colors(
            printing_mode=True,
            printing_resolution=32
        )

        for mesh, rgba in print_meshes:
            assert np.all(
                rgba[:, 3] == 255), "Printing mode should force full opacity"

    def test_file_extension_validation(self, scene_with_molecule, tmp_path):
        """Test that invalid file extensions are caught"""
        invalid_file = tmp_path / "test.obj"

        with pytest.raises(ValueError, match="Invalid file extension"):
            scene_with_molecule.export_to_glb(invalid_file, printing_mode=True)

    def test_empty_scene_export(self, tmp_path):
        """Test that exporting empty scene raises error"""
        scene = SceneManager()
        output_file = tmp_path / "empty.glb"

        with pytest.raises(ValueError, match="No visible objects"):
            scene.export_to_glb(output_file, printing_mode=True)


class TestMeshCollectionPrintingMode:
    """Test mesh collection with printing mode settings"""

    def test_higher_resolution_in_printing_mode(self, scene_with_molecule):
        """Test that printing mode uses higher resolution"""
        exporter = Exporter(scene_with_molecule)

        mol_obj = scene_with_molecule.root.children[0]
        mol_obj.render_settings.resolution = 10

        default_meshes = exporter._collect_meshes_with_colors(
            printing_mode=True)
        high_res_meshes = exporter._collect_meshes_with_colors(
            printing_mode=True,
            printing_resolution=64
        )

        default_verts = sum(mesh.vertices.shape[0]
                            for mesh, _ in default_meshes)
        high_res_verts = sum(mesh.vertices.shape[0]
                             for mesh, _ in high_res_meshes)

        assert high_res_verts > default_verts

    def test_bonds_created_with_center_to_center_flag(self, scene_with_molecule):
        """Test that bonds are created with center_to_center flag in printing mode"""
        exporter = Exporter(scene_with_molecule)

        with patch.object(
            scene_with_molecule.molecule_renderer,
            '_create_bonds_mesh'
        ) as mock_bonds:
            mock_bonds.return_value = None

            exporter._collect_meshes_with_colors(printing_mode=True)

            assert mock_bonds.called
            call_kwargs = mock_bonds.call_args[1]
            assert call_kwargs.get('center_to_center') == True


@pytest.mark.parametrize("resolution", [16, 24, 32, 48, 64])
def test_various_resolutions(scene_with_molecule, tmp_path, resolution):
    """Test export with various resolution settings"""
    output_file = tmp_path / f"test_res_{resolution}.glb"

    scene_with_molecule.export_to_glb(
        output_file,
        printing_mode=True,
        printing_resolution=resolution
    )

    assert output_file.exists()
