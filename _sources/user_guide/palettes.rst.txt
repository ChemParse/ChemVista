Color Palettes
==============

ChemVista supports multiple color palettes for atom coloring, allowing you to customize
the appearance of your molecular visualizations for different purposes.

Available Palettes
------------------

chemvista (Default)
~~~~~~~~~~~~~~~~~~~

The default ChemVista palette provides vibrant, distinguishable colors suitable for
general-purpose visualization.

.. code-block:: python

   scene.set_palette("chemvista")

cpk
~~~

The classic CPK (Corey-Pauling-Koltun) coloring scheme, widely used in molecular
visualization. Based on physical models where:

* Hydrogen: White
* Carbon: Black/Dark gray
* Nitrogen: Blue
* Oxygen: Red
* Sulfur: Yellow

.. code-block:: python

   scene.set_palette("cpk")

jmol
~~~~

The Jmol color scheme, commonly used in web-based molecular viewers.

.. code-block:: python

   scene.set_palette("jmol")

powerpoint
~~~~~~~~~~

A specialized palette with darker colors optimized for PowerPoint 3D presentations.

**Why darker colors?**

PowerPoint's 3D model viewer does not support real-time shadows. Without shadows,
standard bright colors appear flat and washed out. The PowerPoint palette uses
darker, more saturated colors that maintain visual depth even without shadow effects.

.. code-block:: python

   scene.set_palette("powerpoint")

**Recommended for:**

* GLB exports intended for PowerPoint presentations
* Presentations on projectors with limited dynamic range
* Any 3D viewer without shadow support

Using Palettes
--------------

Command Line
~~~~~~~~~~~~

Use the ``--palette`` option:

.. code-block:: bash

   # Use PowerPoint palette for GLB export
   chemvista --xyz molecule.xyz --palette powerpoint --glb molecule.glb

   # Use CPK palette for interactive viewing
   chemvista --xyz molecule.xyz --palette cpk --interactive

   # Use default palette (chemvista)
   chemvista --xyz molecule.xyz --glb molecule.glb

Python API
~~~~~~~~~~

**Global palette (affects all objects):**

.. code-block:: python

   from chemvista import SceneManager

   scene = SceneManager()
   scene.load_xyz("molecule.xyz")

   # Set palette for entire scene
   scene.set_palette("powerpoint")

   scene.export_to_glb("molecule.glb")

**Per-object palette:**

.. code-block:: python

   from chemvista import SceneManager

   scene = SceneManager()
   mol1 = scene.load_xyz("mol1.xyz")
   mol2 = scene.load_xyz("mol2.xyz")

   # Different palettes for different molecules
   mol1.render_settings.palette = "cpk"
   mol2.render_settings.palette = "jmol"

   scene.export_to_glb("scene.glb")

GUI
~~~

In the interactive GUI:

1. Select an object in the scene tree
2. Open the settings dialog (gear icon)
3. Choose a palette from the dropdown menu
4. Click Apply

Adding Custom Palettes
----------------------

You can define custom color palettes by creating a new palette in the palettes module:

.. code-block:: python

   from chemvista.renderer.palettes import register_palette

   my_palette = {
       'H': (255, 255, 255),   # White
       'C': (100, 100, 100),   # Dark gray
       'N': (0, 0, 255),       # Blue
       'O': (255, 0, 0),       # Red
       # ... other elements
       'default': (200, 200, 200),  # Fallback color
   }

   register_palette("my_custom_palette", my_palette)

   # Now use it
   scene.set_palette("my_custom_palette")

Palette Comparison
------------------

Here's a quick comparison of how common elements appear in each palette:

.. list-table::
   :header-rows: 1

   * - Element
     - ChemVista
     - CPK
     - Jmol
     - PowerPoint
   * - Carbon (C)
     - Gray
     - Dark Gray
     - Dark Gray
     - Dark Gray (darker)
   * - Hydrogen (H)
     - White
     - White
     - White
     - Light Gray
   * - Oxygen (O)
     - Red
     - Red
     - Red
     - Dark Red
   * - Nitrogen (N)
     - Blue
     - Blue
     - Blue
     - Dark Blue
   * - Sulfur (S)
     - Yellow
     - Yellow
     - Yellow
     - Dark Yellow

See Also
--------

* :doc:`cli` - Command line options including ``--palette``
* :doc:`../api/renderer` - Renderer API for programmatic color control
