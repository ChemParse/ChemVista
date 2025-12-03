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

export_animated_glb
~~~~~~~~~~~~~~~~~~~

.. automethod:: chemvista.exporter.Exporter.export_animated_glb

Export the entire visible scene as an animated GLB file. This is the **recommended method** for exporting trajectories as it handles multiple objects, transparency, and scene-based export.

**Parameters:**

* ``output_path`` (*str or Path*) -- Output GLB file path
* ``fps`` (*int, optional*) -- Frames per second (default: 10)
* ``resolution`` (*int, optional*) -- Mesh resolution 1-20 (default: 10)
* ``cycle_animation`` (*bool, optional*) -- Add reverse frames for looping (default: False)
* ``scale`` (*str or float, optional*) -- Scale factor. Use ``"auto"`` to fit in 2-unit box, or a number.

**Example:**

.. code-block:: python

   from chemvista.scene_manager import SceneManager
   from chemvista.exporter import Exporter

   # Load trajectory
   scene_manager = SceneManager()
   scene_manager.load_xyz("trajectory.xyz")

   # Export with options
   exporter = Exporter(scene_manager)
   exporter.export_animated_glb(
       output_path="animation.glb",
       fps=15,
       resolution=8,
       cycle_animation=True,
       scale="auto"
   )

**Features:**

* Exports entire visible scene (all trajectories and molecules)
* Multiple trajectories animated together (must have same frame count)
* Static molecules included with fixed positions
* Per-object transparency with separate opaque/transparent meshes
* Automatic scaling to fit viewer expectations

export_trajectory_animated_glb
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: chemvista.exporter.Exporter.export_trajectory_animated_glb

Export a single trajectory with skeletal animation. This method exports only the specified trajectory, not the entire scene.

**Parameters:**

* ``trajectory_object`` (*TrajectoryObject*) -- Trajectory to export
* ``output_path`` (*str or Path*) -- Output GLB file path
* ``fps`` (*int, optional*) -- Frames per second (default: 10)
* ``resolution`` (*int, optional*) -- Mesh resolution 1-20 (default: 10)
* ``cycle_animation`` (*bool, optional*) -- Add reverse frames for looping (default: False)
* ``scale`` (*str or float, optional*) -- Scale factor. Use ``"auto"`` or a number.

**Example:**

.. code-block:: python

   # Export single trajectory
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="animation.glb",
       fps=15,
       resolution=5,
       cycle_animation=True,
       scale="auto"
   )

.. note::

   For most use cases, prefer :meth:`export_animated_glb` which handles the entire scene automatically.

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

* Root node (parent of skeleton and mesh nodes)
* Skeleton root (parent of all bones)
* Bone nodes (one per atom across all objects)
* Mesh nodes (opaque and/or transparent, sharing the skeleton)

**Meshes:**

The exporter creates separate meshes for different transparency levels:

* **OpaqueMesh**: Faces from objects with alpha=1.0, ``alphaMode: "OPAQUE"``
* **TransparentMesh**: Faces from objects with alpha<1.0, ``alphaMode: "BLEND"``

Both meshes share the same vertex data and skeleton.

**Mesh Attributes:**

* ``POSITION``: Vertex positions (bind pose = first frame)
* ``COLOR_0``: Vertex colors with per-object alpha
* ``JOINTS_0``: Bone indices (VEC4, UNSIGNED_SHORT)
* ``WEIGHTS_0``: Bone weights (VEC4, FLOAT)

**Skinning:**

* Inverse bind matrices: Transform from bone space to mesh space (column-major order)
* Atom vertices: 100% weight to corresponding bone
* Bond vertices: Weighted between two endpoint atom bones using axis-based linear interpolation

**Animation:**

* Time keyframes: [0, 1/fps, 2/fps, ..., (n-1)/fps]
* Translation tracks: One per bone
* Interpolation: LINEAR
* All bones animated (static molecules repeat position for all frames)

Transparency Handling
~~~~~~~~~~~~~~~~~~~~~

Per-object transparency is preserved:

1. Each object's ``render_settings.alpha`` value is applied to its geometry
2. Faces are grouped by their alpha value (opaque vs transparent)
3. Separate meshes are created for each group
4. Both meshes share the same skeleton and animate together

This ensures opaque objects render correctly without being affected by transparent objects.

Scale Parameter
~~~~~~~~~~~~~~~

The ``scale`` parameter normalizes model size:

* ``scale=None``: No scaling, coordinates in original units (typically Ångströms)
* ``scale="auto"``: Auto-scale to fit in 2-unit bounding box
* ``scale=0.1``: Manual scale factor (multiply all coordinates)

Scaling is applied to:

* Vertex positions
* Atom radii
* Animation translation data

Exceptions
----------

.. autoexception:: ValueError
   :show-inheritance:

Raised when:

* No visible objects found in scene
* Invalid file extension (not .glb or .gltf)
* Trajectory has no frames
* Inconsistent atom counts across frames
* Multiple trajectories with different frame counts

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

CLI Integration
~~~~~~~~~~~~~~~

The exporter is integrated with the CLI:

.. code-block:: bash

   # Static export
   chemvista --xyz molecule.xyz --glb output.glb

   # Animated export
   chemvista --xyz trajectory.xyz --glb-animated output.glb \
             --fps 15 --resolution 8 --cycle --scale auto

GUI Integration
~~~~~~~~~~~~~~~

Export is available from the GUI menu:

* **File → Export to GLB (Static)** or ``Ctrl+E``
* **File → Export to GLB (Animated)** or ``Ctrl+Shift+E``

The animated export dialog allows configuration of FPS, resolution, cycling, and scale.

See Also
--------

* :class:`chemvista.scene_manager.SceneManager` -- For loading files
* :mod:`chemvista.renderer` -- For rendering settings
* :doc:`../tutorials/trajectory_export` -- Tutorial on exporting trajectories
