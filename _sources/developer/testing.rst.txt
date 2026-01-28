Testing Guide
=============

ChemVista includes a comprehensive test suite covering unit tests, integration tests,
and export consistency tests.

Running Tests
-------------

Basic Test Execution
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   poetry run pytest

   # Run with verbose output
   poetry run pytest -v

   # Run with coverage
   poetry run pytest --cov=chemvista

   # Run specific test file
   poetry run pytest tests/test_scene_manager.py -v

   # Run specific test
   poetry run pytest tests/test_scene_manager.py::test_load_xyz -v

Test Categories
~~~~~~~~~~~~~~~

Run tests by category using markers:

.. code-block:: bash

   # Run only export tests
   poetry run pytest tests/test_export_consistency.py -v

   # Run only GLB tests
   poetry run pytest -k "glb" -v

   # Run only PNG tests
   poetry run pytest -k "png" -v

Test Configuration
------------------

Tests are configured in ``pyproject.toml``:

.. code-block:: toml

   [tool.pytest.ini_options]
   testpaths = ["tests"]
   python_files = ["test_*.py"]
   python_classes = ["Test*"]
   python_functions = ["test_*"]

The test suite automatically runs in headless mode by setting:

* ``QT_QPA_PLATFORM=offscreen`` - Qt offscreen rendering
* ``pv.OFF_SCREEN = True`` - PyVista offscreen mode

Export Consistency Tests
------------------------

The ``test_export_consistency.py`` module provides comprehensive testing for
GLB and PNG exports.

Fingerprint-Based Testing
~~~~~~~~~~~~~~~~~~~~~~~~~

Instead of comparing binary files, the tests use "fingerprints" - lightweight
summaries of export properties:

**GLB Fingerprints include:**

* Vertex and face counts
* Mesh and node counts
* Geometry hashes (positions, indices)
* Bounding box dimensions
* Color statistics (unique colors, histogram)
* Animation data (frames, duration, keyframes)
* Material information

**PNG Fingerprints include:**

* Image dimensions
* Pixel content hash
* Color statistics
* Transparency information

Reference Fingerprints
~~~~~~~~~~~~~~~~~~~~~~

Reference fingerprints are stored in ``tests/data/reference_fingerprints.json``
and track the expected export properties for different configurations.

**Regenerating references:**

.. code-block:: bash

   # Regenerate all reference fingerprints
   pytest tests/test_export_consistency.py --generate-fingerprints -k reference -v

**When to regenerate:**

* After intentional changes to rendering or export
* After VTK version updates
* After palette changes

Test Classes
~~~~~~~~~~~~

``TestExportDeterminism``
   Verifies that repeated exports produce identical results.

``TestPNGExport``
   Tests PNG screenshot functionality including:

   * File creation
   * Content validation
   * Palette effects
   * Transparency
   * Window size effects

``TestParameterEffects``
   Verifies that parameter changes affect output correctly:

   * Palette changes colors
   * Resolution affects vertex count
   * FPS affects animation timing

``TestAPIConsistency``
   Ensures the Python API produces valid exports.

``TestColorVerification``
   Validates specific colors for different palettes.

``TestReferenceFingerprints``
   Compares current exports against stored references.

``TestSaveExportSamples``
   Saves actual GLB and PNG files for visual inspection.

Sample Output Directory
~~~~~~~~~~~~~~~~~~~~~~~

Tests can save sample exports to ``tests/output/`` for visual inspection:

.. code-block:: bash

   # Run sample export tests
   pytest tests/test_export_consistency.py -k save_sample -v

   # View saved files
   ls tests/output/

Output files include:

* GLB exports with different palettes
* Animated trajectory exports
* PNG screenshots (default, powerpoint, transparent)
* Molecules with scalar fields

The output directory is gitignored to avoid committing binary files.

Writing Tests
-------------

Test Fixtures
~~~~~~~~~~~~~

Common fixtures are defined in ``tests/conftest.py``:

.. code-block:: python

   @pytest.fixture
   def scene_manager_factory(test_plotter):
       """Factory to create fresh SceneManager instances."""
       def _create():
           signals = TreeSignals()
           manager = SceneManager(tree_signals=signals)
           manager.plotter = test_plotter
           return manager
       yield _create

   @pytest.fixture
   def test_files():
       """Paths to test data files."""
       return {
           'molecule_1': Path('tests/data/mpf_motor.xyz'),
           'molecule_2': Path('tests/data/C6H6.xyz'),
           'trajectory': Path('tests/data/mpf_motor_trajectory.xyz'),
           'scalar_filed_cube': Path('tests/data/C2H4.eldens.cube'),
       }

Example Test
~~~~~~~~~~~~

.. code-block:: python

   def test_png_palette_affects_colors(self, scene_manager_factory, test_files, temp_png_pair):
       """Different palettes should produce different colors in screenshots."""
       path1, path2 = temp_png_pair

       # Screenshot with default palette
       sm1 = scene_manager_factory()
       sm1.load_xyz(test_files['molecule_1'])
       plotter1 = pv.Plotter(off_screen=True)
       sm1.render(plotter=plotter1)
       plotter1.screenshot(str(path1))
       plotter1.close()
       fp1 = extract_png_fingerprint(path1)

       # Screenshot with PowerPoint palette
       sm2 = scene_manager_factory()
       sm2.load_xyz(test_files['molecule_1'])
       sm2.set_palette('powerpoint')
       plotter2 = pv.Plotter(off_screen=True)
       sm2.render(plotter=plotter2)
       plotter2.screenshot(str(path2))
       plotter2.close()
       fp2 = extract_png_fingerprint(path2)

       # Pixel hashes should differ (different colors)
       assert fp1.pixel_hash != fp2.pixel_hash

Known Issues
------------

VTK Version Compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~

VTK 9.5+ is required for consistent test results. Earlier versions have different
mesh merge behavior that causes fingerprint mismatches.

If you encounter hash mismatches:

.. code-block:: bash

   # Check VTK version
   pip show vtk

   # Should be >= 9.5.0

See the Known Issues section in CLAUDE.md for details.

CI/CD Integration
-----------------

Tests run automatically on GitHub Actions for:

* Python 3.10 and 3.11
* Ubuntu and macOS
* All pull requests and main branch pushes

Screenshot Tests in CI
~~~~~~~~~~~~~~~~~~~~~~

PNG screenshot tests require actual OpenGL rendering, which is not available in
headless CI environments (GitHub Actions). These tests are automatically skipped
when running in CI.

Tests marked with ``@pytest.mark.screenshot`` are skipped when the ``CI`` or
``GITHUB_ACTIONS`` environment variable is set to ``true``.

To run screenshot tests locally:

.. code-block:: bash

   # Run all tests including screenshots
   poetry run pytest -v

   # Run only screenshot tests
   poetry run pytest -m screenshot -v

To simulate CI environment locally (skip screenshot tests):

.. code-block:: bash

   CI=true poetry run pytest -v

See Also
--------

* :doc:`../api/exporter` - Exporter API reference
* :doc:`contributing` - Contributing guidelines
