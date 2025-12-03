Command Line Interface
======================

ChemVista provides a powerful command-line interface for quick visualization and export tasks.

Basic Usage
-----------

The general syntax is:

.. code-block:: bash

   chemvista [OPTIONS]

Quick Reference
---------------

.. code-block:: text

   chemvista [--xyz FILE...] [--cube-mol FILE...] [--cube-field FILE...]
             [-i | -r | -s FILE | -g FILE | --glb-animated FILE]
             [--fps N] [--resolution N] [--cycle] [--scale VALUE]

File Loading Options
--------------------

--xyz
~~~~~

Load XYZ files containing molecular structures or trajectories:

.. code-block:: bash

   # Load single molecule
   chemvista --xyz molecule.xyz

   # Load trajectory (multi-frame XYZ)
   chemvista --xyz trajectory.xyz

   # Load multiple files
   chemvista --xyz mol1.xyz mol2.xyz mol3.xyz

**File format:** Standard XYZ format. Multi-frame files are automatically detected and loaded as trajectories.

--cube-mol
~~~~~~~~~~

Load CUBE files with both the molecule and scalar field:

.. code-block:: bash

   # Load molecule with electron density
   chemvista --cube-mol density.cube

   # Load multiple CUBE files
   chemvista --cube-mol homo.cube lumo.cube

**Result:** Creates a ``MoleculeObject`` with a ``ScalarFieldObject`` child.

--cube-field
~~~~~~~~~~~~

Load CUBE files with scalar field only (no molecule):

.. code-block:: bash

   # Load only the scalar field
   chemvista --cube-field density.cube

**Result:** Creates a standalone ``ScalarFieldObject``.

Visualization Modes
-------------------

These options are mutually exclusive - only one can be used at a time.

-i, --interactive
~~~~~~~~~~~~~~~~~

Launch the full PyQt5 GUI:

.. code-block:: bash

   # Start GUI with file
   chemvista --xyz molecule.xyz --interactive

   # Start empty GUI
   chemvista --interactive

-r, --render
~~~~~~~~~~~~

Render and display in PyVista viewer (default mode):

.. code-block:: bash

   # Open interactive PyVista window
   chemvista --xyz molecule.xyz --render

   # Same as (default behavior)
   chemvista --xyz molecule.xyz

-s, --screenshot
~~~~~~~~~~~~~~~~

Save a screenshot to the specified file:

.. code-block:: bash

   # Save PNG screenshot
   chemvista --xyz molecule.xyz --screenshot output.png

-g, --glb
~~~~~~~~~

Export scene to static GLB file:

.. code-block:: bash

   # Static export for single molecules
   chemvista --xyz molecule.xyz --glb output.glb

   # Export molecule with scalar field
   chemvista --cube-mol density.cube --glb with_density.glb

**Use case:** Single-frame molecules, scalar field visualizations, non-animated content.

--glb-animated
~~~~~~~~~~~~~~

Export scene as animated GLB file with skeletal animation:

.. code-block:: bash

   # Basic animated export
   chemvista --xyz trajectory.xyz --glb-animated animation.glb

   # With all animation options
   chemvista --xyz trajectory.xyz --glb-animated animation.glb \
             --fps 15 --resolution 8 --cycle --scale auto

**Use case:** Molecular dynamics trajectories, animations for PowerPoint presentations.

Animation Options
-----------------

These options are used with ``--glb-animated``:

--fps
~~~~~

Set frames per second for animation playback (default: 10):

.. code-block:: bash

   # Slow motion (5 fps)
   chemvista --xyz traj.xyz --glb-animated slow.glb --fps 5

   # Fast playback (30 fps)
   chemvista --xyz traj.xyz --glb-animated fast.glb --fps 30

**Duration calculation:** ``(frames - 1) / fps`` seconds

--resolution
~~~~~~~~~~~~

Control mesh quality (default: 10, range: 1-20):

.. code-block:: bash

   # High quality, larger file
   chemvista --xyz traj.xyz --glb-animated high.glb --resolution 20

   # Low quality, smaller file
   chemvista --xyz traj.xyz --glb-animated small.glb --resolution 5

**File size impact:**

* resolution=20: ~2000 KB (high quality)
* resolution=10: ~600 KB (default)
* resolution=5: ~200 KB (70% smaller)

--cycle
~~~~~~~

Add reverse frames to create a seamless looping animation:

.. code-block:: bash

   chemvista --xyz traj.xyz --glb-animated looped.glb --cycle

**How it works:**

* Original: frames 1, 2, 3, 4, 5
* Cycled: frames 1, 2, 3, 4, 5, 4, 3, 2
* Creates smooth back-and-forth oscillation

--scale
~~~~~~~

Scale factor for model size:

.. code-block:: bash

   # Auto-scale to fit in 2-unit bounding box
   chemvista --xyz traj.xyz --glb-animated scaled.glb --scale auto

   # Manual scale factor
   chemvista --xyz traj.xyz --glb-animated scaled.glb --scale 0.1

**Values:**

* ``auto``: Automatically fit model in 2-unit box
* Number (e.g., ``0.1``): Multiply all coordinates by this factor
* Omit: Keep original coordinates (Angstroms)

Examples
--------

Single Molecule Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Quick view
   chemvista --xyz water.xyz

   # Save screenshot
   chemvista --xyz water.xyz --screenshot water.png

   # Export to GLB
   chemvista --xyz water.xyz --glb water.glb

Trajectory Export for PowerPoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Basic animated export
   chemvista --xyz md_trajectory.xyz --glb-animated animation.glb

   # Optimized for presentations
   chemvista --xyz md_trajectory.xyz --glb-animated presentation.glb \
             --fps 10 --resolution 8 --cycle --scale auto

Scalar Field Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # View molecule with electron density
   chemvista --cube-mol density.cube

   # View only the isosurface
   chemvista --cube-field density.cube

   # Export to GLB
   chemvista --cube-mol density.cube --glb density.glb

Multiple Files
~~~~~~~~~~~~~~

.. code-block:: bash

   # Load multiple molecules
   chemvista --xyz mol1.xyz mol2.xyz --interactive

   # Combine trajectory with static molecule
   chemvista --xyz motor.xyz surface.xyz --glb-animated motor_scene.glb

Environment Variables
---------------------

QT_QPA_PLATFORM
~~~~~~~~~~~~~~~

For headless/offscreen rendering (useful on servers without display):

.. code-block:: bash

   export QT_QPA_PLATFORM=offscreen
   chemvista --xyz molecule.xyz --screenshot output.png
   chemvista --xyz trajectory.xyz --glb-animated animation.glb

Exit Codes
----------

* **0**: Success
* **1**: General error (invalid scale value, export failure, etc.)
* **2**: Invalid arguments

Getting Help
------------

.. code-block:: bash

   # Show all options
   chemvista --help

   # Show version
   chemvista --version

See Also
--------

* :doc:`gui` - Interactive GUI documentation
* :doc:`../tutorials/trajectory_export` - Tutorial on exporting animated trajectories
* :doc:`../api/exporter` - Exporter API reference
