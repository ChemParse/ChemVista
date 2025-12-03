"""
Tests for AnimatedMoleculeRenderer - verifies correctness and performance of animation rendering.
"""

import pytest
import numpy as np
import pyvista as pv
import time
from unittest.mock import MagicMock, patch
from nx_ase import Molecule, Trajectory

from chemvista.renderer.animated_molecule import AnimatedMoleculeRenderer


class TestAnimatedMoleculeRendererSetup:
    """Tests for initial setup and mesh creation"""

    def test_renderer_initialization(self):
        """Test that renderer initializes with correct defaults"""
        renderer = AnimatedMoleculeRenderer()

        assert renderer._atoms_mesh is None
        assert renderer._bonds_mesh is None
        assert renderer._atom_info == []
        assert renderer._bond_info == []
        assert renderer._base_molecule is None
        assert renderer._plotter is None
        assert renderer._settings is None
        assert renderer.is_setup is False

    def test_setup_creates_meshes(self, test_plotter, test_objects):
        """Test that setup creates atom and bond meshes"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(molecule, test_plotter, settings)

        assert renderer.is_setup is True
        assert renderer._atoms_mesh is not None
        assert renderer._base_molecule is molecule
        assert renderer._plotter is test_plotter
        assert renderer._settings is settings

    def test_setup_tracks_atom_info(self, test_plotter, test_objects):
        """Test that atom info is properly tracked for position updates"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(molecule, test_plotter, settings)

        # Should have info for each atom
        num_visible_atoms = len([s for s in molecule.get_chemical_symbols()])
        assert len(renderer._atom_info) == num_visible_atoms

        # Each atom info should have required fields
        for atom_info in renderer._atom_info:
            assert 'original_idx' in atom_info
            assert 'vertex_start' in atom_info
            assert 'vertex_count' in atom_info
            assert 'base_points' in atom_info
            assert isinstance(atom_info['base_points'], np.ndarray)

    def test_setup_tracks_bond_info(self, test_plotter, test_objects):
        """Test that bond info is properly tracked for position updates"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_2']  # C6H6 has bonds
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(molecule, test_plotter, settings)

        # Should have bond info if molecule has bonds
        if len(molecule.get_all_bonds()) > 0:
            assert len(renderer._bond_info) > 0

            for bond_info in renderer._bond_info:
                assert 'atom_indices' in bond_info
                assert 'vertex_start' in bond_info
                assert 'vertex_count' in bond_info
                assert 'resolution' in bond_info

    def test_setup_respects_show_hydrogens(self, test_plotter, test_objects):
        """Test that show_hydrogens setting filters hydrogen atoms"""
        renderer_with_h = AnimatedMoleculeRenderer()
        renderer_without_h = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_2']  # C6H6 has hydrogens

        settings_with_h = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }
        settings_without_h = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': False,
        }

        # Need separate plotters to avoid conflicts
        plotter1 = pv.Plotter(off_screen=True)
        plotter2 = pv.Plotter(off_screen=True)

        renderer_with_h.setup(molecule, plotter1, settings_with_h)
        renderer_without_h.setup(molecule, plotter2, settings_without_h)

        # Should have fewer atoms when hiding hydrogens
        num_h = sum(1 for s in molecule.get_chemical_symbols() if s == 'H')
        if num_h > 0:
            assert len(renderer_with_h._atom_info) > len(renderer_without_h._atom_info)
            assert len(renderer_with_h._atom_info) - len(renderer_without_h._atom_info) == num_h

        plotter1.close()
        plotter2.close()

    def test_vertex_offsets_are_contiguous(self, test_plotter, test_objects):
        """Test that vertex offsets are properly calculated for merged mesh"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(molecule, test_plotter, settings)

        # Verify vertex ranges don't overlap and are contiguous
        if len(renderer._atom_info) > 1:
            sorted_info = sorted(renderer._atom_info, key=lambda x: x['vertex_start'])
            for i in range(len(sorted_info) - 1):
                current_end = sorted_info[i]['vertex_start'] + sorted_info[i]['vertex_count']
                next_start = sorted_info[i + 1]['vertex_start']
                assert current_end == next_start, "Vertex ranges should be contiguous"


class TestAnimatedMoleculeRendererUpdates:
    """Tests for position update functionality"""

    def test_update_positions_modifies_mesh(self, test_plotter, test_objects):
        """Test that update_positions actually modifies the mesh points"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(molecule, test_plotter, settings)

        # Get original mesh points
        original_points = renderer._atoms_mesh.points.copy()

        # Create new positions (shifted by 1.0 in all directions)
        new_positions = molecule.positions + 1.0

        renderer.update_positions(new_positions)

        # Points should have changed
        assert not np.allclose(renderer._atoms_mesh.points, original_points)

    def test_update_positions_correctness(self, test_plotter):
        """Test that atom positions are updated correctly"""
        renderer = AnimatedMoleculeRenderer()

        # Create a simple molecule with known positions
        mol = Molecule(
            symbols=['C', 'O'],
            positions=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        )
        settings = {
            'resolution': 8,  # Lower resolution for simpler mesh
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(mol, test_plotter, settings)

        # Get the centroid of each atom's vertices before update
        centroids_before = []
        for atom_info in renderer._atom_info:
            start = atom_info['vertex_start']
            count = atom_info['vertex_count']
            centroid = renderer._atoms_mesh.points[start:start + count].mean(axis=0)
            centroids_before.append(centroid)

        # Update to new positions
        new_positions = np.array([[2.0, 0.0, 0.0], [3.0, 0.0, 0.0]])
        renderer.update_positions(new_positions)

        # Get centroids after update
        centroids_after = []
        for atom_info in renderer._atom_info:
            start = atom_info['vertex_start']
            count = atom_info['vertex_count']
            centroid = renderer._atoms_mesh.points[start:start + count].mean(axis=0)
            centroids_after.append(centroid)

        # Verify centroids match new positions
        for i, (centroid, expected_pos) in enumerate(zip(centroids_after, new_positions)):
            np.testing.assert_array_almost_equal(
                centroid, expected_pos, decimal=1,
                err_msg=f"Atom {i} centroid should match new position"
            )

    def test_update_positions_preserves_mesh_structure(self, test_plotter, test_objects):
        """Test that update doesn't change mesh topology (point count, connectivity)"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(molecule, test_plotter, settings)

        original_n_points = renderer._atoms_mesh.n_points
        original_n_cells = renderer._atoms_mesh.n_cells

        # Update positions
        new_positions = molecule.positions + np.random.randn(*molecule.positions.shape) * 0.5
        renderer.update_positions(new_positions)

        # Mesh structure should be preserved
        assert renderer._atoms_mesh.n_points == original_n_points
        assert renderer._atoms_mesh.n_cells == original_n_cells

    def test_update_handles_missing_renderer(self):
        """Test that update gracefully handles un-setup renderer"""
        renderer = AnimatedMoleculeRenderer()

        # Should not raise an error
        renderer.update_positions(np.array([[0, 0, 0]]))

    def test_update_calls_render(self, test_plotter, test_objects):
        """Test that update triggers plotter render"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        # Mock the render method
        test_plotter.render = MagicMock()

        renderer.setup(molecule, test_plotter, settings)
        new_positions = molecule.positions + 0.1
        renderer.update_positions(new_positions)

        test_plotter.render.assert_called()


class TestAnimatedMoleculeRendererBonds:
    """Tests for bond rendering and updates"""

    def test_bond_mesh_creation(self, test_plotter, test_objects):
        """Test that bonds mesh is created correctly"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_2']  # C6H6 - benzene with bonds
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(molecule, test_plotter, settings)

        # Should have bonds mesh
        if len(molecule.get_all_bonds()) > 0:
            assert renderer._bonds_mesh is not None
            assert renderer._bonds_mesh.n_points > 0

    def test_bond_update_with_positions(self, test_plotter, test_objects):
        """Test that bonds are updated when positions change"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_2']
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(molecule, test_plotter, settings)

        if renderer._bonds_mesh is None:
            pytest.skip("No bonds in molecule")

        original_bond_points = renderer._bonds_mesh.points.copy()

        # Shift all atoms
        new_positions = molecule.positions + 2.0
        renderer.update_positions(new_positions)

        # Bond positions should have changed
        assert not np.allclose(renderer._bonds_mesh.points, original_bond_points)


class TestAnimatedMoleculeRendererClear:
    """Tests for clear functionality"""

    def test_clear_resets_state(self, test_plotter, test_objects):
        """Test that clear properly resets all renderer state"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(molecule, test_plotter, settings)
        assert renderer.is_setup is True

        renderer.clear()

        assert renderer._atoms_mesh is None
        assert renderer._bonds_mesh is None
        assert renderer._atom_info == []
        assert renderer._bond_info == []
        assert renderer._base_molecule is None
        assert renderer._plotter is None
        assert renderer._settings is None
        assert renderer.is_setup is False


class TestAnimatedMoleculeRendererPerformance:
    """Performance benchmarks for animation rendering"""

    def test_setup_time_benchmark(self, test_plotter, test_objects, benchmark_config):
        """Benchmark initial setup time"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 20,  # Default resolution
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        start_time = time.perf_counter()
        renderer.setup(molecule, test_plotter, settings)
        setup_time = time.perf_counter() - start_time

        # Log the timing
        print(f"\nSetup time for {len(molecule)} atoms: {setup_time*1000:.2f}ms")

        # Setup should complete in reasonable time (< 2 seconds for typical molecules)
        assert setup_time < benchmark_config['max_setup_time'], \
            f"Setup took {setup_time:.2f}s, expected < {benchmark_config['max_setup_time']}s"

    def test_update_time_benchmark(self, test_plotter, test_objects, benchmark_config):
        """Benchmark per-frame update time"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 20,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        # Mock render to avoid actual rendering overhead in benchmark
        test_plotter.render = MagicMock()

        renderer.setup(molecule, test_plotter, settings)

        # Measure update times
        update_times = []
        num_updates = 100

        for i in range(num_updates):
            # Create slightly different positions each time
            new_positions = molecule.positions + np.random.randn(*molecule.positions.shape) * 0.01

            start_time = time.perf_counter()
            renderer.update_positions(new_positions)
            update_time = time.perf_counter() - start_time
            update_times.append(update_time)

        avg_update_time = np.mean(update_times)
        max_update_time = np.max(update_times)

        print(f"\nUpdate times for {len(molecule)} atoms over {num_updates} frames:")
        print(f"  Average: {avg_update_time*1000:.2f}ms")
        print(f"  Maximum: {max_update_time*1000:.2f}ms")
        print(f"  Theoretical FPS: {1/avg_update_time:.1f}")

        # Updates should be fast enough for 60 FPS (< 16.67ms)
        assert avg_update_time < benchmark_config['max_update_time'], \
            f"Average update took {avg_update_time*1000:.2f}ms, expected < {benchmark_config['max_update_time']*1000:.0f}ms"

    def test_update_time_scales_with_atoms(self, benchmark_config):
        """Test that update time scales reasonably with number of atoms"""
        update_times = {}

        for num_atoms in [10, 50, 100]:
            # Create molecule with specified number of atoms
            symbols = ['C'] * num_atoms
            positions = np.random.randn(num_atoms, 3) * 5.0
            mol = Molecule(symbols=symbols, positions=positions)

            plotter = pv.Plotter(off_screen=True)
            plotter.render = MagicMock()  # Mock to avoid rendering overhead

            renderer = AnimatedMoleculeRenderer()
            settings = {
                'resolution': 20,
                'alpha': 1.0,
                'show_hydrogens': True,
            }

            renderer.setup(mol, plotter, settings)

            # Measure update time
            times = []
            for _ in range(50):
                new_positions = positions + np.random.randn(num_atoms, 3) * 0.01
                start = time.perf_counter()
                renderer.update_positions(new_positions)
                times.append(time.perf_counter() - start)

            update_times[num_atoms] = np.mean(times)
            plotter.close()

        print(f"\nScaling test - average update times:")
        for n, t in update_times.items():
            print(f"  {n} atoms: {t*1000:.2f}ms")

        # Verify roughly linear scaling (scaling is expected to be somewhat super-linear
        # due to memory allocation overhead, but should not be worse than O(n^2))
        if 10 in update_times and 100 in update_times:
            scaling_factor = update_times[100] / update_times[10]
            print(f"  Scaling factor (100 vs 10 atoms): {scaling_factor:.1f}x")
            # Allow up to 20x for 10x increase (accounts for memory/cache effects)
            assert scaling_factor < 20, f"Update time scaling too high: {scaling_factor}x"


class TestAnimatedMoleculeRendererIntegration:
    """Integration tests for trajectory animation"""

    def test_trajectory_animation_sequence(self, test_plotter, test_objects):
        """Test rendering a full trajectory animation sequence"""
        trajectory = test_objects['trajectory']
        renderer = AnimatedMoleculeRenderer()

        if len(trajectory) < 2:
            pytest.skip("Need at least 2 frames for trajectory test")

        # Use first frame for setup
        first_frame = trajectory[0]
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        renderer.setup(first_frame, test_plotter, settings)

        # Mock render AFTER setup to count only update calls
        test_plotter.render = MagicMock()

        # Animate through all frames
        for i, frame in enumerate(trajectory):
            renderer.update_positions(frame.positions)

        # Should have called render for each update
        assert test_plotter.render.call_count == len(trajectory)

    def test_interpolated_positions(self, test_plotter, test_objects):
        """Test that interpolated positions work correctly with renderer"""
        trajectory = test_objects['trajectory']

        if len(trajectory) < 2:
            pytest.skip("Need at least 2 frames for interpolation test")

        renderer = AnimatedMoleculeRenderer()
        first_frame = trajectory[0]
        settings = {
            'resolution': 10,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        test_plotter.render = MagicMock()
        renderer.setup(first_frame, test_plotter, settings)

        # Get positions for frames 0 and 1
        pos0 = trajectory[0].positions
        pos1 = trajectory[1].positions

        # Test various interpolation points
        for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
            interpolated = pos0 * (1 - alpha) + pos1 * alpha

            # Should be able to update with interpolated positions
            renderer.update_positions(interpolated)

            # Verify mesh was updated (check a sample atom)
            if len(renderer._atom_info) > 0:
                atom_info = renderer._atom_info[0]
                start = atom_info['vertex_start']
                count = atom_info['vertex_count']
                centroid = renderer._atoms_mesh.points[start:start + count].mean(axis=0)
                expected_pos = interpolated[atom_info['original_idx']]
                np.testing.assert_array_almost_equal(centroid, expected_pos, decimal=1)


@pytest.fixture
def test_plotter():
    """Create a test plotter for animation renderer tests"""
    plotter = pv.Plotter(off_screen=True)
    yield plotter
    try:
        plotter.close()
    except (AttributeError, RuntimeError):
        pass


@pytest.fixture
def benchmark_config():
    """Configuration for performance benchmarks"""
    return {
        'max_setup_time': 2.0,  # Maximum acceptable setup time in seconds
        'max_update_time': 0.016,  # Maximum acceptable update time (60 FPS target)
    }


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
