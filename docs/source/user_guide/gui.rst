Graphical User Interface
========================

ChemVista provides an intuitive PyQt5-based GUI for interactive molecular visualization.

Launching the GUI
-----------------

Start the GUI from command line:

.. code-block:: bash

   # Launch with file
   chemvista --xyz molecule.xyz --interactive

   # Launch empty (load files from menu)
   chemvista --interactive

Or from Python:

.. code-block:: python

   from chemvista.gui.main_window import ChemVistaApp
   from PyQt5.QtWidgets import QApplication
   import sys

   app = QApplication(sys.argv)
   window = ChemVistaApp()
   window.show()
   sys.exit(app.exec_())

Main Window
-----------

The main window consists of:

1. **Menu Bar**: File operations, view controls, export options
2. **3D Viewport**: Interactive PyVista rendering window
3. **Object Tree**: Hierarchical view of scene objects
4. **Property Panel**: Settings for selected objects

Menu Bar
--------

File Menu
~~~~~~~~~

* **Open XYZ** (``Ctrl+O``): Load molecular structure or trajectory
* **Open CUBE (Molecule)**: Load CUBE file with molecule and scalar field
* **Open CUBE (Field)**: Load CUBE file with scalar field only
* **Export to GLB (Static)** (``Ctrl+E``): Export scene to static GLB format
* **Export to GLB (Animated)** (``Ctrl+Shift+E``): Export trajectory with skeletal animation
* **Exit** (``Ctrl+Q``): Close application

View Menu
~~~~~~~~~

* **Reset Camera** (``R``): Reset view to default
* **Toggle Axes** (``A``): Show/hide coordinate axes
* **Background Color**: Change background color
* **Rendering Quality**: Adjust mesh resolution

3D Viewport
-----------

Mouse Controls
~~~~~~~~~~~~~~

* **Left Click + Drag**: Rotate view
* **Right Click + Drag**: Pan view
* **Scroll Wheel**: Zoom in/out
* **Middle Click**: Reset view

Camera Controls
~~~~~~~~~~~~~~~

* **R**: Reset camera
* **X/Y/Z**: Align view to axis
* **S**: Take screenshot

Object Tree
-----------

The object tree shows all loaded objects in a hierarchical structure:

Tree Structure
~~~~~~~~~~~~~~

* **Root**: Scene root
  * **TrajectoryObject**: Molecular dynamics trajectory
    * **MoleculeObject**: Individual frames
      * **ScalarFieldObject**: Associated scalar fields
  * **MoleculeObject**: Standalone molecules
    * **ScalarFieldObject**: Associated scalar fields
  * **ScalarFieldObject**: Standalone scalar fields

Interactions
~~~~~~~~~~~~

* **Click**: Select object
* **Double-Click**: Edit object name
* **Right-Click**: Context menu
* **Drag & Drop**: Reorder objects (respects hierarchy rules)

Context Menu
~~~~~~~~~~~~

* **Show/Hide**: Toggle visibility
* **Remove**: Delete object
* **Properties**: Open settings dialog
* **Export**: Export selected object

Object Properties
-----------------

Each object type has specific rendering settings:

Molecule Settings
~~~~~~~~~~~~~~~~~

* **Show Atoms**: Toggle atom spheres
* **Show Bonds**: Toggle bond cylinders
* **Show Hydrogens**: Toggle hydrogen atoms
* **Atom Style**: Ball-and-stick, space-filling, etc.
* **Bond Width**: Cylinder radius for bonds
* **Resolution**: Mesh quality (higher = smoother)
* **Alpha**: Transparency (0.0 = transparent, 1.0 = opaque)

Scalar Field Settings
~~~~~~~~~~~~~~~~~~~~~

* **Isosurface Values**: List of iso-values to render
* **Colors**: Color for each isosurface
* **Opacity**: Transparency for isosurfaces
* **Smooth Surface**: Apply smoothing filter
* **Show Grid**: Display underlying grid
* **Grid Surface**: Show bounding box
* **Grid Points**: Show grid vertices

Trajectory Settings
~~~~~~~~~~~~~~~~~~~

* **Current Frame**: Select active frame
* **Play/Pause**: Animate through frames
* **Frame Rate**: Frames per second
* **Loop**: Repeat animation

Export Dialogs
--------------

Static Export (GLB)
~~~~~~~~~~~~~~~~~~~

Access via **File → Export to GLB (Static)** or ``Ctrl+E``.

Exports the current scene as a static GLB file suitable for:

* Single molecules
* Molecules with scalar field isosurfaces
* Non-animated 3D content

**Options:**

* **Output Path**: Destination file (.glb)
* **Include Transparency**: Preserve alpha values from render settings

Animated Export (GLB)
~~~~~~~~~~~~~~~~~~~~~

Access via **File → Export to GLB (Animated)** or ``Ctrl+Shift+E``.

Exports trajectories as animated GLB files with skeletal animation:

**Options:**

* **Output Path**: Destination file (.glb)
* **FPS**: Frames per second (default: 10)

  * Lower = slower playback, longer duration
  * Higher = faster playback, shorter duration

* **Resolution**: Mesh quality 1-20 (default: 10)

  * Higher = smoother spheres/cylinders, larger file
  * Lower = visible facets, smaller file
  * **File size impact:** resolution 5 is ~70% smaller than resolution 10

* **Cycle Animation**: Add reverse frames for seamless looping

  * Creates back-and-forth oscillation
  * Nearly doubles animation duration

* **Scale**: Model size normalization

  * **Auto**: Fit in 2-unit bounding box (recommended for PowerPoint)
  * **Number**: Manual scale factor
  * **None**: Keep original Angstrom coordinates

**Transparency Support:**

Each object's alpha value is preserved in the export:

* Objects with alpha=1.0 are rendered as opaque
* Objects with alpha<1.0 are rendered with transparency
* Separate meshes ensure correct rendering of mixed scenes

**Multi-Object Export:**

The animated export captures the entire visible scene:

* Multiple trajectories animate together (must have same frame count)
* Static molecules are included with fixed positions
* Each object maintains its own transparency setting

Keyboard Shortcuts
------------------

Global
~~~~~~

* **Ctrl+O**: Open XYZ file
* **Ctrl+E**: Export to GLB (static)
* **Ctrl+Shift+E**: Export to GLB (animated)
* **Ctrl+Q**: Quit application

View
~~~~

* **R**: Reset camera
* **F**: Frame selected object
* **G**: Toggle grid
* **A**: Toggle axes

Object Tree
~~~~~~~~~~~

* **Delete**: Remove selected object
* **F2**: Rename object
* **Ctrl+C**: Copy object
* **Ctrl+V**: Paste object

Tips and Tricks
---------------

Performance
~~~~~~~~~~~

* Lower resolution for large molecules (>100 atoms)
* Hide objects not currently needed
* Use "Show Hydrogens: False" for cleaner view
* For trajectories with many frames, consider using --cycle sparingly

Quality
~~~~~~~

* Increase resolution for publication-quality renders
* Use anti-aliasing for smoother edges
* Adjust lighting for better depth perception
* Resolution 8-10 is usually sufficient for presentations

Workflow
~~~~~~~~

1. Load your molecular data
2. Adjust visualization settings in property panel
3. Set transparency for different objects if needed
4. Arrange view with mouse controls
5. Take screenshot or export to GLB
6. Import GLB into PowerPoint or other 3D viewers

PowerPoint Integration
~~~~~~~~~~~~~~~~~~~~~~

For best results when using exported GLB files in PowerPoint:

1. Use ``--scale auto`` or set Scale to "Auto" in the dialog
2. Resolution 8-10 provides good balance of quality and file size
3. Enable "Cycle Animation" for looping presentations
4. PowerPoint 2019 or later required for 3D model support
5. Maximum file size ~100 MB

Troubleshooting
---------------

Animation Not Playing
~~~~~~~~~~~~~~~~~~~~~

* Ensure PowerPoint 2019 or later
* Check file size is under 100 MB
* Verify the GLB file opens in other viewers (e.g., Windows 3D Viewer)

Objects Not Visible After Export
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Check object visibility in the Object Tree before export
* Hidden objects are not included in exports

Transparency Issues
~~~~~~~~~~~~~~~~~~~

* Ensure alpha values are set correctly in Molecule Settings
* The exporter creates separate meshes for opaque and transparent objects
* Some viewers may not support transparency correctly

See Also
--------

* :doc:`cli` - Command line interface documentation
* :doc:`../tutorials/trajectory_export` - Tutorial on exporting animated trajectories
* :doc:`../api/exporter` - Exporter API reference
