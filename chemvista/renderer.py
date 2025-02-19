import numpy as np
import pyvista as pv
import json
import pathlib
from typing import Optional, Dict
from nx_ase.molecule import Molecule


class MoleculeRenderer:
    def __init__(self):
        settings_path = pathlib.Path(
            __file__).parent / 'renderer_settings.json'
        with open(settings_path) as f:
            self.atoms_settings = json.load(f)

    def render_molecule(self,
                        molecule: Molecule,
                        plotter: pv.Plotter,
                        show_hydrogens: bool = True,
                        alpha: float = 1.0,
                        show_numbers: bool = False,
                        resolution: int = 20) -> None:
        """Render a single molecule using a single merged mesh for better performance"""
        # Create atoms and bonds meshes
        atoms_mesh = self._create_atoms_mesh(
            molecule, show_hydrogens, alpha, resolution)
        bonds_mesh = self._create_bonds_mesh(
            molecule, show_hydrogens, alpha, resolution)

        # Merge atoms and bonds into a single mesh
        merged_mesh = None
        if atoms_mesh.n_points > 0:
            merged_mesh = atoms_mesh
        if bonds_mesh.n_points > 0:
            if merged_mesh is None:
                merged_mesh = bonds_mesh
            else:
                merged_mesh = merged_mesh.merge(bonds_mesh)

        # Add the merged mesh to the scene with proper color handling
        if merged_mesh is not None:
            plotter.add_mesh(merged_mesh, scalars='RGBA',
                             rgb=True, smooth_shading=True)

        if show_numbers:
            self._add_atom_numbers(molecule, plotter)

    def _create_atoms_mesh(self, molecule, show_hydrogens, alpha, resolution):
        """Create a single mesh containing all atoms"""
        merged_spheres = None

        for position, symbol in zip(molecule.positions, molecule.get_chemical_symbols()):
            if not show_hydrogens and symbol == 'H':
                continue

            settings = self.atoms_settings.get(
                symbol, self.atoms_settings['Unknown'])

            sphere = pv.Sphere(
                radius=settings['radius'],
                center=position,
                theta_resolution=resolution,
                phi_resolution=resolution
            )

            # Convert color to RGBA values (0-255)
            color = np.array(settings['color'], dtype=np.uint8)
            alpha_value = int(alpha * 255)
            rgba_array = np.zeros((sphere.n_points, 4), dtype=np.uint8)
            rgba_array[:, :3] = color
            rgba_array[:, 3] = alpha_value

            sphere['RGBA'] = rgba_array

            if merged_spheres is None:
                merged_spheres = sphere
            else:
                merged_spheres = merged_spheres.merge(sphere)

        return merged_spheres or pv.PolyData()

    def _create_bonds_mesh(self, molecule, show_hydrogens, alpha, resolution):
        """Create a single mesh containing all bonds"""
        merged_bonds = None

        for bond in molecule.get_all_bonds():
            if not show_hydrogens and 'H' in [molecule.symbols[i] for i in bond]:
                continue

            atom_a = molecule.positions[bond[0]]
            atom_b = molecule.positions[bond[1]]
            bond_type = molecule.G[bond[0]][bond[1]].get('bond_type', 1)

            # Create cylinders based on bond type
            cylinders = self._create_bond_cylinders(
                atom_a, atom_b, bond_type, alpha, resolution
            )

            for cylinder in cylinders:
                if merged_bonds is None:
                    merged_bonds = cylinder
                else:
                    merged_bonds = merged_bonds.merge(cylinder)

        return merged_bonds or pv.PolyData()

    def _create_bond_cylinders(self, start, end, bond_type, alpha, resolution):
        """Create cylinders for a single bond"""
        cylinders = []
        bond_vector = end - start
        unit_vector = bond_vector / np.linalg.norm(bond_vector)
        perp_vector = self._get_perpendicular_vector(unit_vector)

        if bond_type == 1:
            cyl = self._create_single_cylinder(
                start, end, 0.05, alpha, resolution)
            cylinders.append(cyl)
        elif bond_type == 2:
            offset = 0.03
            for i in [-1, 1]:
                offset_vec = i * offset * perp_vector
                cyl = self._create_single_cylinder(
                    start + offset_vec,
                    end + offset_vec,
                    0.025, alpha, resolution
                )
                cylinders.append(cyl)
        elif bond_type == 3:
            offset = 0.05
            for i in [-1, 0, 1]:
                offset_vec = i * offset * perp_vector
                cyl = self._create_single_cylinder(
                    start + offset_vec,
                    end + offset_vec,
                    0.02, alpha, resolution
                )
                cylinders.append(cyl)

        return cylinders

    def _create_single_cylinder(self, start, end, radius, alpha, resolution):
        """Create a single cylinder with color data"""
        cylinder = pv.Cylinder(
            center=0.5*(start + end),
            direction=end - start,
            height=np.linalg.norm(end - start),
            radius=radius,
            resolution=resolution,
            capping=False
        )

        # Set bond color to light gray with alpha
        color = np.array([211, 211, 211], dtype=np.uint8)
        alpha_value = int(alpha * 255)
        rgba_array = np.zeros((cylinder.n_points, 4), dtype=np.uint8)
        rgba_array[:, :3] = color
        rgba_array[:, 3] = alpha_value

        cylinder['RGBA'] = rgba_array
        return cylinder

    def _get_perpendicular_vector(self, vector):
        """Get a vector perpendicular to the input vector"""
        # Find the smallest component to cross with
        basis_vectors = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        smallest = np.argmin(np.abs(vector))
        perp = np.cross(vector, basis_vectors[smallest])
        return perp / np.linalg.norm(perp)

    def _add_atom_numbers(self, molecule, plotter):
        """Add atom numbers to the visualization"""
        poly = pv.PolyData(molecule.positions)
        poly["Labels"] = [str(i) for i in range(len(molecule))]
        plotter.add_point_labels(poly, "Labels", point_size=20, font_size=36)
