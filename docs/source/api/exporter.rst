Exporter API
============

The Exporter class handles all export functionality for ChemVista, including static GLB export and animated trajectory export.

.. module:: chemvista.exporter

Exporter Class
--------------

.. autoclass:: chemvista.exporter.Exporter
   :members:
   :undoc-members:
   :show-inheritance:

   .. automethod:: __init__

Static Export Methods
---------------------

export_glb
~~~~~~~~~~

.. automethod:: chemvista.exporter.Exporter.export_glb

Export the entire scene to a static GLB file. Suitable for single molecules and scalar fields.

**Example:**

.. code-block:: python

   from chemvista.scene_manager import SceneManager
   from chemvista.exporter import Exporter

   scene_manager = SceneManager()
   scene_manager.load_xyz("molecule.xyz")

   exporter = Exporter(scene_manager)
   exporter.export_glb("output.glb")

**Features:**

* Preserves vertex colors
* Supports transparency with BLEND mode
* Multiple materials (opaque/transparent separation)
* Suitable for static molecular structures

export_scene_to_glb
~~~~~~~~~~~~~~~~~~~

.. automethod:: chemvista.exporter.Exporter.export_scene_to_glb

Convenience alias for :meth:`export_glb`.

Animated Export Methods
-----------------------

export_trajectory_animated_glb
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: chemvista.exporter.Exporter.export_trajectory_animated_glb

Export a molecular trajectory with skeletal animation. Creates PowerPoint-compatible animated 3D models.

**Parameters:**

* ``trajectory_object`` (*TrajectoryObject*) -- Trajectory to export
* ``output_path`` (*str or Path*) -- Output GLB file path
* ``fps`` (*int, optional*) -- Frames per second (default: 10)
* ``resolution`` (*int, optional*) -- Mesh resolution 1-20 (default: 10, lower = fewer triangles)
* ``cycle_animation`` (*bool, optional*) -- Add reverse frames for looping (default: False)

**Example:**

.. code-block:: python

   # Basic export
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="animation.glb"
   )

   # With options
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="animation.glb",
       fps=15,
       resolution=5,  # Low quality for smaller file
       cycle_animation=True  # Loop animation
   )

**Technical Details:**

* Uses glTF 2.0 skeletal animation
* Each atom is a bone in the skeleton
* Bonds are skinned to two bones (endpoints)
* Axis-based linear interpolation for bone weighting
* PowerPoint 2019+ compatible

Helper Methods
--------------

_collect_meshes_with_colors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: chemvista.exporter.Exporter._collect_meshes_with_colors
   :private:

Internal method that collects all visible meshes from the scene with their vertex colors.

_pv_to_trimesh
~~~~~~~~~~~~~~

.. automethod:: chemvista.exporter.Exporter._pv_to_trimesh
   :private:

Converts PyVista PolyData to trimesh.Trimesh format.

Export File Format Details
---------------------------

Static GLB Structure
~~~~~~~~~~~~~~~~~~~~

The static export uses trimesh to create glTF 2.0 files with:

**Materials:**

* **OpaqueMaterial**: ``alphaMode: "OPAQUE"`` for fully opaque meshes
* **TransparentMaterial**: ``alphaMode: "BLEND"`` for transparent meshes

**Vertex Attributes:**

* ``POSITION``: 3D coordinates (VEC3, FLOAT)
* ``COLOR_0``: RGBA colors (VEC4, UNSIGNED_BYTE, normalized)

Animated GLB Structure
~~~~~~~~~~~~~~~~~~~~~~~

The animated export creates skeletal animation with:

**Nodes:**

* Root node (parent of mesh and skeleton)
* Mesh node (references mesh and skin)
* Skeleton root (parent of all bones)
* Bone nodes (one per atom)

**Mesh Attributes:**

* ``POSITION``: Vertex positions (bind pose = first frame)
* ``COLOR_0``: Vertex colors
* ``JOINTS_0``: Bone indices (VEC4, UNSIGNED_SHORT)
* ``WEIGHTS_0``: Bone weights (VEC4, FLOAT)

**Skinning:**

* Inverse bind matrices: Transform from bone space to mesh space
* Each atom vertex: 100% weight to one bone
* Each bond vertex: Weighted between two bones (endpoint atoms)

**Animation:**

* Time keyframes: [0, 1/fps, 2/fps, ..., (n-1)/fps]
* Translation tracks: One per bone
* Interpolation: LINEAR

Exceptions
----------

.. autoexception:: ValueError
   :show-inheritance:

Raised when:

* No visible objects found in scene
* Invalid file extension (not .glb or .gltf)
* Trajectory has no frames
* Inconsistent atom counts across frames

.. autoexception:: RuntimeError
   :show-inheritance:

Raised when export operation fails.

Usage Notes
-----------

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Resolution**: Lower values dramatically reduce file size

  * resolution=20: High quality, 2-5x larger files
  * resolution=10: Default, good balance
  * resolution=5: Low quality, 70% size reduction

* **Frame Count**: More frames = larger files

  * Consider subsampling long trajectories
  * Use higher FPS to reduce duration

* **Atom Count**: More atoms = more bones = larger files

  * Use lower resolution for large molecules
  * Consider hiding hydrogen atoms

File Size Examples
~~~~~~~~~~~~~~~~~~

For a 47-atom, 10-frame trajectory:

* resolution=20, fps=10: ~2000 KB
* resolution=10, fps=10: ~600 KB
* resolution=5, fps=10: ~200 KB
* resolution=5, fps=10, cycled: ~210 KB

PowerPoint Compatibility
~~~~~~~~~~~~~~~~~~~~~~~~

* Requires PowerPoint 2019 or later
* Maximum file size: ~100 MB
* Animation plays automatically when inserted
* Only first animation in GLB file is played

See Also
--------

* :class:`chemvista.scene_manager.SceneManager` -- For loading files
* :mod:`chemvista.renderer` -- For rendering settings
* :doc:`../tutorials/trajectory_export` -- Tutorial on exporting trajectories
