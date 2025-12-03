"""
Animated molecule renderer that supports in-place mesh updates for smooth animation.

This renderer stores mesh references and allows updating atom/bond positions
without clearing and re-rendering the entire scene.
"""

import numpy as np
import pyvista as pv
import json
import pathlib
from typing import Optional, List, Dict, Tuple
from nx_ase.molecule import Molecule
import logging

logger = logging.getLogger("chemvista.renderer.animated_molecule")


class AnimatedMoleculeRenderer:
    """
    Renderer that creates and caches meshes for real-time animation.

    Uses merged meshes for fast initial setup, then updates vertex positions
    in-place for smooth animation without re-adding meshes to the plotter.
    """

    def __init__(self):
        settings_path = pathlib.Path(__file__).parent / 'molecule_renderer_settings.json'
        with open(settings_path) as f:
            self.atoms_settings = json.load(f)

        # Single merged mesh for all atoms
        self._atoms_mesh: Optional[pv.PolyData] = None
        # Single merged mesh for all bonds
        self._bonds_mesh: Optional[pv.PolyData] = None

        # Metadata for updating positions
        self._atom_info: List[Dict] = []  # Per-atom: original_idx, vertex_start, vertex_count, base_points
        self._bond_info: List[Dict] = []  # Per-bond: atom_indices, vertex_start, vertex_count, base_cylinder

        self._base_molecule: Optional[Molecule] = None
        self._plotter: Optional[pv.Plotter] = None
        self._settings: Optional[Dict] = None

    def setup(self, molecule: Molecule, plotter: pv.Plotter, settings: dict) -> None:
        """
        Initial setup - creates merged meshes and adds them to the plotter.

        Args:
            molecule: Base molecule (first frame) defining structure
            plotter: PyVista plotter to render to
            settings: Render settings dict
        """
        import time
        start_time = time.time()

        self._base_molecule = molecule
        self._plotter = plotter
        self._settings = settings

        # Clear any existing cache
        self._atom_info.clear()
        self._bond_info.clear()
        self._atoms_mesh = None
        self._bonds_mesh = None

        resolution = settings.get('resolution', 20)
        alpha = settings.get('alpha', 1.0)
        show_hydrogens = settings.get('show_hydrogens', True)

        # Build atoms mesh
        self._atoms_mesh = self._build_atoms_mesh(molecule, resolution, alpha, show_hydrogens)
        if self._atoms_mesh is not None:
            plotter.add_mesh(self._atoms_mesh, scalars='RGBA', rgb=True, smooth_shading=True)

        # Build bonds mesh
        self._bonds_mesh = self._build_bonds_mesh(molecule, resolution, alpha, show_hydrogens)
        if self._bonds_mesh is not None:
            plotter.add_mesh(self._bonds_mesh, scalars='RGBA', rgb=True, smooth_shading=True)

        elapsed = time.time() - start_time
        logger.debug(f"AnimatedMoleculeRenderer setup completed in {elapsed:.3f}s "
                     f"({len(molecule)} atoms, {len(self._bond_info)} bonds)")

    def _build_atoms_mesh(self, molecule: Molecule, resolution: int, alpha: float,
                          show_hydrogens: bool) -> Optional[pv.PolyData]:
        """Build a single merged mesh for all atoms with tracking info."""
        merged = None
        vertex_offset = 0

        for i, (position, symbol) in enumerate(zip(molecule.positions, molecule.get_chemical_symbols())):
            if not show_hydrogens and symbol == 'H':
                continue

            atom_settings = self.atoms_settings.get(symbol, self.atoms_settings['Unknown'])
            radius = atom_settings['radius']

            # Create sphere at origin
            sphere = pv.Sphere(
                radius=radius,
                center=(0, 0, 0),
                theta_resolution=resolution,
                phi_resolution=resolution
            )

            # Store base points (relative to center) before translation
            base_points = sphere.points.copy()

            # Translate to actual position
            sphere.points = sphere.points + position

            # Add color data
            color = np.array(atom_settings['color'], dtype=np.uint8)
            alpha_value = int(alpha * 255)
            rgba_array = np.zeros((sphere.n_points, 4), dtype=np.uint8)
            rgba_array[:, :3] = color
            rgba_array[:, 3] = alpha_value
            sphere['RGBA'] = rgba_array

            # Store atom info for later updates
            self._atom_info.append({
                'original_idx': i,
                'vertex_start': vertex_offset,
                'vertex_count': sphere.n_points,
                'base_points': base_points,
            })

            vertex_offset += sphere.n_points

            if merged is None:
                merged = sphere
            else:
                merged = merged.merge(sphere)

        return merged

    def _build_bonds_mesh(self, molecule: Molecule, resolution: int, alpha: float,
                          show_hydrogens: bool) -> Optional[pv.PolyData]:
        """Build a single merged mesh for all bonds with tracking info."""
        merged = None
        vertex_offset = 0

        for bond in molecule.get_all_bonds():
            symbols = [molecule.symbols[i] for i in bond]
            if not show_hydrogens and 'H' in symbols:
                continue

            atom_a = molecule.positions[bond[0]]
            atom_b = molecule.positions[bond[1]]
            bond_type = molecule.G[bond[0]][bond[1]].get('bond_type', 1)

            # Get bond parameters (radius and offset) for this bond type
            bond_params = self._get_bond_params(bond_type)

            for params in bond_params:
                radius = params['radius']
                offset_factor = params['offset_factor']

                # Create cylinder and store base points for fast updates
                cyl, base_points = self._create_cylinder_with_base(
                    atom_a, atom_b, radius, offset_factor, alpha, resolution
                )

                # Store bond info with base points for transformation
                self._bond_info.append({
                    'atom_indices': bond,
                    'bond_type': bond_type,
                    'vertex_start': vertex_offset,
                    'vertex_count': cyl.n_points,
                    'resolution': resolution,
                    'radius': radius,
                    'offset_factor': offset_factor,
                    'base_points': base_points,  # Unit cylinder points for fast transform
                })

                vertex_offset += cyl.n_points

                if merged is None:
                    merged = cyl
                else:
                    merged = merged.merge(cyl)

        return merged

    def _get_bond_params(self, bond_type: int) -> List[Dict]:
        """Get cylinder parameters for each bond type."""
        if bond_type == 1:
            return [{'radius': 0.05, 'offset_factor': 0.0}]
        elif bond_type == 2:
            return [
                {'radius': 0.025, 'offset_factor': -0.03},
                {'radius': 0.025, 'offset_factor': 0.03},
            ]
        elif bond_type == 3:
            return [
                {'radius': 0.02, 'offset_factor': -0.05},
                {'radius': 0.02, 'offset_factor': 0.0},
                {'radius': 0.02, 'offset_factor': 0.05},
            ]
        return [{'radius': 0.05, 'offset_factor': 0.0}]

    def _create_cylinder_with_base(self, start: np.ndarray, end: np.ndarray,
                                    radius: float, offset_factor: float,
                                    alpha: float, resolution: int) -> Tuple[pv.PolyData, np.ndarray]:
        """Create a cylinder and return both the mesh and base points for fast updates."""
        bond_vector = end - start
        length = np.linalg.norm(bond_vector)

        if length < 1e-6:
            # Return empty cylinder for zero-length bonds
            cyl = pv.PolyData()
            return cyl, np.array([])

        # Create a unit cylinder along Z axis (height=1, centered at origin)
        unit_cylinder = pv.Cylinder(
            center=(0, 0, 0),
            direction=(0, 0, 1),
            height=1.0,
            radius=radius,
            resolution=resolution,
            capping=False
        )

        # Store base points (unit cylinder)
        base_points = unit_cylinder.points.copy()

        # Transform to actual position
        transformed_points = self._transform_cylinder_points(
            base_points, start, end, offset_factor
        )
        unit_cylinder.points = transformed_points

        # Set bond color to light gray with alpha
        color = np.array([211, 211, 211], dtype=np.uint8)
        alpha_value = int(alpha * 255)
        rgba_array = np.zeros((unit_cylinder.n_points, 4), dtype=np.uint8)
        rgba_array[:, :3] = color
        rgba_array[:, 3] = alpha_value
        unit_cylinder['RGBA'] = rgba_array

        return unit_cylinder, base_points

    def _transform_cylinder_points(self, base_points: np.ndarray,
                                    start: np.ndarray, end: np.ndarray,
                                    offset_factor: float) -> np.ndarray:
        """Transform unit cylinder base points to connect start and end positions."""
        if len(base_points) == 0:
            return base_points

        bond_vector = end - start
        length = np.linalg.norm(bond_vector)

        if length < 1e-6:
            return base_points

        # Unit direction
        direction = bond_vector / length

        # Build rotation matrix from Z axis to bond direction
        z_axis = np.array([0.0, 0.0, 1.0])
        rotation = self._rotation_matrix_from_vectors(z_axis, direction)

        # Scale z component by length, keep x,y as is (radius already correct)
        scaled_points = base_points.copy()
        scaled_points[:, 2] *= length

        # Rotate
        rotated_points = scaled_points @ rotation.T

        # Calculate perpendicular offset if needed
        if abs(offset_factor) > 1e-6:
            perp = self._get_perpendicular_vector(direction)
            offset_vec = offset_factor * perp
            rotated_points = rotated_points + offset_vec

        # Translate to center of bond
        center = 0.5 * (start + end)
        return rotated_points + center

    def _rotation_matrix_from_vectors(self, vec1: np.ndarray, vec2: np.ndarray) -> np.ndarray:
        """Compute rotation matrix that rotates vec1 to vec2."""
        # Normalize inputs
        a = vec1 / np.linalg.norm(vec1)
        b = vec2 / np.linalg.norm(vec2)

        # Check if vectors are parallel or anti-parallel
        dot = np.dot(a, b)
        if dot > 0.9999:
            return np.eye(3)
        if dot < -0.9999:
            # Find a perpendicular vector for 180-degree rotation
            perp = np.array([1, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1, 0])
            perp = perp - np.dot(perp, a) * a
            perp = perp / np.linalg.norm(perp)
            # 180-degree rotation around perp
            return 2 * np.outer(perp, perp) - np.eye(3)

        # Rodrigues' rotation formula
        v = np.cross(a, b)
        s = np.linalg.norm(v)
        c = dot

        vx = np.array([
            [0, -v[2], v[1]],
            [v[2], 0, -v[0]],
            [-v[1], v[0], 0]
        ])

        return np.eye(3) + vx + vx @ vx * ((1 - c) / (s * s))

    def update_positions(self, new_positions: np.ndarray) -> None:
        """
        Update atom and bond positions in-place for smooth animation.

        Args:
            new_positions: New atom positions array of shape (num_atoms, 3)
        """
        if self._atoms_mesh is None:
            return

        # Update atom positions in-place
        for atom_info in self._atom_info:
            original_idx = atom_info['original_idx']
            if original_idx < len(new_positions):
                start = atom_info['vertex_start']
                count = atom_info['vertex_count']
                new_pos = new_positions[original_idx]
                # Update vertices: base_points + new position
                self._atoms_mesh.points[start:start + count] = atom_info['base_points'] + new_pos

        # Update bond positions in-place using fast transformation
        if self._bonds_mesh is not None:
            for bond_info in self._bond_info:
                atom_indices = bond_info['atom_indices']
                pos_a = new_positions[atom_indices[0]]
                pos_b = new_positions[atom_indices[1]]

                start = bond_info['vertex_start']
                count = bond_info['vertex_count']
                base_points = bond_info.get('base_points')
                offset_factor = bond_info.get('offset_factor', 0.0)

                if base_points is not None and len(base_points) == count:
                    # Fast transformation using stored base points
                    new_cyl_points = self._transform_cylinder_points(
                        base_points, pos_a, pos_b, offset_factor
                    )
                    self._bonds_mesh.points[start:start + count] = new_cyl_points

        # Trigger render update
        if self._plotter:
            self._plotter.render()

    def _get_perpendicular_vector(self, vector: np.ndarray) -> np.ndarray:
        """Get a vector perpendicular to the input vector."""
        basis_vectors = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        smallest = np.argmin(np.abs(vector))
        perp = np.cross(vector, basis_vectors[smallest])
        norm = np.linalg.norm(perp)
        if norm < 1e-6:
            return basis_vectors[(smallest + 1) % 3]
        return perp / norm

    def clear(self) -> None:
        """Clear cached meshes."""
        self._atoms_mesh = None
        self._bonds_mesh = None
        self._atom_info.clear()
        self._bond_info.clear()
        self._base_molecule = None
        self._plotter = None
        self._settings = None

    @property
    def is_setup(self) -> bool:
        """Check if renderer has been set up with meshes."""
        return self._atoms_mesh is not None
