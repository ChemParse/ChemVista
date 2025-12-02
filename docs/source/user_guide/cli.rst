Command Line Interface
======================

ChemVista provides a powerful command-line interface for quick visualization and export tasks.

Basic Usage
-----------

The general syntax is:

.. code-block:: bash

   chemvista [OPTIONS]

Common Options
--------------

File Loading
~~~~~~~~~~~~

.. code-block:: bash

   # Load XYZ file (single molecule or trajectory)
   chemvista --xyz molecule.xyz

   # Load CUBE file with molecule
   chemvista --cube-mol density.cube

   # Load CUBE file with scalar field only
   chemvista --cube-field density.cube

Visualization Modes
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Render and display (default)
   chemvista --xyz molecule.xyz

   # Launch interactive GUI
   chemvista --xyz molecule.xyz --interactive

   # Save screenshot
   chemvista --xyz molecule.xyz --screenshot output.png

Export Options
~~~~~~~~~~~~~~

.. code-block:: bash

   # Export to GLB format
   chemvista --xyz trajectory.xyz --export output.glb

   # Export with custom settings
   chemvista --xyz trajectory.xyz --export output.glb --fps 20 --resolution 5

Examples
--------

Single Molecule
~~~~~~~~~~~~~~~

Visualize a single molecular structure:

.. code-block:: bash

   chemvista --xyz water.xyz

Molecular Trajectory
~~~~~~~~~~~~~~~~~~~~

View and export a molecular dynamics trajectory:

.. code-block:: bash

   # View trajectory interactively
   chemvista --xyz md_trajectory.xyz --interactive

   # Export as animated GLB for PowerPoint
   chemvista --xyz md_trajectory.xyz --export animation.glb --fps 10

Scalar Fields
~~~~~~~~~~~~~

Visualize electron density or other scalar fields:

.. code-block:: bash

   # Show molecule with scalar field
   chemvista --cube-mol density.cube

   # Show only the scalar field isosurface
   chemvista --cube-field density.cube

Advanced Usage
--------------

Quality Control
~~~~~~~~~~~~~~~

Control the mesh resolution for exports:

.. code-block:: bash

   # High quality (more triangles, larger file)
   chemvista --xyz trajectory.xyz --export high.glb --resolution 20

   # Low quality (fewer triangles, smaller file)
   chemvista --xyz trajectory.xyz --export low.glb --resolution 5

Animation Settings
~~~~~~~~~~~~~~~~~~

Customize animation parameters:

.. code-block:: bash

   # Set frames per second
   chemvista --xyz trajectory.xyz --export output.glb --fps 30

   # Enable cycling (loop animation)
   chemvista --xyz trajectory.xyz --export output.glb --cycle

Combined Options
~~~~~~~~~~~~~~~~

Multiple options can be combined:

.. code-block:: bash

   chemvista --xyz trajectory.xyz \\
             --export output.glb \\
             --fps 15 \\
             --resolution 8 \\
             --cycle \\
             --screenshot preview.png

Environment Variables
---------------------

QT_QPA_PLATFORM
~~~~~~~~~~~~~~~

For headless rendering:

.. code-block:: bash

   export QT_QPA_PLATFORM=offscreen
   chemvista --xyz molecule.xyz --screenshot output.png

Exit Codes
----------

* **0**: Success
* **1**: General error
* **2**: Invalid arguments
* **3**: File not found
* **4**: Rendering error

Getting Help
------------

Display help information:

.. code-block:: bash

   # Show all options
   chemvista --help

   # Show version
   chemvista --version
