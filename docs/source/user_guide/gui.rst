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

* **Open XYZ**: Load molecular structure or trajectory
* **Open CUBE (Molecule)**: Load CUBE file with molecule
* **Open CUBE (Field)**: Load CUBE file with scalar field only
* **Export GLB**: Export scene to GLB format
* **Export Animated GLB**: Export trajectory with skeletal animation
* **Exit**: Close application

View Menu
~~~~~~~~~

* **Reset Camera**: Reset view to default
* **Toggle Axes**: Show/hide coordinate axes
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

Export Dialog
-------------

When exporting, a dialog provides options:

Static Export (GLB)
~~~~~~~~~~~~~~~~~~~

* **Output Path**: Destination file
* **Include Transparency**: Preserve alpha values
* **Combine Meshes**: Merge all objects

Animated Export (GLB)
~~~~~~~~~~~~~~~~~~~~~

* **Output Path**: Destination file
* **FPS**: Frames per second (default: 10)
* **Resolution**: Mesh quality (1-20, default: 10)
* **Cycle Animation**: Add reverse frames for looping
* **Include Bonds**: Export bond cylinders

Keyboard Shortcuts
------------------

Global
~~~~~~

* **Ctrl+O**: Open file
* **Ctrl+S**: Export scene
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

* Lower resolution for large molecules
* Hide objects not currently needed
* Use "Show Hydrogens: False" for cleaner view

Quality
~~~~~~~

* Increase resolution for publication-quality renders
* Use anti-aliasing for smoother edges
* Adjust lighting for better depth perception

Workflow
~~~~~~~~

1. Load your molecular data
2. Adjust visualization settings in property panel
3. Arrange view with mouse controls
4. Take screenshot or export to GLB
5. Import GLB into PowerPoint or other tools
