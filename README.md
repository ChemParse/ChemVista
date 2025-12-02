# ChemVista

ChemVista is a chemical visualization tool built with Python, PyQt5, and PyVista for 3D molecular rendering. It provides both a CLI and GUI for visualizing molecules, trajectories, and scalar fields from computational chemistry files (XYZ and CUBE formats).

## Features

- **3D Molecular Visualization**: Render molecules with atoms, bonds, and multiple bond types
- **Scalar Field Visualization**: Display electron density and other scalar fields as isosurfaces
- **Trajectory Animation**: Load and visualize molecular dynamics trajectories
- **Interactive GUI**: PyQt5-based interface with scene tree and property editors
- **Export to GLB**: Export molecules and scalar fields to GLB format for PowerPoint 3D and other 3D viewers
- **Animated Trajectory Export**: Export molecular trajectories as animated GLB files with skeletal animation for PowerPoint
- **CLI Support**: Command-line interface for batch processing and scripting
- **Screenshot Generation**: Save high-quality renders as images

## Installation

```bash
# Clone the repository
git clone https://github.com/imtambovtcev/ChemVista.git
cd ChemVista

# Install with Poetry
poetry install

# Or install with pip (after poetry build)
pip install .
```

## Quick Start

### Command Line Usage

```bash
# Render a molecule
chemvista --xyz molecule.xyz

# Launch interactive GUI
chemvista --xyz molecule.xyz --interactive

# Save a screenshot
chemvista --xyz molecule.xyz --screenshot output.png

# Export to GLB for PowerPoint 3D
chemvista --xyz molecule.xyz --glb molecule.glb

# Export trajectory as animated GLB for PowerPoint (skeletal animation)
chemvista --xyz trajectory.xyz --glb-animated trajectory_anim.glb --fps 15

# Load molecule with electron density from CUBE file
chemvista --cube-mol density.cube --interactive

# Load multiple files
chemvista --xyz mol1.xyz --xyz mol2.xyz --cube-field field.cube
```

### Python API Usage

```python
from chemvista import SceneManager, Exporter

# Create scene manager
scene = SceneManager()

# Load a molecule
mol_obj = scene.load_xyz("molecule.xyz")

# Adjust rendering settings
mol_obj.render_settings.alpha = 0.8
mol_obj.render_settings.resolution = 30

# Render
plotter = scene.render()
plotter.show()

# Export to GLB for PowerPoint
scene.export_to_glb("molecule.glb")
```

### Export to PowerPoint 3D

ChemVista can export molecules and scalar fields to GLB format, which can be imported into PowerPoint as interactive 3D objects:

```bash
# Export a molecule with electron density
chemvista --cube-mol molecule.cube --glb output.glb

# Export with transparency support
chemvista --xyz molecule.xyz --glb molecule.glb
```

#### Animated Trajectories for PowerPoint

Export molecular dynamics trajectories as animated GLB files that play in PowerPoint using skeletal animation (the only animation type PowerPoint supports):

```bash
# Export trajectory with default settings (10 fps, resolution=10)
chemvista --xyz trajectory.xyz --glb-animated output.glb

# Export with custom frame rate (15 fps)
chemvista --xyz trajectory.xyz --glb-animated output.glb --fps 15

# Export with lower resolution for smaller file size
chemvista --xyz trajectory.xyz --glb-animated output.glb --resolution 5

# Export with seamless loop (adds reverse frames)
chemvista --xyz trajectory.xyz --glb-animated output.glb --cycle
```

**Using Python API:**

```python
from chemvista import SceneManager

# Load trajectory
scene = SceneManager()
traj_obj = scene.load_xyz("trajectory.xyz")

# Export as animated GLB for PowerPoint
scene.export_trajectory_animated_glb(
    trajectory_object=traj_obj,
    output_path="animated_trajectory.glb",
    fps=15,
    resolution=10,      # Lower = smaller file (default: 10)
    cycle_animation=True  # Add reverse frames for seamless loop
)
```

**In PowerPoint:**
1. Insert > 3D Models > From a File...
2. Select the .glb file
3. The animation will play automatically when presenting!

**Note:** PowerPoint only supports skeletal animations. Each atom becomes a bone in the skeleton, allowing smooth animation playback.

See [examples/export_to_glb.py](examples/export_to_glb.py) for more examples.

## File Formats

- **XYZ**: Single molecules or trajectories (multi-frame)
- **CUBE**: Gaussian CUBE files containing molecules and/or scalar fields

## Architecture

ChemVista uses a hierarchical scene graph to organize chemical objects:

- **SceneManager**: Manages the scene and provides high-level operations
- **SceneObject**: Base class for renderable objects (molecules, scalar fields, trajectories)
- **Renderer**: Stateless renderers convert objects to PyVista meshes
- **Exporter**: Converts rendered scenes to GLB format for 3D model export

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

## Development

```bash
# Install development dependencies
poetry install

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=chemvista

# Run specific test file
poetry run pytest tests/test_exporter.py -v
```

## Dependencies

- Python >=3.10
- PyVista: 3D visualization
- PyQt5: GUI framework
- nx_ase: Molecular data structures
- trimesh: 3D model export
- ASE, NetworkX, NumPy, and more (see pyproject.toml)

## Third-Party Assets

Icons from Material Design Icons by Pictogrammers (https://pictogrammers.com/library/mdi/)
are licensed under the Apache License 2.0 (https://www.apache.org/licenses/LICENSE-2.0).

Contributors of the icons used in this project:
- Austin Andrews (Templarian) - https://pictogrammers.com/contributor/Templarian/
- Nick (Croutonix) https://pictogrammers.com/contributor/Croutonix/
- Google - https://pictogrammers.com/contributor/google/
