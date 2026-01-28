Exporting Animated Trajectories
================================

This tutorial covers exporting molecular dynamics trajectories as animated GLB files for PowerPoint and other 3D viewers.

Overview
--------

ChemVista uses **skeletal animation** to create PowerPoint-compatible animated 3D models. Each atom becomes a "bone" in a skeleton, and the bone positions are animated through the trajectory frames. Bonds automatically stretch and compress as atoms move using two-bone skinning with linear interpolation along the bond axis.

Key Features
~~~~~~~~~~~~

* **Skeletal animation** - One bone per atom, bonds skinned to endpoint atoms
* **Multi-object support** - Export multiple trajectories and molecules together
* **Per-object transparency** - Different objects can have different alpha values
* **Automatic scaling** - Fit models to standard viewer sizes
* **Seamless looping** - Create back-and-forth animations

Basic Export
------------

Using the CLI
~~~~~~~~~~~~~

The simplest way to export an animated trajectory:

.. code-block:: bash

   # Basic animated export
   chemvista --xyz trajectory.xyz --glb-animated output.glb

   # With all options
   chemvista --xyz trajectory.xyz --glb-animated output.glb \
             --fps 15 \
             --resolution 8 \
             --cycle \
             --scale auto

Using Python API
~~~~~~~~~~~~~~~~

.. code-block:: python

   from chemvista.scene_manager import SceneManager
   from chemvista.exporter import Exporter

   # Create scene manager and load trajectory
   scene_manager = SceneManager()
   trajectory = scene_manager.load_xyz("md_trajectory.xyz")

   print(f"Loaded {len(trajectory.children)} frames")

   # Create exporter and export
   exporter = Exporter(scene_manager)
   exporter.export_animated_glb(
       output_path="animation.glb",
       fps=10,
       resolution=10
   )

Using in PowerPoint
~~~~~~~~~~~~~~~~~~~

1. Open PowerPoint (2019 or later)
2. Insert → 3D Models → From a File
3. Select ``animation.glb``
4. Animation plays automatically!

Export Options
--------------

Resolution
~~~~~~~~~~

Controls mesh quality (spheres and cylinders):

.. code-block:: bash

   # High quality (smooth spheres, larger file)
   chemvista --xyz trajectory.xyz --glb-animated high.glb --resolution 20

   # Medium quality (default)
   chemvista --xyz trajectory.xyz --glb-animated medium.glb --resolution 10

   # Low quality (smaller file, visible facets)
   chemvista --xyz trajectory.xyz --glb-animated low.glb --resolution 5

**File Size Comparison (approximate):**

* resolution=20: ~2000 KB
* resolution=10: ~600 KB (70% smaller)
* resolution=5: ~200 KB (90% smaller)

Frame Rate (FPS)
~~~~~~~~~~~~~~~~

Controls animation speed:

.. code-block:: bash

   # Slow motion
   chemvista --xyz trajectory.xyz --glb-animated slow.glb --fps 5

   # Normal speed (default)
   chemvista --xyz trajectory.xyz --glb-animated normal.glb --fps 10

   # Fast motion
   chemvista --xyz trajectory.xyz --glb-animated fast.glb --fps 30

**Duration Calculation:** Duration = (Number of frames - 1) / FPS

* 10 frames at 10 fps = 0.9 seconds
* 50 frames at 10 fps = 4.9 seconds

Looping (Cycle)
~~~~~~~~~~~~~~~

Create seamless back-and-forth animations:

.. code-block:: bash

   chemvista --xyz trajectory.xyz --glb-animated looped.glb --cycle

**How it works:**

* Original: frames 1, 2, 3, 4, 5
* Cycled: frames 1, 2, 3, 4, 5, 4, 3, 2
* Avoids duplicates at loop points
* Creates smooth oscillating motion

Scale
~~~~~

Normalize model size for viewers:

.. code-block:: bash

   # Auto-scale to fit in 2-unit bounding box
   chemvista --xyz trajectory.xyz --glb-animated scaled.glb --scale auto

   # Manual scale factor
   chemvista --xyz trajectory.xyz --glb-animated scaled.glb --scale 0.1

**Why use scaling?**

* Many 3D viewers expect models in a specific size range
* ``--scale auto`` fits the model into a 2-unit box
* Useful when coordinates are in Ångströms but viewer expects nanometers

Scene-Based Export
------------------

The ``export_animated_glb`` method exports the **entire visible scene**, not just a single trajectory. This allows you to:

Multiple Trajectories
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   scene_manager = SceneManager()

   # Load multiple trajectories
   traj1 = scene_manager.load_xyz("motor.xyz")
   traj2 = scene_manager.load_xyz("substrate.xyz")

   # Both must have the same number of frames!
   # Export entire scene
   exporter = Exporter(scene_manager)
   exporter.export_animated_glb("combined.glb", fps=15)

**Important:** All trajectories must have the same number of frames.

Trajectories with Static Molecules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   scene_manager = SceneManager()

   # Load animated trajectory
   motor = scene_manager.load_xyz("motor_trajectory.xyz")

   # Load static molecule (single frame)
   surface = scene_manager.load_xyz("surface.xyz")

   # Export - motor animates, surface stays static
   exporter = Exporter(scene_manager)
   exporter.export_animated_glb("motor_on_surface.glb")

Static molecules are included with the same position for all frames.

Transparency Support
--------------------

Each object can have its own transparency (alpha) value:

.. code-block:: python

   scene_manager = SceneManager()

   # Load objects
   molecule1 = scene_manager.load_xyz("main.xyz")
   molecule2 = scene_manager.load_xyz("background.xyz")

   # Set different transparencies
   molecule1.render_settings.alpha = 1.0  # Fully opaque
   molecule2.render_settings.alpha = 0.5  # Semi-transparent

   # Export - transparency is preserved
   exporter = Exporter(scene_manager)
   exporter.export_animated_glb("with_transparency.glb")

**How it works:**

The exporter creates two separate meshes sharing the same skeleton:

1. **Opaque mesh** - All geometry with alpha=1.0, uses ``alphaMode: OPAQUE``
2. **Transparent mesh** - All geometry with alpha<1.0, uses ``alphaMode: BLEND``

This ensures opaque objects render correctly while transparent objects show proper transparency.

GUI Export
----------

Export animated GLB files from the GUI:

1. Load your trajectory/molecules
2. Adjust render settings (transparency, etc.) as desired
3. **File → Export to GLB (Animated)** or press ``Ctrl+Shift+E``
4. Configure export settings in the dialog:

   * FPS (frames per second)
   * Resolution (mesh quality)
   * Cycle animation (loop)
   * Scale factor

5. Choose output file location
6. Click Export

Complete Python Example
-----------------------

.. code-block:: python

   """
   Complete example: Export MD trajectory with optimal settings
   """
   from pathlib import Path
   from chemvista.scene_manager import SceneManager
   from chemvista.exporter import Exporter

   def export_trajectory(xyz_file, output_file, quality='medium'):
       # Load trajectory
       scene_manager = SceneManager()
       trajectory = scene_manager.load_xyz(xyz_file)

       # Check if valid trajectory
       if not hasattr(trajectory, 'children') or len(trajectory.children) < 2:
           raise ValueError("File does not contain a multi-frame trajectory")

       num_frames = len(trajectory.children)
       num_atoms = len(trajectory.children[0].molecule)

       print(f"Trajectory: {num_frames} frames, {num_atoms} atoms")

       # Set resolution based on quality
       resolution_map = {
           'high': 20,
           'medium': 10,
           'low': 5
       }
       resolution = resolution_map.get(quality, 10)

       # Export
       exporter = Exporter(scene_manager)
       exporter.export_animated_glb(
           output_path=output_file,
           fps=10,
           resolution=resolution,
           cycle_animation=True,
           scale="auto"
       )

       # Report file size
       file_size = Path(output_file).stat().st_size / 1024
       duration = (num_frames * 2 - 2) / 10  # *2 for cycling
       print(f"Exported: {output_file}")
       print(f"  Size: {file_size:.1f} KB")
       print(f"  Duration: {duration:.1f}s (with cycling)")

   # Usage
   export_trajectory(
       "md_simulation.xyz",
       "presentation.glb",
       quality='medium'
   )

Static GLB Export
-----------------

For non-animated exports (single frame or current view):

.. code-block:: bash

   # CLI
   chemvista --xyz molecule.xyz --glb output.glb

.. code-block:: python

   # Python
   exporter.export_glb("static.glb")

Static exports also support multiple molecules and transparency.

Optimization Tips
-----------------

For Large Molecules (>100 atoms)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   chemvista --xyz large.xyz --glb-animated output.glb --resolution 5

Lower resolution dramatically reduces file size.

For Many Frames (>50)
~~~~~~~~~~~~~~~~~~~~~

Options:

1. **Higher FPS** - Faster playback, shorter duration
2. **Don't cycle** - Halves the effective frame count
3. **Lower resolution** - Smaller per-frame geometry

.. code-block:: bash

   chemvista --xyz long.xyz --glb-animated output.glb \
             --fps 20 --resolution 5

For PowerPoint
~~~~~~~~~~~~~~

Optimal settings for presentations:

.. code-block:: bash

   chemvista --xyz trajectory.xyz --glb-animated presentation.glb \
             --fps 10 \
             --resolution 8 \
             --cycle \
             --scale auto

Troubleshooting
---------------

Animation Not Playing in PowerPoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Possible causes:**

1. PowerPoint version too old (need 2019 or later)
2. File too large (>100 MB limit)
3. File corruption

**Solutions:**

* Update PowerPoint to latest version
* Use ``--resolution 5`` to reduce file size
* Try opening in another GLB viewer first to verify file

Transparent Objects Not Rendering Correctly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom:** All objects appear transparent or all appear opaque

**Solution:** Ensure you're using the latest version of ChemVista which creates separate meshes for opaque and transparent geometry.

Bonds Don't Move with Atoms
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom:** Bonds stay in place while atoms move

**Solution:** This was fixed in a recent update. Bonds now use two-bone skinning and move correctly with their endpoint atoms.

File Too Large
~~~~~~~~~~~~~~

**Solutions (in order of impact):**

1. Lower resolution: ``--resolution 5`` (biggest impact)
2. Don't cycle: remove ``--cycle``
3. Increase FPS: ``--fps 20`` (shorter duration)
4. Subsample frames before loading

Multiple Trajectories with Different Frame Counts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error:** "All trajectories must have the same number of frames"

**Solution:** Ensure all trajectories have the same number of frames, or export them separately.

Command Line Reference
----------------------

.. code-block:: text

   chemvista --xyz FILE [--glb-animated OUTPUT] [OPTIONS]

   Options:
     --glb-animated FILE   Export animated GLB to FILE
     --glb FILE            Export static GLB to FILE
     --fps N               Frames per second (default: 10)
     --resolution N        Mesh resolution (default: 10)
     --cycle               Add reverse frames for looping
     --scale VALUE         Scale factor: "auto" or number

Next Steps
----------

* Try exporting your own MD trajectories
* Experiment with different quality settings
* Import into PowerPoint and other 3D viewers
* See :doc:`scene_management` for advanced scene manipulation
