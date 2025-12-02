Exporting Animated Trajectories
================================

This tutorial covers exporting molecular dynamics trajectories as animated GLB files for PowerPoint and other 3D viewers.

Overview
--------

ChemVista uses **skeletal animation** to create PowerPoint-compatible animated 3D models. Each atom becomes a "bone" in a skeleton, and the bone positions are animated through the trajectory frames. Bonds automatically stretch and compress as atoms move.

Basic Export
------------

Step 1: Load Trajectory
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from chemvista.scene_manager import SceneManager
   from chemvista.exporter import Exporter
   from pathlib import Path

   # Create scene manager and load trajectory
   scene_manager = SceneManager()
   trajectory = scene_manager.load_xyz("md_trajectory.xyz")

   print(f"Loaded {len(trajectory.children)} frames")
   print(f"Each frame has {len(trajectory.children[0].molecule)} atoms")

Step 2: Create Exporter
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Create exporter instance
   exporter = Exporter(scene_manager)

Step 3: Export with Default Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Export with defaults (resolution=10, fps=10)
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="animation.glb"
   )

Step 4: Use in PowerPoint
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open PowerPoint
2. Insert → 3D Models → From a File
3. Select ``animation.glb``
4. Animation plays automatically!

Advanced Options
----------------

Quality Control
~~~~~~~~~~~~~~~

Adjust mesh resolution to balance quality vs. file size:

.. code-block:: python

   # High quality (smooth spheres, larger file)
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="high_quality.glb",
       resolution=20  # More triangles
   )

   # Low quality (smaller file, visible facets)
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="low_quality.glb",
       resolution=5  # Fewer triangles
   )

**File Size Comparison:**

* resolution=20: ~2000 KB (baseline)
* resolution=10: ~600 KB (70% smaller)
* resolution=5: ~200 KB (90% smaller)

Animation Speed
~~~~~~~~~~~~~~~

Control playback speed with FPS parameter:

.. code-block:: python

   # Slow motion (5 fps)
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="slow.glb",
       fps=5
   )

   # Normal speed (10 fps, default)
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="normal.glb",
       fps=10
   )

   # Fast motion (30 fps)
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="fast.glb",
       fps=30
   )

**Duration Calculation:**

Duration = (Number of frames - 1) / FPS

* 10 frames at 10 fps = 0.9 seconds
* 50 frames at 10 fps = 4.9 seconds

Looping Animations
~~~~~~~~~~~~~~~~~~

Create seamless loops by adding reverse frames:

.. code-block:: python

   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="looped.glb",
       cycle_animation=True  # Adds reverse frames
   )

**How it works:**

* Original: frames 1, 2, 3, 4, 5
* Cycled: frames 1, 2, 3, 4, 5, 4, 3, 2
* Avoids duplicates at loop point
* Creates smooth back-and-forth motion

Complete Example
----------------

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
       if not hasattr(trajectory, 'children'):
           raise ValueError("File does not contain a trajectory")

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
       exporter.export_trajectory_animated_glb(
           trajectory_object=trajectory,
           output_path=output_file,
           fps=10,
           resolution=resolution,
           cycle_animation=True  # Enable looping
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

Optimization Tips
-----------------

For Large Molecules
~~~~~~~~~~~~~~~~~~~

When exporting large molecules (>100 atoms):

.. code-block:: python

   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="large_molecule.glb",
       resolution=5,  # Lower resolution
       fps=10
   )

**Why:** Fewer triangles = smaller file, faster loading

For Many Frames
~~~~~~~~~~~~~~~

When exporting long trajectories (>50 frames):

.. code-block:: python

   # Option 1: Subsample frames
   trajectory_subset = trajectory.children[::2]  # Every 2nd frame

   # Option 2: Lower FPS
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="long_trajectory.glb",
       fps=20,  # Higher FPS = shorter duration
       resolution=5
   )

For PowerPoint
~~~~~~~~~~~~~~

Optimize for PowerPoint presentations:

.. code-block:: python

   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="powerpoint.glb",
       fps=10,  # Smooth but not too fast
       resolution=8,  # Good balance
       cycle_animation=True  # Loop seamlessly
   )

Troubleshooting
---------------

Animation Not Playing in PowerPoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Possible causes:**

1. PowerPoint version too old (need 2019 or later)
2. File corruption
3. GLB file > 100 MB (PowerPoint limit)

**Solutions:**

* Use ``resolution=5`` to reduce file size
* Subsample frames
* Update PowerPoint

Bonds Look Wrong
~~~~~~~~~~~~~~~~

**Symptom:** Bonds don't stretch correctly, or appear disconnected

**Solution:** This should not happen with the current implementation, but if it does:

.. code-block:: python

   # Check trajectory frame consistency
   for i, frame in enumerate(trajectory.children):
       print(f"Frame {i}: {len(frame.molecule)} atoms")

Atoms are the wrong positions in frames are too slow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solution:** Adjust frame rate:

.. code-block:: python

   # Increase FPS for faster motion
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="output.glb",
       fps=20  # Faster
   )

File Too Large
~~~~~~~~~~~~~~

**Solutions (in order of impact):**

1. Lower resolution: ``resolution=5`` (biggest impact)
2. Subsample frames: ``trajectory.children[::2]``
3. Increase FPS: ``fps=20`` (shorter duration)
4. Don't cycle: ``cycle_animation=False``

Command Line Usage
------------------

Export from command line:

.. code-block:: bash

   # Basic export
   chemvista --xyz trajectory.xyz --export output.glb

   # With options
   chemvista --xyz trajectory.xyz \\
             --export output.glb \\
             --fps 15 \\
             --resolution 8 \\
             --cycle

Next Steps
----------

* Try exporting your own MD trajectories
* Experiment with different quality settings
* Import into PowerPoint and other 3D viewers
* See :doc:`scene_management` for advanced scene manipulation
