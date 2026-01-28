Installation
============

Requirements
------------

ChemVista requires Python 3.10 or later and supports Linux, macOS, and Windows.

**System Requirements:**

* Python >= 3.10
* OpenGL support for 3D rendering
* Qt5 for GUI (PyQt5)

Python Version Compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Note the VTK version constraints:

* **Python 3.10-3.11**: VTK < 9.4.0
* **Python >= 3.12**: VTK >= 9.5.0

This is important for CI/CD testing and compatibility.

Installation Methods
--------------------

Using Poetry (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Poetry is the recommended package manager for ChemVista development:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/yourusername/ChemVista.git
   cd ChemVista

   # Install dependencies
   poetry install

   # Run ChemVista
   poetry run chemvista --help

Using pip
~~~~~~~~~

For regular users, pip installation is simpler:

.. code-block:: bash

   # Install from local directory
   pip install -e .

   # Or install from git
   pip install git+https://github.com/yourusername/ChemVista.git

Development Installation
~~~~~~~~~~~~~~~~~~~~~~~~

For development with all optional dependencies:

.. code-block:: bash

   # Install with development dependencies
   poetry install --with dev

   # Or with pip
   pip install -e ".[dev]"

Verifying Installation
----------------------

Check that ChemVista is installed correctly:

.. code-block:: bash

   # Check CLI is available
   chemvista --version

   # Run tests
   poetry run pytest

   # Or with pip installation
   pytest

Common Issues
-------------

Qt Platform Plugin Not Found
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see errors about Qt platform plugins:

.. code-block:: bash

   # Set Qt platform to offscreen for headless systems
   export QT_QPA_PLATFORM=offscreen

   # Or install additional Qt dependencies
   sudo apt-get install libqt5gui5  # Ubuntu/Debian

VTK Version Conflicts
~~~~~~~~~~~~~~~~~~~~~

If you encounter VTK version conflicts:

.. code-block:: bash

   # For Python 3.10-3.11
   pip install "vtk<9.4.0"

   # For Python 3.12+
   pip install "vtk>=9.5.0"

Missing OpenGL
~~~~~~~~~~~~~~

On headless servers, you may need to set up virtual framebuffer:

.. code-block:: bash

   # Install xvfb
   sudo apt-get install xvfb

   # Run with xvfb
   xvfb-run -a chemvista --xyz molecule.xyz

Uninstallation
--------------

To remove ChemVista:

.. code-block:: bash

   # If installed with poetry
   poetry env remove python

   # If installed with pip
   pip uninstall chemvista
