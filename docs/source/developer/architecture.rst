Architecture Overview
=====================

ChemVista follows a hierarchical scene graph architecture inspired by 3D engines, with clear separation between data models, rendering, and UI.

Core Design Patterns
--------------------

Hierarchical Scene Graph
~~~~~~~~~~~~~~~~~~~~~~~~~

The central architectural pattern is a tree structure for organizing chemical objects:

**TreeNode** (``tree_structure.py``)
   Generic tree node with:

   * UUID-based identification
   * Parent/child relationships
   * Visibility propagation
   * Qt signals for GUI updates

**SceneObject** (``scene_objects.py``)
   Extends TreeNode for renderable chemical objects:

   * ``MoleculeObject``: Can have ``ScalarFieldObject`` children
   * ``TrajectoryObject``: Can have ``MoleculeObject`` children
   * ``ScalarFieldObject``: Leaf node, no children

**SceneManager** (``scene_manager.py``)
   Manages scene graph root and provides high-level operations:

   * Loading files (XYZ, CUBE)
   * Rendering coordination
   * Object manipulation

Tree Structure Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hierarchy rules enforced by ``_can_add_child()`` methods:

.. code-block:: python

   MoleculeObject
   └── ScalarFieldObject  # Only scalar fields allowed

   TrajectoryObject
   └── MoleculeObject  # Only molecules allowed
       └── ScalarFieldObject

   ScalarFieldObject  # No children allowed

**Bidirectional Synchronization:**

When scene objects are modified, corresponding nx_ase data structures are automatically updated:

* Adding ``ScalarFieldObject`` → adds to ``molecule.scalar_fields``
* Reordering trajectory frames → reorders ``Trajectory.images`` list

Component Architecture
----------------------

Data Layer
~~~~~~~~~~

**nx_ase Library** (external dependency):

* ``Molecule``: ASE Atoms wrapper with NetworkX graph for bonds
* ``ScalarField``: 3D grid data (electron density, etc.)
* ``Trajectory``: List of molecules (animation frames)

Repository: https://github.com/imtambovtcev/nx_ase.git

Rendering Layer
~~~~~~~~~~~~~~~

**Stateless Renderer Pattern:**

Renderers convert data + settings → PyVista meshes:

.. code-block:: python

   class MoleculeRenderer(Renderer):
       def render(self, molecule, plotter, settings):
           # Creates PyVista spheres for atoms
           # Creates PyVista cylinders for bonds
           # Adds meshes to plotter

   class ScalarFieldRenderer(Renderer):
       def render(self, field, plotter, settings):
           # Creates structured grid
           # Generates isosurface contours
           # Adds meshes to plotter

**Key Point:** Renderers are stateless - same inputs always produce same outputs.

Settings Management
~~~~~~~~~~~~~~~~~~~

Each object type has associated settings (dataclasses in ``render_settings.py``):

.. code-block:: python

   @dataclass
   class MoleculeRenderSettings:
       show_atoms: bool = True
       show_bonds: bool = True
       show_hydrogens: bool = True
       resolution: int = 10
       alpha: float = 1.0

Changes to settings emit ``render_changed`` signal for GUI updates.

Export Layer
~~~~~~~~~~~~

**Two Export Strategies:**

1. **Static Export** (Trimesh-based):

   * For single molecules, scalar fields
   * Vertex colors + PBR materials
   * Supports transparency (BLEND mode)

2. **Animated Export** (Skeletal Animation):

   * For molecular trajectories
   * Custom glTF 2.0 generation
   * PowerPoint-compatible
   * Bones per atom, bonds stretch/compress

GUI Architecture
----------------

Qt Integration
~~~~~~~~~~~~~~

**Main Components:**

.. code-block:: text

   ChemVistaApp (QMainWindow)
   ├── MenuBar (File, View, Export menus)
   ├── SceneWidget (QWidget wrapping QtInteractor)
   │   └── QtInteractor (PyVista's Qt integration)
   ├── ObjectTreeWidget (QTreeView)
   │   └── ObjectTreeModel (QAbstractItemModel)
   └── SettingsDialog (QDialog)

**Signal Flow:**

.. code-block:: text

   User Action → Qt Signal → SceneManager Method
        ↓
   TreeSignals Emitted
        ↓
   GUI Widgets React (via Qt slots)

TreeSignals Pattern
~~~~~~~~~~~~~~~~~~~

Separate QObject for tree signals to avoid multiple inheritance:

.. code-block:: python

   class TreeSignals(QObject):
       child_added = pyqtSignal(object, object)
       child_removed = pyqtSignal(object, object)
       visibility_changed = pyqtSignal(object, bool)
       render_changed = pyqtSignal(object)

This allows headless operation without Qt dependencies.

Testing Architecture
--------------------

Headless Testing
~~~~~~~~~~~~~~~~

Tests run without display using:

.. code-block:: python

   # conftest.py
   os.environ["QT_QPA_PLATFORM"] = "offscreen"
   pv.OFF_SCREEN = True

**MockQtInteractor:**

Replaces real QtInteractor in tests to avoid VTK render window creation:

.. code-block:: python

   @pytest.fixture
   def chem_vista_app(qapp, qtbot, test_files):
       with patch('chemvista.gui.scene.QtInteractor', MockQtInteractor):
           app = ChemVistaApp()
           yield app
           app.close()

Fixtures
~~~~~~~~

Key fixtures in ``conftest.py``:

* ``qapp``: Session-scoped QApplication
* ``qtbot``: PyQt test helpers
* ``test_files``: Paths to test data (XYZ/CUBE)
* ``test_objects``: Pre-loaded nx_ase objects
* ``chem_vista_app``: Mocked ChemVistaApp

Module Structure
----------------

.. code-block:: text

   chemvista/
   ├── __init__.py
   ├── cli.py                 # Command-line interface
   ├── scene_manager.py       # Scene graph management
   ├── scene_objects.py       # Object types (Molecule, Trajectory, etc.)
   ├── tree_structure.py      # Generic tree node implementation
   ├── exporter.py            # GLB export (static & animated)
   ├── renderer/
   │   ├── base.py           # Base renderer class
   │   ├── molecule.py       # Molecule rendering
   │   ├── scalar_field.py   # Scalar field rendering
   │   └── render_settings.py  # Settings dataclasses
   └── gui/
       ├── main_window.py    # Main application window
       ├── scene.py          # 3D viewport widget
       ├── qt_utils.py       # Qt environment setup
       └── widgets/
           ├── object_tree/  # Tree view with drag-drop
           └── settings_dialog.py  # Property editors

Key Algorithms
--------------

Skeletal Animation Export
~~~~~~~~~~~~~~~~~~~~~~~~~

**Challenge:** Create PowerPoint-compatible animated 3D models from trajectory data.

**Solution:** Use glTF 2.0 skeletal animation with one bone per atom.

**Algorithm:**

1. Create sphere geometry for each atom (bind pose = first frame)
2. Assign vertices to bones (one bone per atom sphere)
3. Create bond cylinders with two-bone skinning:

   * Project each bond vertex onto bond axis
   * Interpolate weights: ``weight_a = 1 - t``, ``weight_b = t``
   * Where ``t`` is normalized position along bond axis

4. Create inverse bind matrices: ``translate(-atom_position)``
5. Create animation tracks (translation per bone per frame)
6. Serialize to binary glTF format

**Key Innovation:** Axis-based linear interpolation for bonds ensures they stretch/compress correctly without rotation artifacts.

Vertex Concatenation
~~~~~~~~~~~~~~~~~~~~~

**Challenge:** PyVista's ``merge()`` deduplicates vertices, breaking index calculations.

**Solution:** Manual concatenation without deduplication:

.. code-block:: python

   all_vertices = []
   all_faces = []
   vertex_offset = 0

   for mesh in meshes:
       all_vertices.append(mesh.points)
       faces = mesh.faces + vertex_offset
       all_faces.append(faces)
       vertex_offset += len(mesh.points)

   combined_vertices = np.vstack(all_vertices)
   combined_faces = np.vstack(all_faces)

This ensures predictable vertex indices for skinning assignment.

Visibility Propagation
~~~~~~~~~~~~~~~~~~~~~~~

When node visibility changes, all descendants inherit the state:

.. code-block:: python

   def set_visible(self, visible: bool):
       self._visible = visible
       # Propagate to children
       for child in self.children:
           child.set_visible(visible)
       self.signals.visibility_changed.emit(self, visible)

Efficient iteration over visible nodes:

.. code-block:: python

   def iter_visible(self):
       if self.visible:
           yield self
           for child in self.children:
               yield from child.iter_visible()

Design Decisions
----------------

Why Scene Graph?
~~~~~~~~~~~~~~~~

**Alternatives considered:**

* Flat list of objects
* Dictionary/registry pattern

**Chosen:** Hierarchical tree

**Rationale:**

* Natural representation of trajectory structure (trajectory → frames → scalar fields)
* Visibility/transform propagation built-in
* Familiar to 3D graphics programmers
* Supports complex molecular assemblies

Why Stateless Renderers?
~~~~~~~~~~~~~~~~~~~~~~~~~

**Alternatives:**

* Renderers cache meshes
* Objects render themselves

**Chosen:** Stateless render functions

**Rationale:**

* Simpler to test (pure functions)
* No state management complexity
* Easier to parallelize (if needed)
* Clear separation: data vs. visualization

Why Two Export Modes?
~~~~~~~~~~~~~~~~~~~~~~

**Why not unify?**

Static and animated exports serve different purposes:

**Static Export:**

* Optimized for static scenes
* Vertex colors for precise control
* Supports transparency blending
* Smaller files for non-animated content

**Animated Export:**

* Specialized for trajectories
* Skeletal animation for PowerPoint
* Bone-based deformation
* Different optimization trade-offs

**Attempting to unify would compromise both use cases.**

Future Architecture Considerations
-----------------------------------

Potential Enhancements
~~~~~~~~~~~~~~~~~~~~~~

1. **Plugin System:** Allow custom renderers/exporters
2. **Undo/Redo:** Command pattern for scene modifications
3. **Serialization:** Save/load scene state
4. **Scripting API:** Python console in GUI
5. **Parallel Rendering:** Multi-threaded render pipeline

Scalability Limits
~~~~~~~~~~~~~~~~~~

Current architecture handles:

* **Molecules:** Up to ~10,000 atoms tested
* **Trajectories:** Up to ~1000 frames tested
* **Scalar Fields:** Up to 200³ grid tested

For larger systems, consider:

* Level-of-detail (LOD) rendering
* Culling invisible objects
* Streaming/pagination for trajectories
* GPU-accelerated rendering (VTK/OpenGL)
