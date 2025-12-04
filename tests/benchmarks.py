"""
Performance benchmarks for ChemVista.

These benchmarks measure performance but DO NOT assert time limits.
Run with: poetry run pytest tests/benchmarks.py -v -s

The benchmarks:
1. Measure and report timing data
2. Compare relative performance (fast path vs slow path)
3. Can be used to track performance regressions over time

To run only benchmarks: poetry run pytest tests/benchmarks.py -v -s
To skip benchmarks in CI: poetry run pytest tests/ --ignore=tests/benchmarks.py
"""

import pytest
import numpy as np
import pyvista as pv
import time
from unittest.mock import MagicMock, patch
from nx_ase import Molecule

from chemvista.renderer.animated_molecule import AnimatedMoleculeRenderer
from chemvista.scene_manager import SceneManager
from chemvista.tree_structure import TreeSignals


def measure_time(func, *args, **kwargs):
    """Measure execution time of a function"""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return elapsed, result


def measure_times(func, iterations, *args, **kwargs):
    """Measure execution time over multiple iterations"""
    times = []
    for _ in range(iterations):
        elapsed, _ = measure_time(func, *args, **kwargs)
        times.append(elapsed)
    return {
        'mean': np.mean(times),
        'std': np.std(times),
        'min': np.min(times),
        'max': np.max(times),
        'median': np.median(times),
        'times': times
    }


class TestAnimationBenchmarks:
    """Benchmarks for animation rendering performance"""

    def test_setup_time(self, test_plotter, test_objects):
        """Measure initial setup time for animated renderer"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 20,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        elapsed, _ = measure_time(renderer.setup, molecule, test_plotter, settings)

        print(f"\n{'='*60}")
        print(f"BENCHMARK: AnimatedMoleculeRenderer.setup()")
        print(f"{'='*60}")
        print(f"  Molecule size: {len(molecule)} atoms")
        print(f"  Setup time: {elapsed*1000:.2f}ms")
        print(f"{'='*60}")

    def test_update_time(self, test_plotter, test_objects):
        """Measure per-frame update time"""
        renderer = AnimatedMoleculeRenderer()
        molecule = test_objects['molecule_1']
        settings = {
            'resolution': 20,
            'alpha': 1.0,
            'show_hydrogens': True,
        }

        # Mock render to isolate update performance
        test_plotter.render = MagicMock()
        renderer.setup(molecule, test_plotter, settings)

        # Measure updates
        def do_update():
            new_positions = molecule.positions + np.random.randn(*molecule.positions.shape) * 0.01
            renderer.update_positions(new_positions)

        stats = measure_times(do_update, iterations=100)

        print(f"\n{'='*60}")
        print(f"BENCHMARK: AnimatedMoleculeRenderer.update_positions()")
        print(f"{'='*60}")
        print(f"  Molecule size: {len(molecule)} atoms")
        print(f"  Iterations: 100")
        print(f"  Mean time: {stats['mean']*1000:.2f}ms")
        print(f"  Std dev: {stats['std']*1000:.2f}ms")
        print(f"  Min time: {stats['min']*1000:.2f}ms")
        print(f"  Max time: {stats['max']*1000:.2f}ms")
        print(f"  Theoretical max FPS: {1/stats['mean']:.1f}")
        print(f"{'='*60}")

    def test_scaling_with_atoms(self):
        """Measure how update time scales with molecule size"""
        atom_counts = [10, 25, 50, 100, 200]
        results = {}

        for num_atoms in atom_counts:
            symbols = ['C'] * num_atoms
            positions = np.random.randn(num_atoms, 3) * 5.0
            mol = Molecule(symbols=symbols, positions=positions)

            plotter = pv.Plotter(off_screen=True)
            plotter.render = MagicMock()

            renderer = AnimatedMoleculeRenderer()
            settings = {
                'resolution': 20,
                'alpha': 1.0,
                'show_hydrogens': True,
            }

            renderer.setup(mol, plotter, settings)

            def do_update():
                new_pos = positions + np.random.randn(num_atoms, 3) * 0.01
                renderer.update_positions(new_pos)

            stats = measure_times(do_update, iterations=50)
            results[num_atoms] = stats['mean']
            plotter.close()

        print(f"\n{'='*60}")
        print(f"BENCHMARK: Update time scaling with molecule size")
        print(f"{'='*60}")
        for n, t in results.items():
            print(f"  {n:4d} atoms: {t*1000:8.2f}ms")

        # Calculate scaling factors
        if 10 in results and 100 in results:
            factor = results[100] / results[10]
            print(f"  Scaling (100 vs 10 atoms): {factor:.1f}x")
        if 10 in results and 200 in results:
            factor = results[200] / results[10]
            print(f"  Scaling (200 vs 10 atoms): {factor:.1f}x")
        print(f"{'='*60}")


class TestVisibilityBenchmarks:
    """Benchmarks for visibility toggle performance"""

    @pytest.fixture
    def signals(self):
        return TreeSignals()

    @pytest.fixture
    def scene(self, test_plotter, signals):
        manager = SceneManager(tree_signals=signals)
        manager.plotter = test_plotter
        return manager

    def test_full_render_time(self, scene, test_files, test_plotter):
        """Measure full scene render time (baseline for comparison)"""
        # Load multiple molecules
        objs = []
        for _ in range(3):
            obj = scene.load_xyz(test_files['molecule_1'])
            objs.append(obj)

        def do_render():
            test_plotter.clear()
            scene.render(test_plotter)

        stats = measure_times(do_render, iterations=10)

        print(f"\n{'='*60}")
        print(f"BENCHMARK: Full scene render")
        print(f"{'='*60}")
        print(f"  Objects in scene: {len(objs)}")
        print(f"  Mean time: {stats['mean']*1000:.2f}ms")
        print(f"  Std dev: {stats['std']*1000:.2f}ms")
        print(f"{'='*60}")

    def test_actor_visibility_toggle_time(self, scene, test_files, test_plotter):
        """Measure fast visibility toggle time using actor.SetVisibility()"""
        obj = scene.load_xyz(test_files['molecule_1'])

        # Render once to get actors
        _, actor_map = scene.render(test_plotter)

        if obj.uuid not in actor_map or not actor_map[obj.uuid]:
            pytest.skip("No actors returned from render")

        actors = actor_map[obj.uuid]

        def do_toggle():
            for actor in actors:
                if hasattr(actor, 'SetVisibility'):
                    actor.SetVisibility(False)
                    actor.SetVisibility(True)

        stats = measure_times(do_toggle, iterations=1000)

        print(f"\n{'='*60}")
        print(f"BENCHMARK: Actor visibility toggle (fast path)")
        print(f"{'='*60}")
        print(f"  Actors: {len(actors)}")
        print(f"  Mean time: {stats['mean']*1000000:.2f}µs")  # microseconds
        print(f"  Std dev: {stats['std']*1000000:.2f}µs")
        print(f"{'='*60}")

    def test_visibility_speedup_ratio(self, scene, test_files, test_plotter):
        """Compare fast visibility toggle vs full re-render"""
        # Load molecule
        obj = scene.load_xyz(test_files['molecule_1'])

        # Render once to get actors
        _, actor_map = scene.render(test_plotter)

        if obj.uuid not in actor_map or not actor_map[obj.uuid]:
            pytest.skip("No actors returned from render")

        actors = actor_map[obj.uuid]

        # Measure full render time
        def do_full_render():
            test_plotter.clear()
            scene.render(test_plotter)

        full_stats = measure_times(do_full_render, iterations=10)

        # Measure fast toggle time
        def do_fast_toggle():
            for actor in actors:
                if hasattr(actor, 'SetVisibility'):
                    actor.SetVisibility(False)

        fast_stats = measure_times(do_fast_toggle, iterations=100)

        speedup = full_stats['mean'] / fast_stats['mean'] if fast_stats['mean'] > 0 else float('inf')

        print(f"\n{'='*60}")
        print(f"BENCHMARK: Visibility toggle speedup")
        print(f"{'='*60}")
        print(f"  Full re-render: {full_stats['mean']*1000:.2f}ms")
        print(f"  Fast toggle: {fast_stats['mean']*1000000:.2f}µs")
        print(f"  Speedup: {speedup:.0f}x faster")
        print(f"{'='*60}")


class TestRenderBenchmarks:
    """Benchmarks for rendering different object types"""

    @pytest.fixture
    def signals(self):
        return TreeSignals()

    @pytest.fixture
    def scene(self, test_plotter, signals):
        manager = SceneManager(tree_signals=signals)
        manager.plotter = test_plotter
        return manager

    def test_molecule_render_time(self, scene, test_objects, test_plotter):
        """Measure molecule rendering time"""
        molecule = test_objects['molecule_1']
        settings = scene.molecule_renderer.get_default_settings()

        def do_render():
            test_plotter.clear()
            scene.molecule_renderer.render(molecule, test_plotter, settings)

        stats = measure_times(do_render, iterations=10)

        print(f"\n{'='*60}")
        print(f"BENCHMARK: Molecule render")
        print(f"{'='*60}")
        print(f"  Atoms: {len(molecule)}")
        print(f"  Mean time: {stats['mean']*1000:.2f}ms")
        print(f"  Std dev: {stats['std']*1000:.2f}ms")
        print(f"{'='*60}")

    def test_scalar_field_render_time(self, scene, test_objects, test_plotter):
        """Measure scalar field rendering time"""
        field = test_objects['scalar_field']
        settings = scene.scalar_field_renderer.get_default_settings()

        def do_render():
            test_plotter.clear()
            scene.scalar_field_renderer.render(field, test_plotter, settings)

        stats = measure_times(do_render, iterations=5)

        print(f"\n{'='*60}")
        print(f"BENCHMARK: Scalar field render")
        print(f"{'='*60}")
        print(f"  Grid shape: {field.scalar_field.shape}")
        print(f"  Mean time: {stats['mean']*1000:.2f}ms")
        print(f"  Std dev: {stats['std']*1000:.2f}ms")
        print(f"{'='*60}")


# Fixtures needed for benchmarks
@pytest.fixture
def test_plotter():
    """Create a test plotter"""
    plotter = pv.Plotter(off_screen=True)
    yield plotter
    try:
        plotter.close()
    except (AttributeError, RuntimeError):
        pass


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
