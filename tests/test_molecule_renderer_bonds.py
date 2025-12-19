"""Tests for center-to-center bond rendering in 3D printing mode."""

import pytest
import numpy as np
from chemvista.renderer import MoleculeRenderer
from nx_ase import Molecule


@pytest.fixture
def renderer():
    """Create a molecule renderer"""
    return MoleculeRenderer()


@pytest.fixture
def simple_molecule():
    """Create a simple H2 molecule for testing."""
    positions = np.array([[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]])
    molecule = Molecule(positions=positions, symbols=['H', 'H'])
    molecule.G.add_edge(0, 1, bond_type=1)
    return molecule


class TestBondRenderingModes:
    """Test bond rendering in visualization vs printing modes"""

    def test_create_bonds_mesh_with_center_to_center_flag(self, renderer, simple_molecule):
        """Test that _create_bonds_mesh accepts center_to_center parameter"""
        settings = {
            'show_hydrogens': True,
            'show_numbers': False,
            'alpha': 1.0,
            'resolution': 20
        }

        bonds_viz = renderer._create_bonds_mesh(
            simple_molecule,
            settings,
            center_to_center=False
        )

        bonds_print = renderer._create_bonds_mesh(
            simple_molecule,
            settings,
            center_to_center=True
        )

        assert bonds_viz is not None
        assert bonds_print is not None

    def test_visualization_mode_has_gaps(self, renderer, simple_molecule):
        """Test that visualization mode creates gaps between atoms and bonds"""
        settings = {
            'show_hydrogens': True,
            'show_numbers': False,
            'alpha': 1.0,
            'resolution': 20
        }

        atom_a = simple_molecule.positions[0]
        atom_b = simple_molecule.positions[1]

        radius_a = renderer.atoms_settings['H']['radius']
        radius_b = renderer.atoms_settings['H']['radius']

        bonds_viz = renderer._create_bonds_mesh(
            simple_molecule,
            settings,
            center_to_center=False
        )

        bond_points = bonds_viz.points

        distances_to_a = np.linalg.norm(bond_points - atom_a, axis=1)
        distances_to_b = np.linalg.norm(bond_points - atom_b, axis=1)

        min_dist_a = distances_to_a.min()
        min_dist_b = distances_to_b.min()

        assert min_dist_a >= radius_a * 0.9, "Bond extends into atom A in visualization mode"
        assert min_dist_b >= radius_b * 0.9, "Bond extends into atom B in visualization mode"

    def test_printing_mode_has_no_gaps(self, renderer, simple_molecule):
        """Test that printing mode creates bonds from center to center (no gaps)"""
        settings = {
            'show_hydrogens': True,
            'show_numbers': False,
            'alpha': 1.0,
            'resolution': 20
        }

        atom_a = simple_molecule.positions[0]
        atom_b = simple_molecule.positions[1]

        bonds_print = renderer._create_bonds_mesh(
            simple_molecule,
            settings,
            center_to_center=True
        )

        bond_points = bonds_print.points

        distances_to_a = np.linalg.norm(bond_points - atom_a, axis=1)
        distances_to_b = np.linalg.norm(bond_points - atom_b, axis=1)

        min_dist_a = distances_to_a.min()
        min_dist_b = distances_to_b.min()

        assert min_dist_a < 0.05, "Bond doesn't reach atom A center in printing mode"
        assert min_dist_b < 0.05, "Bond doesn't reach atom B center in printing mode"


class TestBondTypesWithCenterToCenter:
    """Test different bond types with center-to-center rendering"""

    @pytest.mark.parametrize("bond_type", [1, 2, 3])
    def test_different_bond_types_printing_mode(self, renderer, bond_type):
        """Test that all bond types work in printing mode"""
        start = np.array([0.0, 0.0, 0.0])
        end = np.array([1.5, 0.0, 0.0])
        alpha = 1.0
        resolution = 20
        radius_a = 0.2
        radius_b = 0.2

        cylinders = renderer._create_bond_cylinders(
            start, end, bond_type, alpha, resolution,
            radius_a, radius_b, center_to_center=True
        )

        expected_count = bond_type
        if bond_type == 2:
            expected_count = 2
        elif bond_type == 3:
            expected_count = 3

        assert len(cylinders) == expected_count
