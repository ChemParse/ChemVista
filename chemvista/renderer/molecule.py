import numpy as np
import pyvista as pv
import json
import pathlib
from typing import Optional, List, Dict, Any, Union
from nx_ase.molecule import Molecule
from .base import Renderer
from .palettes import load_palette, load_default_settings


class MoleculeRenderer(Renderer):
    # Default bond settings (used if not present in palette)
    DEFAULT_BOND_SETTINGS = {
        "color": [211, 211, 211],  # Light gray
        "single": {"radius": 0.05},
        "double": {"radius": 0.025, "offset": 0.03},
        "triple": {"radius": 0.02, "offset": 0.05}
    }

    def __init__(self):
        settings = load_default_settings()
        self.atoms_settings = {k: v for k, v in settings.items() if k != 'bonds'}
        self.bond_settings = settings.get('bonds', self.DEFAULT_BOND_SETTINGS.copy())

    def set_atom_settings(self, settings: Dict[str, Any]) -> None:
        """
        Set custom atom settings (colors and radii).

        Args:
            settings: Dictionary mapping element symbols to their settings.
                     Each entry should have 'color' (RGB list) and 'radius' (float).
                     Can also include 'bonds' key with bond rendering settings.

        Example:
            >>> renderer.set_atom_settings({
            ...     "C": {"color": [50, 50, 50], "radius": 0.2},
            ...     "H": {"color": [255, 255, 255], "radius": 0.1},
            ...     "bonds": {"color": [200, 200, 200], ...}
            ... })
        """
        # Separate atom settings from bond settings
        self.atoms_settings = {k: v for k, v in settings.items() if k != 'bonds'}
        if 'bonds' in settings:
            self.bond_settings = settings['bonds']

    def set_palette(self, name_or_path: str, radius_scale: float = 1.0) -> None:
        """
        Set atom colors/radii from a named palette or custom file.

        Args:
            name_or_path: Built-in palette name ('chemvista', 'cpk', 'jmol')
                         or path to a custom JSON palette file.
            radius_scale: Scale factor for atom radii (default: 1.0)

        Example:
            >>> renderer.set_palette("cpk")
            >>> renderer.set_palette("jmol", radius_scale=0.8)
            >>> renderer.set_palette("/path/to/custom_palette.json")
        """
        settings = load_palette(name_or_path, radius_scale)
        self.atoms_settings = {k: v for k, v in settings.items() if k != 'bonds'}
        if 'bonds' in settings:
            self.bond_settings = settings['bonds']

    def get_default_settings(self) -> dict:
        return {
            'show_hydrogens': True,
            'show_numbers': False,
            'alpha': 1.0,
            'resolution': 20,
        }

    def validate_settings(self, settings: dict) -> bool:
        required = {'show_hydrogens', 'show_numbers', 'alpha', 'resolution'}
        return all(key in settings for key in required)

    def render(self, molecule: Molecule, plotter: pv.Plotter, settings: dict) -> List:
        """Render molecule to plotter and return list of actors.

        Returns:
            List of VTK actors that were added to the plotter.
        """
        if not self.validate_settings(settings):
            raise ValueError("Invalid settings for molecule rendering")

        actors = []

        atoms_mesh = self._create_atoms_mesh(molecule, settings)
        bonds_mesh = self._create_bonds_mesh(molecule, settings)

        if atoms_mesh is not None:
            actor = plotter.add_mesh(atoms_mesh, scalars='RGBA',
                                     rgb=True, smooth_shading=True)
            actors.append(actor)
        if bonds_mesh is not None:
            actor = plotter.add_mesh(bonds_mesh, scalars='RGBA',
                                     rgb=True, smooth_shading=True)
            actors.append(actor)

        if settings['show_numbers']:
            label_actor = self._add_atom_numbers(molecule, plotter)
            if label_actor is not None:
                actors.append(label_actor)

        return actors

    def _create_atoms_mesh(self, molecule: Molecule, settings: dict) -> Optional[pv.PolyData]:
        """Create a single mesh containing all atoms"""
        merged_spheres = None

        for position, symbol in zip(molecule.positions, molecule.get_chemical_symbols()):
            if not settings['show_hydrogens'] and symbol == 'H':
                continue

            atom_settings = self.atoms_settings.get(
                symbol, self.atoms_settings['Unknown'])

            sphere = pv.Sphere(
                radius=atom_settings['radius'],
                center=position,
                theta_resolution=settings['resolution'],
                phi_resolution=settings['resolution']
            )

            # Add color data
            color = np.array(atom_settings['color'], dtype=np.uint8)
            alpha_value = int(settings['alpha'] * 255)
            rgba_array = np.zeros((sphere.n_points, 4), dtype=np.uint8)
            rgba_array[:, :3] = color
            rgba_array[:, 3] = alpha_value
            sphere['RGBA'] = rgba_array

            if merged_spheres is None:
                merged_spheres = sphere
            else:
                merged_spheres = merged_spheres.merge(sphere)

        return merged_spheres

    def _create_bonds_mesh(self, molecule: Molecule, settings: dict) -> Optional[pv.PolyData]:
        """Create a single mesh containing all bonds"""
        merged_bonds = None

        for bond in molecule.get_all_bonds():
            symbol_a = molecule.symbols[bond[0]]
            symbol_b = molecule.symbols[bond[1]]

            if not settings['show_hydrogens'] and 'H' in [symbol_a, symbol_b]:
                continue

            atom_a = molecule.positions[bond[0]]
            atom_b = molecule.positions[bond[1]]
            bond_type = molecule.G[bond[0]][bond[1]].get('bond_type', 1)

            # Get atom radii to offset bond endpoints to atom surfaces
            radius_a = self.atoms_settings.get(symbol_a, self.atoms_settings['Unknown'])['radius']
            radius_b = self.atoms_settings.get(symbol_b, self.atoms_settings['Unknown'])['radius']

            # Create cylinders for bond
            cylinders = self._create_bond_cylinders(
                atom_a, atom_b, bond_type, settings['alpha'], settings['resolution'],
                radius_a, radius_b
            )

            for cylinder in cylinders:
                if merged_bonds is None:
                    merged_bonds = cylinder
                else:
                    merged_bonds = merged_bonds.merge(cylinder)

        return merged_bonds

    def _create_bond_cylinders(self, start: np.ndarray, end: np.ndarray,
                               bond_type: int, alpha: float, resolution: int,
                               radius_a: float = 0.0, radius_b: float = 0.0) -> List[pv.PolyData]:
        """Create cylinders for a single bond.

        Args:
            start: Position of first atom
            end: Position of second atom
            bond_type: Bond order (1, 2, or 3)
            alpha: Transparency value
            resolution: Cylinder resolution
            radius_a: Radius of first atom (to offset bond start to surface)
            radius_b: Radius of second atom (to offset bond end to surface)
        """
        cylinders = []
        bond_vector = end - start
        bond_length = np.linalg.norm(bond_vector)

        if bond_length < 1e-6:
            return cylinders

        unit_vector = bond_vector / bond_length
        perp_vector = self._get_perpendicular_vector(unit_vector)

        # Offset start and end points to atom surfaces
        surface_start = start + radius_a * unit_vector
        surface_end = end - radius_b * unit_vector

        # Check if bond is too short after offsetting (atoms overlapping)
        if np.linalg.norm(surface_end - surface_start) < 1e-6:
            return cylinders

        # Get bond settings
        single_settings = self.bond_settings.get('single', {'radius': 0.05})
        double_settings = self.bond_settings.get('double', {'radius': 0.025, 'offset': 0.03})
        triple_settings = self.bond_settings.get('triple', {'radius': 0.02, 'offset': 0.05})

        if bond_type == 1:
            cyl = self._create_single_cylinder(
                surface_start, surface_end, single_settings['radius'], alpha, resolution)
            cylinders.append(cyl)
        elif bond_type == 2:
            offset = double_settings.get('offset', 0.03)
            radius = double_settings['radius']
            for i in [-1, 1]:
                offset_vec = i * offset * perp_vector
                cyl = self._create_single_cylinder(
                    surface_start + offset_vec, surface_end + offset_vec, radius, alpha, resolution
                )
                cylinders.append(cyl)
        elif bond_type == 3:
            offset = triple_settings.get('offset', 0.05)
            radius = triple_settings['radius']
            for i in [-1, 0, 1]:
                offset_vec = i * offset * perp_vector
                cyl = self._create_single_cylinder(
                    surface_start + offset_vec, surface_end + offset_vec, radius, alpha, resolution
                )
                cylinders.append(cyl)

        return cylinders

    def _create_single_cylinder(self, start: np.ndarray, end: np.ndarray,
                                radius: float, alpha: float, resolution: int) -> pv.PolyData:
        """Create a single cylinder with color data"""
        cylinder = pv.Cylinder(
            center=0.5*(start + end),
            direction=end - start,
            height=np.linalg.norm(end - start),
            radius=radius,
            resolution=resolution,
            capping=False
        )

        # Get bond color from settings
        bond_color = self.bond_settings.get('color', [211, 211, 211])
        color = np.array(bond_color, dtype=np.uint8)
        alpha_value = int(alpha * 255)
        rgba_array = np.zeros((cylinder.n_points, 4), dtype=np.uint8)
        rgba_array[:, :3] = color
        rgba_array[:, 3] = alpha_value
        cylinder['RGBA'] = rgba_array

        return cylinder

    def _get_perpendicular_vector(self, vector: np.ndarray) -> np.ndarray:
        """Get a vector perpendicular to the input vector"""
        basis_vectors = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        smallest = np.argmin(np.abs(vector))
        perp = np.cross(vector, basis_vectors[smallest])
        return perp / np.linalg.norm(perp)

    def _add_atom_numbers(self, molecule: Molecule, plotter: pv.Plotter):
        """Add atom numbers to the visualization.

        Returns:
            The actor for the labels, or None.
        """
        poly = pv.PolyData(molecule.positions)
        poly["Labels"] = [str(i) for i in range(len(molecule))]
        actor = plotter.add_point_labels(poly, "Labels", point_size=20, font_size=36)
        return actor
