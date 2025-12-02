ChemVista Documentation
=======================

ChemVista is a powerful chemical visualization tool built with Python, PyQt5, and PyVista for 3D molecular rendering.
It provides both a CLI and GUI for visualizing molecules, trajectories, and scalar fields from computational chemistry files.

.. image:: https://img.shields.io/badge/python-3.10+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python Version

.. image:: https://img.shields.io/badge/license-MIT-green.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License

Features
--------

* **3D Molecular Visualization**: Interactive visualization of molecular structures using PyVista
* **Trajectory Animation**: View and export molecular dynamics trajectories with skeletal animation
* **Scalar Field Rendering**: Display electron density and other scalar fields with isosurfaces
* **Multiple Export Formats**: Export to GLB format for PowerPoint and other 3D viewers
* **Hierarchical Scene Management**: Tree-based scene graph for organizing molecular objects
* **GUI and CLI**: Both graphical interface and command-line tools available

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/yourusername/ChemVista.git
   cd ChemVista

   # Install with Poetry
   poetry install

   # Or install with pip
   pip install -e .

Basic Usage
~~~~~~~~~~~

**Command Line Interface:**

.. code-block:: bash

   # Load and render XYZ file
   chemvista --xyz molecule.xyz

   # Load molecule with scalar field
   chemvista --cube-mol density.cube

   # Launch interactive GUI
   chemvista --xyz molecule.xyz --interactive

   # Export to GLB format
   chemvista --xyz trajectory.xyz --export output.glb

**Python API:**

.. code-block:: python

   from chemvista.scene_manager import SceneManager
   from chemvista.exporter import Exporter

   # Load trajectory
   scene_manager = SceneManager()
   trajectory = scene_manager.load_xyz("trajectory.xyz")

   # Export animated GLB
   exporter = Exporter(scene_manager)
   exporter.export_trajectory_animated_glb(
       trajectory_object=trajectory,
       output_path="output.glb",
       fps=10,
       resolution=5,  # Lower resolution for smaller files
       cycle_animation=True  # Loop animation
   )

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/installation
   user_guide/cli
   user_guide/gui
   user_guide/file_formats

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials/basic_visualization
   tutorials/trajectory_export
   tutorials/scalar_fields
   tutorials/scene_management

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/scene_manager
   api/exporter
   api/renderer
   api/scene_objects

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   developer/architecture
   developer/testing
   developer/contributing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
