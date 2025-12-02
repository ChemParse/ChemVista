Scene Manager API
=================

The SceneManager is the central coordinator for ChemVista scenes, managing the scene graph and orchestrating rendering.

.. module:: chemvista.scene_manager

SceneManager Class
------------------

.. autoclass:: chemvista.scene_manager.SceneManager
   :members:
   :undoc-members:
   :show-inheritance:

   .. automethod:: __init__

File Loading Methods
---------------------

load_xyz
~~~~~~~~

.. automethod:: chemvista.scene_manager.SceneManager.load_xyz

Load molecular structures or trajectories from XYZ files.

**Returns:**

* **Single frame**: Returns ``MoleculeObject``
* **Multiple frames**: Returns ``TrajectoryObject`` with ``MoleculeObject`` children

**Example:**

.. code-block:: python

   scene_manager = SceneManager()

   # Load single molecule
   molecule = scene_manager.load_xyz("water.xyz")
   print(f"Loaded {len(molecule.molecule)} atoms")

   # Load trajectory
   trajectory = scene_manager.load_xyz("md_simulation.xyz")
   print(f"Loaded {len(trajectory.children)} frames")

load_molecule_from_cube
~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: chemvista.scene_manager.SceneManager.load_molecule_from_cube

Load CUBE file including both molecule and scalar field.

**Returns:** ``MoleculeObject`` with ``ScalarFieldObject`` child

**Example:**

.. code-block:: python

   # Load electron density with molecule
   mol = scene_manager.load_molecule_from_cube("density.cube")

   # Access scalar field
   scalar_field = mol.children[0]  # First child
   print(f"Grid dimensions: {scalar_field.scalar_field.grid_shape}")

load_scalar_field_from_cube
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: chemvista.scene_manager.SceneManager.load_scalar_field_from_cube

Load CUBE file with scalar field only (no molecule).

**Returns:** ``ScalarFieldObject``

**Example:**

.. code-block:: python

   # Load only the scalar field
   field = scene_manager.load_scalar_field_from_cube("density.cube")
   print(f"Isosurface values: {field.render_settings.isosurface_values}")

Rendering Methods
-----------------

render
~~~~~~

.. automethod:: chemvista.scene_manager.SceneManager.render

Render all visible objects in the scene to a PyVista plotter.

**Example:**

.. code-block:: python

   import pyvista as pv

   # Create plotter
   plotter = pv.Plotter()

   # Render scene
   scene_manager.render(plotter)

   # Show
   plotter.show()

Scene Graph Access
------------------

root
~~~~

.. autoattribute:: chemvista.scene_manager.SceneManager.root

The root node of the scene tree. All loaded objects are children of this node.

**Example:**

.. code-block:: python

   # Iterate all objects
   for obj in scene_manager.root.children:
       print(f"Object: {obj.name}, Type: {type(obj).__name__}")

   # Iterate only visible objects
   for obj in scene_manager.root.iter_visible():
       print(f"Visible: {obj.name}")

molecule_renderer
~~~~~~~~~~~~~~~~~

.. autoattribute:: chemvista.scene_manager.SceneManager.molecule_renderer

Instance of ``MoleculeRenderer`` used for rendering molecules.

scalar_field_renderer
~~~~~~~~~~~~~~~~~~~~~

.. autoattribute:: chemvista.scene_manager.SceneManager.scalar_field_renderer

Instance of ``ScalarFieldRenderer`` used for rendering scalar fields.

Object Manipulation
-------------------

Finding Objects
~~~~~~~~~~~~~~~

Objects can be found by UUID or by iteration:

.. code-block:: python

   # By UUID
   obj = scene_manager.root.get_object_by_uuid(uuid)

   # By name (iterate and filter)
   for obj in scene_manager.root.children:
       if obj.name == "Water":
           print(f"Found: {obj}")

   # By type
   molecules = [obj for obj in scene_manager.root.children
                if isinstance(obj, MoleculeObject)]

Removing Objects
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Remove specific object
   molecule.parent.remove_child(molecule)

   # Remove by UUID
   obj = scene_manager.root.get_object_by_uuid(uuid)
   if obj:
       obj.parent.remove_child(obj)

   # Clear all
   for child in list(scene_manager.root.children):
       scene_manager.root.remove_child(child)

Visibility Control
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Hide object
   molecule.set_visible(False)

   # Show object
   molecule.set_visible(True)

   # Toggle
   molecule.set_visible(not molecule.visible)

   # Hide all
   for obj in scene_manager.root.children:
       obj.set_visible(False)

Usage Patterns
--------------

Basic Workflow
~~~~~~~~~~~~~~

.. code-block:: python

   from chemvista.scene_manager import SceneManager
   import pyvista as pv

   # 1. Create scene manager
   scene_manager = SceneManager()

   # 2. Load data
   molecule = scene_manager.load_xyz("molecule.xyz")

   # 3. Adjust settings
   molecule.render_settings.show_hydrogens = False
   molecule.render_settings.resolution = 15

   # 4. Render
   plotter = pv.Plotter()
   scene_manager.render(plotter)
   plotter.show()

Multiple Objects
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Load multiple files
   mol1 = scene_manager.load_xyz("protein.xyz")
   mol2 = scene_manager.load_xyz("ligand.xyz")
   field = scene_manager.load_scalar_field_from_cube("density.cube")

   # Rename for clarity
   mol1.name = "Protein"
   mol2.name = "Ligand"
   field.name = "Electron Density"

   # Adjust settings independently
   mol1.render_settings.alpha = 0.5  # Semi-transparent
   mol2.render_settings.resolution = 20  # High quality

   # Render all visible objects
   plotter = pv.Plotter()
   scene_manager.render(plotter)
   plotter.show()

Trajectory Workflow
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Load trajectory
   trajectory = scene_manager.load_xyz("dynamics.xyz")

   print(f"Trajectory: {len(trajectory.children)} frames")

   # Access individual frames
   first_frame = trajectory.children[0]
   last_frame = trajectory.children[-1]

   # Modify visibility
   for i, frame in enumerate(trajectory.children):
       frame.set_visible(i == 0)  # Show only first frame

   # Export to animated GLB
   from chemvista.exporter import Exporter
   exporter = Exporter(scene_manager)
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="animation.glb"
   )

See Also
--------

* :class:`chemvista.scene_objects.SceneObject` -- Base class for scene objects
* :class:`chemvista.exporter.Exporter` -- Export functionality
* :mod:`chemvista.renderer` -- Rendering modules
* :doc:`../tutorials/scene_management` -- Scene management tutorial
