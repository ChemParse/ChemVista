Supported File Formats
======================

ChemVista supports standard computational chemistry file formats for molecular structures and scalar fields.

Input Formats
-------------

XYZ Files
~~~~~~~~~

**Extension:** ``.xyz``

**Description:** Standard molecular coordinate format

**Single Molecule:**

.. code-block:: text

   3
   Water molecule
   O  0.000  0.000  0.000
   H  0.757  0.586  0.000
   H -0.757  0.586  0.000

**Trajectory (Multiple Frames):**

.. code-block:: text

   3
   Frame 1
   O  0.000  0.000  0.000
   H  0.757  0.586  0.000
   H -0.757  0.586  0.000
   3
   Frame 2
   O  0.010  0.005  0.000
   H  0.760  0.590  0.000
   H -0.750  0.590  0.000

**Loading in ChemVista:**

.. code-block:: python

   from chemvista.scene_manager import SceneManager

   scene_manager = SceneManager()

   # Returns MoleculeObject for single frame
   # Returns TrajectoryObject for multiple frames
   obj = scene_manager.load_xyz("molecule.xyz")

CUBE Files
~~~~~~~~~~

**Extension:** ``.cube``

**Description:** Gaussian cube format for volumetric data (electron density, electrostatic potential, etc.)

**Structure:**

.. code-block:: text

   Electron Density
   Calculated with Gaussian
   47    0.000    0.000    0.000    # Natoms, origin
   40    0.283    0.000    0.000    # Nx, voxel_x
   40    0.000    0.283    0.000    # Ny, voxel_y
   40    0.000    0.000    0.283    # Nz, voxel_z
   6     6.000    0.000    0.000    0.000  # Atom: number, charge, x, y, z
   ...
   # Volumetric data follows

**Loading Options:**

.. code-block:: python

   # Load molecule with scalar field
   mol_obj = scene_manager.load_molecule_from_cube("density.cube")
   # Returns MoleculeObject with ScalarFieldObject child

   # Load only scalar field
   field_obj = scene_manager.load_scalar_field_from_cube("density.cube")
   # Returns standalone ScalarFieldObject

Output Formats
--------------

GLB Format
~~~~~~~~~~

**Extension:** ``.glb``

**Description:** Binary glTF 2.0 format for 3D models

**Two Export Modes:**

1. **Static Export** - For single molecules and scalar fields

   .. code-block:: python

      exporter.export_glb("static_scene.glb")

   **Features:**

   * Vertex colors preserved
   * Transparency support (BLEND mode)
   * Multiple materials (opaque/transparent)
   * Suitable for static molecular structures with scalar fields

2. **Animated Export** - For molecular trajectories

   .. code-block:: python

      exporter.export_trajectory_animated_glb(
          trajectory_object=traj,
          output_path="animated.glb",
          fps=10,
          resolution=5,
          cycle_animation=True
      )

   **Features:**

   * Skeletal animation (PowerPoint-compatible)
   * Atoms as bones, bonds stretch/compress
   * Adjustable frame rate and mesh quality
   * Optional animation cycling for loops

**PowerPoint Compatibility:**

GLB files can be inserted into PowerPoint:

1. Insert → 3D Models → From a File
2. Select the exported GLB file
3. Animation will play automatically for animated exports
4. Can rotate, scale, and position in slides

**Supported Viewers:**

* Microsoft PowerPoint
* Windows 3D Viewer
* Blender
* Online viewers (e.g., gltf-viewer.donmccurdy.com)
* Three.js applications

PNG/JPG Screenshots
~~~~~~~~~~~~~~~~~~~

**Extensions:** ``.png``, ``.jpg``

**Description:** 2D raster images of rendered view

.. code-block:: python

   # From Python API
   plotter.screenshot("output.png")

   # From CLI
   chemvista --xyz molecule.xyz --screenshot output.png

File Format Details
-------------------

XYZ Format Specification
~~~~~~~~~~~~~~~~~~~~~~~~~

**Line 1:** Number of atoms (integer)

**Line 2:** Comment line (optional, can be empty)

**Lines 3+:** Atom data

Each atom line contains:

* **Element Symbol** (string): Chemical element
* **X coordinate** (float): Angstroms
* **Y coordinate** (float): Angstroms
* **Z coordinate** (float): Angstroms

**Notes:**

* Coordinates are in Angstroms by default
* Element symbols are case-sensitive (first letter uppercase)
* Multiple frames are concatenated (no separator)

CUBE Format Specification
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Header:**

* Line 1-2: Comment lines
* Line 3: Number of atoms, origin coordinates
* Lines 4-6: Grid dimensions and voxel vectors
* Lines 7+: Atom data (atomic number, charge, coordinates)

**Body:**

* Volumetric data in row-major order
* Values typically in atomic units
* Can represent various scalar fields (density, potential, etc.)

**Notes:**

* ChemVista converts coordinates to Angstroms
* Grid data is stored in fortran order (column-major)
* Supports positive and negative isovalues

GLB Format Specification
~~~~~~~~~~~~~~~~~~~~~~~~~

ChemVista exports conform to glTF 2.0 specification:

**Binary Structure:**

1. **12-byte header**: Magic number, version, length
2. **JSON chunk**: Scene structure, materials, animations
3. **Binary chunk**: Vertex data, indices, textures

**Skeletal Animation Structure:**

* **Nodes**: Scene hierarchy (root, mesh, skeleton)
* **Meshes**: Geometry with skinning attributes (JOINTS_0, WEIGHTS_0)
* **Skins**: Bone hierarchy and inverse bind matrices
* **Animations**: Keyframe data for bone transformations

**Materials:**

* **Opaque**: ``alphaMode: "OPAQUE"``
* **Transparent**: ``alphaMode: "BLEND"``
* **Vertex colors**: COLOR_0 attribute

Best Practices
--------------

Choosing Export Format
~~~~~~~~~~~~~~~~~~~~~~~

**Use Static GLB when:**

* Exporting single molecular structures
* Including scalar field isosurfaces
* Need transparency support
* Target is 3D viewer or web application

**Use Animated GLB when:**

* Exporting molecular dynamics trajectories
* Need animation in PowerPoint
* Want bonds to stretch/compress
* Trajectory shows conformational changes

Quality vs. File Size
~~~~~~~~~~~~~~~~~~~~~

**High Quality** (resolution=20):

* Smooth spheres and cylinders
* Larger file size (2-5x)
* Use for: Publication figures, close-up views

**Medium Quality** (resolution=10):

* Good balance
* Default setting
* Use for: General visualization, presentations

**Low Quality** (resolution=5):

* Smaller file size (70% reduction)
* Visible facets on close inspection
* Use for: Large molecules, web sharing, quick previews

Animation Tips
~~~~~~~~~~~~~~

* Use ``cycle_animation=True`` for seamless loops
* Adjust FPS based on motion speed (10-30 typical)
* Lower resolution for large molecules (>100 atoms)
* Test in PowerPoint before finalizing settings
