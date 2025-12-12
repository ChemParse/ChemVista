"""
3D Export functionality for ChemVista

This module provides functionality to export rendered molecules and scalar fields
to 3D file formats (GLB) suitable for PowerPoint and other 3D viewers.
"""

import logging
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import pyvista as pv
import trimesh
from trimesh.visual import ColorVisuals
from trimesh.visual.material import PBRMaterial

from .scene_manager import SceneManager
from .scene_objects import MoleculeObject, ScalarFieldObject

logger = logging.getLogger("chemvista.exporter")


class Exporter:
    """Handles export of ChemVista scenes to 3D file formats"""

    def __init__(self, scene_manager: SceneManager):
        """
        Initialize the exporter with a scene manager.

        Args:
            scene_manager: The SceneManager instance containing the scene to export
        """
        self.scene_manager = scene_manager

    @staticmethod
    def _pv_to_trimesh(mesh: pv.PolyData) -> trimesh.Trimesh:
        """
        Convert a PyVista mesh to a trimesh.Trimesh object.

        Args:
            mesh: PyVista PolyData mesh to convert

        Returns:
            Converted trimesh.Trimesh object
        """
        # Triangulate the mesh to ensure all faces are triangles
        mesh = mesh.triangulate()

        # PyVista faces format: [n_points, p1, p2, ..., pn, n_points, ...]
        # Extract just the point indices (skip the count)
        faces = mesh.faces.reshape(-1, 4)[:, 1:]

        return trimesh.Trimesh(
            vertices=mesh.points,
            faces=faces,
            process=False  # Don't process to preserve vertex colors
        )

    def _collect_meshes_with_colors(self) -> List[tuple[trimesh.Trimesh, np.ndarray]]:
        """
        Collect all visible meshes from the scene with their vertex colors.

        This method directly generates PyVista meshes from renderers with proper
        RGBA data, then converts them to trimesh format.

        Returns:
            List of tuples (trimesh, rgba_colors) for each mesh in the scene
        """
        meshes_with_colors = []

        # Iterate through all visible objects
        for obj in self.scene_manager.root.iter_visible():
            # Skip root node
            if obj == self.scene_manager.root:
                continue

            # Collect PyVista meshes based on object type
            pv_meshes = []

            if isinstance(obj, MoleculeObject):
                # Get meshes directly from renderer
                renderer = self.scene_manager.molecule_renderer
                settings = vars(obj.render_settings)

                # Create atoms mesh
                atoms_mesh = renderer._create_atoms_mesh(obj.molecule, settings)
                if atoms_mesh is not None:
                    pv_meshes.append(atoms_mesh)

                # Create bonds mesh
                bonds_mesh = renderer._create_bonds_mesh(obj.molecule, settings)
                if bonds_mesh is not None:
                    pv_meshes.append(bonds_mesh)

            elif isinstance(obj, ScalarFieldObject):
                # For scalar fields, we need to render to a temporary plotter
                # because the scalar field renderer uses plotter.add_mesh directly
                temp_plotter = pv.Plotter(off_screen=True)
                self.scene_manager.scalar_field_renderer.render(
                    field=obj.scalar_field,
                    plotter=temp_plotter,
                    settings=vars(obj.render_settings)
                )

                # Extract meshes from the plotter
                for actor in temp_plotter.renderer.actors.values():
                    if hasattr(actor, 'GetMapper'):
                        mapper = actor.GetMapper()
                        if mapper and hasattr(mapper, 'GetInput'):
                            mesh = pv.wrap(mapper.GetInput())

                            # Get color from actor if no RGBA data
                            if 'RGBA' not in mesh.array_names:
                                color_prop = actor.GetProperty()
                                color = color_prop.GetColor()
                                opacity = color_prop.GetOpacity()

                                # Create RGBA array from actor color
                                rgba = np.zeros((mesh.n_points, 4), dtype=np.uint8)
                                rgba[:, 0] = int(color[0] * 255)
                                rgba[:, 1] = int(color[1] * 255)
                                rgba[:, 2] = int(color[2] * 255)
                                rgba[:, 3] = int(opacity * 255)
                                mesh['RGBA'] = rgba

                            pv_meshes.append(mesh)

                temp_plotter.close()
            else:
                # Skip trajectory objects (they should be rendered as their children)
                continue

            # Process all collected PyVista meshes
            for pv_mesh in pv_meshes:
                if 'RGBA' in pv_mesh.array_names:
                    rgba = pv_mesh['RGBA']

                    # Convert to uint8 if needed
                    if rgba.dtype != np.uint8:
                        rgba = (rgba * 255).astype(np.uint8)

                    # Ensure RGBA has 4 channels
                    if len(rgba.shape) == 1 or rgba.shape[1] == 3:
                        if len(rgba.shape) == 1:
                            # Single value per vertex, create grayscale
                            rgba_full = np.zeros((len(rgba), 4), dtype=np.uint8)
                            rgba_full[:, :3] = rgba[:, np.newaxis]
                            rgba_full[:, 3] = 255
                            rgba = rgba_full
                        else:
                            # Add alpha channel
                            alpha = np.full((rgba.shape[0], 1), 255, dtype=np.uint8)
                            rgba = np.hstack([rgba, alpha])

                    # Convert to trimesh
                    tm = self._pv_to_trimesh(pv_mesh)
                    meshes_with_colors.append((tm, rgba))

        return meshes_with_colors

    def export_glb(
        self,
        output_path: Union[str, Path],
        **kwargs
    ) -> None:
        """
        Export the current scene to a GLB file.

        This method renders all visible objects and combines them into a single
        GLB file with proper vertex colors and transparency support.

        The exported GLB file will preserve:
        - Atom colors from the molecule renderer settings
        - Bond colors (light gray by default)
        - Scalar field isosurface colors
        - Transparency values from the alpha settings

        Args:
            output_path: Path where the GLB file will be saved
            **kwargs: Reserved for future options (currently unused)

        Raises:
            ValueError: If no visible objects are found in the scene or invalid file extension
            RuntimeError: If export fails

        Note:
            Transparency is controlled by the alpha channel in vertex colors,
            which comes from the render settings of each object.
        """
        output_path = Path(output_path)

        # Validate file extension
        if output_path.suffix.lower() not in ['.glb', '.gltf']:
            raise ValueError(
                f"Invalid file extension '{output_path.suffix}'. "
                f"Must be '.glb' or '.gltf'. Did you mean '{output_path.stem}.glb'?"
            )

        logger.info(f"Exporting scene to GLB: {output_path}")

        # Collect all meshes with their colors
        meshes_with_colors = self._collect_meshes_with_colors()

        if not meshes_with_colors:
            raise ValueError("No visible objects found in scene to export")

        # Separate meshes by transparency level to assign different materials
        # Group meshes into opaque (alpha=255) and transparent (alpha<255)
        opaque_meshes = []
        opaque_colors = []
        transparent_meshes = []
        transparent_colors = []

        for tm, rgba in meshes_with_colors:
            # Check if this mesh has any transparency
            if np.all(rgba[:, 3] == 255):
                # Fully opaque
                opaque_meshes.append(tm)
                opaque_colors.append(rgba)
            else:
                # Has some transparency
                transparent_meshes.append(tm)
                transparent_colors.append(rgba)

        # Create scene with separate meshes for different transparency levels
        scene_geometries = {}

        # Combine opaque meshes
        if opaque_meshes:
            if len(opaque_meshes) == 1:
                combined_opaque = opaque_meshes[0]
                combined_opaque_rgba = opaque_colors[0]
            else:
                combined_opaque = trimesh.util.concatenate(opaque_meshes)
                combined_opaque_rgba = np.vstack(opaque_colors).astype(np.uint8)

            combined_opaque.visual = ColorVisuals(combined_opaque, vertex_colors=combined_opaque_rgba)
            combined_opaque.visual.material = PBRMaterial(
                name="OpaqueMaterial",
                baseColorFactor=[1.0, 1.0, 1.0, 1.0],
                alphaMode="OPAQUE",
                doubleSided=True,
            )
            scene_geometries['opaque'] = combined_opaque

        # Combine transparent meshes
        if transparent_meshes:
            if len(transparent_meshes) == 1:
                combined_transparent = transparent_meshes[0]
                combined_transparent_rgba = transparent_colors[0]
            else:
                combined_transparent = trimesh.util.concatenate(transparent_meshes)
                combined_transparent_rgba = np.vstack(transparent_colors).astype(np.uint8)

            combined_transparent.visual = ColorVisuals(combined_transparent, vertex_colors=combined_transparent_rgba)

            # Calculate average alpha for material baseColorFactor
            avg_alpha = np.mean(combined_transparent_rgba[:, 3]) / 255.0

            combined_transparent.visual.material = PBRMaterial(
                name="TransparentMaterial",
                baseColorFactor=[1.0, 1.0, 1.0, avg_alpha],
                alphaMode="BLEND",
                doubleSided=True,
            )
            scene_geometries['transparent'] = combined_transparent

        # Create a scene with both geometries
        if len(scene_geometries) == 0:
            raise ValueError("No meshes to export")
        elif len(scene_geometries) == 1:
            # Single mesh - export directly
            combined = list(scene_geometries.values())[0]
        else:
            # Multiple meshes - create scene
            combined = trimesh.Scene(geometry=scene_geometries)

        # Export to GLB
        try:
            combined.export(str(output_path))

            total_vertices = sum(m.vertices.shape[0] for m in scene_geometries.values())
            total_faces = sum(m.faces.shape[0] for m in scene_geometries.values())

            logger.info(f"✅ Successfully exported to {output_path}")
            logger.info(f"   Total vertices: {total_vertices}")
            logger.info(f"   Total faces: {total_faces}")
            logger.info(f"   Meshes: {len(scene_geometries)} ({', '.join(scene_geometries.keys())})")
        except Exception as e:
            logger.error(f"Failed to export GLB: {e}")
            raise RuntimeError(f"Failed to export GLB: {e}")

    def export_trajectory_animated_glb(
        self,
        trajectory_object,
        output_path: Union[str, Path],
        fps: int = 10,
        resolution: int = 10,
        cycle_animation: bool = False,
        scale: Optional[float] = None,
        **kwargs
    ) -> None:
        """
        Export a trajectory as an animated GLB file using skeletal animation.

        This creates a PowerPoint-compatible animated 3D model where each atom
        is a bone in a skeleton, and the bone positions are animated through
        the trajectory frames.

        Args:
            trajectory_object: TrajectoryObject to export
            output_path: Path where the GLB file will be saved
            fps: Frames per second for animation (default: 10)
            resolution: Mesh resolution for spheres/cylinders (default: 10, lower = fewer triangles)
            cycle_animation: If True, adds reverse frames to create a loop (default: False)
            scale: Scale factor for the model. If None (default), coordinates are in Angstroms.
                   Use scale=0.1 to convert to nanometers, or scale="auto" to fit in a 2-unit box.
            **kwargs: Additional options (reserved for future use)

        Raises:
            ValueError: If trajectory has no frames or inconsistent atom counts
            RuntimeError: If export fails

        Note:
            All trajectory frames must have the same number of atoms in the same order.
            PowerPoint only plays the first animation in the GLB file.
            Lower resolution values create smaller files with fewer triangles.
        """
        import json
        import struct

        output_path = Path(output_path)

        # Validate file extension
        if output_path.suffix.lower() not in ['.glb', '.gltf']:
            raise ValueError(
                f"Invalid file extension '{output_path.suffix}'. "
                f"Must be '.glb' or '.gltf'."
            )

        logger.info(f"Exporting animated trajectory to GLB: {output_path}")

        # Get trajectory frames
        frames = trajectory_object.children
        if not frames:
            raise ValueError("Trajectory has no frames")

        logger.info(f"  Original frames: {len(frames)}")

        # Add reverse frames for cycling if requested
        if cycle_animation and len(frames) > 1:
            # Add reverse frames (excluding first and last to avoid duplicates)
            reverse_frames = frames[-2:0:-1]
            frames = frames + reverse_frames
            logger.info(f"  Cycling enabled: added {len(reverse_frames)} reverse frames")

        num_frames = len(frames)
        logger.info(f"  Total frames: {num_frames}")
        logger.info(f"  FPS: {fps}")
        logger.info(f"  Duration: {num_frames / fps:.2f} seconds")
        logger.info(f"  Resolution: {resolution}")

        # Verify all frames have same atom count
        num_atoms_per_frame = [len(frame.molecule) for frame in frames]
        if not all(n == num_atoms_per_frame[0] for n in num_atoms_per_frame):
            raise ValueError(
                f"All trajectory frames must have the same number of atoms. "
                f"Found frames with: {set(num_atoms_per_frame)} atoms"
            )

        num_atoms = num_atoms_per_frame[0]
        logger.info(f"  Atoms: {num_atoms}")

        # Get first frame for geometry
        first_frame = frames[0]
        molecule = first_frame.molecule
        settings = first_frame.render_settings

        # Use the scene manager's renderer to respect custom palettes
        from dataclasses import asdict
        renderer = self.scene_manager.molecule_renderer

        # Convert settings to dict (renderer expects dict)
        settings_dict = asdict(settings) if hasattr(settings, '__dataclass_fields__') else settings

        # Override resolution with user-provided value
        settings_dict['resolution'] = resolution

        # Calculate scale factor
        # Collect all positions across all frames to find bounding box
        all_positions = np.vstack([frame.molecule.positions for frame in frames])
        bbox_min = all_positions.min(axis=0)
        bbox_max = all_positions.max(axis=0)
        bbox_size = bbox_max - bbox_min
        max_extent = np.max(bbox_size)

        # Handle scale parameter
        if scale == "auto":
            # Auto-scale to fit in a 2-unit box (reasonable for most viewers)
            target_size = 2.0
            scale_factor = target_size / max_extent if max_extent > 0 else 1.0
            logger.info(f"  Auto-scaling: {max_extent:.2f} Å -> {target_size:.2f} units (scale={scale_factor:.4f})")
        elif scale is not None:
            scale_factor = float(scale)
            logger.info(f"  Scale factor: {scale_factor} (max extent: {max_extent:.2f} Å -> {max_extent * scale_factor:.2f} units)")
        else:
            scale_factor = 1.0
            logger.info(f"  No scaling (max extent: {max_extent:.2f} Å)")

        # Create atom spheres manually WITHOUT using merge() to avoid vertex deduplication
        # This is critical for skeletal animation to work correctly
        atoms_vertices_list = []
        atoms_faces_list = []
        atoms_colors_list = []
        atom_vertex_offset = 0
        vertices_per_atom = None

        for atom_idx, (position, symbol) in enumerate(zip(molecule.positions, molecule.get_chemical_symbols())):
            if not settings_dict['show_hydrogens'] and symbol == 'H':
                continue

            atom_settings = renderer.atoms_settings.get(symbol, renderer.atoms_settings['Unknown'])

            # Apply scale factor to position and radius
            scaled_position = position * scale_factor
            scaled_radius = atom_settings['radius'] * scale_factor

            sphere = pv.Sphere(
                radius=scaled_radius,
                center=scaled_position,
                theta_resolution=settings_dict['resolution'],
                phi_resolution=settings_dict['resolution']
            )
            sphere = sphere.triangulate()

            # Track vertices per atom (should be consistent)
            if vertices_per_atom is None:
                vertices_per_atom = sphere.n_points

            # Store vertices
            atoms_vertices_list.append(sphere.points.astype(np.float32))

            # Adjust face indices and store
            faces = sphere.faces.reshape(-1, 4)[:, 1:].astype(np.uint32)
            faces = faces + atom_vertex_offset
            atoms_faces_list.append(faces)

            # Create RGBA colors
            color = np.array(atom_settings['color'], dtype=np.uint8)
            alpha_value = int(settings_dict['alpha'] * 255)
            rgba = np.zeros((sphere.n_points, 4), dtype=np.uint8)
            rgba[:, :3] = color
            rgba[:, 3] = alpha_value
            atoms_colors_list.append(rgba)

            atom_vertex_offset += sphere.n_points

        # Combine all atom data
        atoms_vertices = np.vstack(atoms_vertices_list)
        atoms_faces = np.vstack(atoms_faces_list)
        atoms_colors = np.vstack(atoms_colors_list)

        logger.info(f"  Vertices per atom: {vertices_per_atom}")
        logger.info(f"  Total atom vertices: {len(atoms_vertices)}")

        # Vertices are in world space (bind pose = frame 0 positions)
        # We'll use inverse bind matrices to handle the transformation

        # Create bonds individually to track vertex ranges accurately
        bonds_vertices_list = []
        bonds_faces_list = []
        bonds_colors_list = []
        bond_skinning_info = []  # Store (atom_a, atom_b, vertex_start, vertex_count) for each bond

        bond_list = list(molecule.get_all_bonds())
        total_bond_vertices = 0

        for bond in bond_list:
            symbol_a = molecule.symbols[bond[0]]
            symbol_b = molecule.symbols[bond[1]]

            if not settings_dict['show_hydrogens'] and 'H' in [symbol_a, symbol_b]:
                continue

            atom_a, atom_b = bond
            atom_a_pos = molecule.positions[atom_a] * scale_factor
            atom_b_pos = molecule.positions[atom_b] * scale_factor
            bond_type = molecule.G[atom_a][atom_b].get('bond_type', 1)

            # Get atom radii to offset bond endpoints to atom surfaces
            radius_a = renderer.atoms_settings.get(symbol_a, renderer.atoms_settings['Unknown'])['radius']
            radius_b = renderer.atoms_settings.get(symbol_b, renderer.atoms_settings['Unknown'])['radius']

            # Create cylinders for this bond with scaled positions
            # Note: _create_bond_cylinders uses a fixed radius, so we scale the output vertices
            cylinders = renderer._create_bond_cylinders(
                molecule.positions[atom_a], molecule.positions[atom_b], bond_type,
                settings_dict['alpha'], settings_dict['resolution'],
                radius_a, radius_b
            )

            # Manually concatenate cylinders WITHOUT using merge() to avoid vertex deduplication
            bond_vertices_parts = []
            bond_faces_parts = []
            bond_colors_parts = []
            local_vertex_offset = 0

            for cylinder in cylinders:
                cylinder = cylinder.triangulate()
                # Apply scale factor to bond vertices
                scaled_bond_vertices = (cylinder.points * scale_factor).astype(np.float32)
                bond_vertices_parts.append(scaled_bond_vertices)

                # Adjust face indices for local offset
                cyl_faces = cylinder.faces.reshape(-1, 4)[:, 1:].astype(np.uint32)
                cyl_faces = cyl_faces + local_vertex_offset
                bond_faces_parts.append(cyl_faces)

                # Get colors
                if 'RGBA' in cylinder.array_names:
                    bond_colors_parts.append(cylinder['RGBA'].astype(np.uint8))
                else:
                    bond_colors_parts.append(np.full((cylinder.n_points, 4), 200, dtype=np.uint8))

                local_vertex_offset += cylinder.n_points

            if bond_vertices_parts:
                # Combine all parts of this bond
                bond_verts = np.vstack(bond_vertices_parts)
                bond_faces = np.vstack(bond_faces_parts)
                bond_colors = np.vstack(bond_colors_parts)

                vertex_start = total_bond_vertices
                vertex_count = len(bond_verts)

                # Store vertices and faces
                bonds_vertices_list.append(bond_verts)

                # Adjust face indices for global offset
                bond_faces = bond_faces + total_bond_vertices
                bonds_faces_list.append(bond_faces)

                # Store colors
                bonds_colors_list.append(bond_colors)

                # Store skinning info
                bond_skinning_info.append({
                    'atom_a': atom_a,
                    'atom_b': atom_b,
                    'vertex_start': vertex_start,
                    'vertex_count': vertex_count,
                    'pos_a': atom_a_pos,
                    'pos_b': atom_b_pos
                })

                total_bond_vertices += vertex_count

        # Combine all bonds
        bonds_vertices = None
        bonds_faces = None
        bonds_colors = None
        bonds_joints = None
        bonds_weights = None

        if bonds_vertices_list:
            bonds_vertices = np.vstack(bonds_vertices_list)
            bonds_faces = np.vstack(bonds_faces_list)
            bonds_colors = np.vstack(bonds_colors_list)

            logger.info(f"  Total bond vertices: {len(bonds_vertices)}")
            logger.info(f"  Number of bonds with vertices: {len(bond_skinning_info)}")

            # Create skinning data for bonds
            bonds_joints = np.zeros((len(bonds_vertices), 4), dtype=np.uint16)
            bonds_weights = np.zeros((len(bonds_vertices), 4), dtype=np.float32)

            # Assign skinning weights using axis-based linear interpolation
            for bond_info in bond_skinning_info:
                atom_a = bond_info['atom_a']
                atom_b = bond_info['atom_b']
                vertex_start = bond_info['vertex_start']
                vertex_count = bond_info['vertex_count']
                pos_a = bond_info['pos_a']
                pos_b = bond_info['pos_b']

                # Calculate bond direction for projection
                bond_vec = pos_b - pos_a
                bond_length = np.linalg.norm(bond_vec)

                if bond_length > 1e-6:
                    bond_dir = bond_vec / bond_length
                else:
                    bond_dir = np.array([1.0, 0.0, 0.0])

                # For each vertex in this bond
                for v_offset in range(vertex_count):
                    v_idx = vertex_start + v_offset
                    v_pos = bonds_vertices[v_idx]

                    # Project vertex onto bond axis to get interpolation factor
                    rel_pos = v_pos - pos_a
                    t = np.dot(rel_pos, bond_dir) / bond_length if bond_length > 1e-6 else 0.5

                    # Clamp to [0, 1] range
                    t = max(0.0, min(1.0, t))

                    # Linear interpolation: weight_a = (1-t), weight_b = t
                    weight_a = 1.0 - t
                    weight_b = t

                    bonds_joints[v_idx, 0] = atom_a
                    bonds_joints[v_idx, 1] = atom_b
                    bonds_weights[v_idx, 0] = weight_a
                    bonds_weights[v_idx, 1] = weight_b

        # Combine atoms and bonds
        if bonds_vertices is not None:
            # Adjust bond face indices to account for atom vertices
            bonds_faces = bonds_faces + len(atoms_vertices)

            # Combine everything
            vertices = np.vstack([atoms_vertices, bonds_vertices])
            faces = np.vstack([atoms_faces, bonds_faces])
            colors = np.vstack([atoms_colors, bonds_colors])

            # Combine skinning data
            atoms_joints = np.zeros((len(atoms_vertices), 4), dtype=np.uint16)
            atoms_weights = np.zeros((len(atoms_vertices), 4), dtype=np.float32)

            # Assign each atom's vertices to its corresponding bone
            for atom_idx in range(num_atoms):
                start_vertex = atom_idx * vertices_per_atom
                end_vertex = start_vertex + vertices_per_atom
                atoms_joints[start_vertex:end_vertex, 0] = atom_idx
                atoms_weights[start_vertex:end_vertex, 0] = 1.0

            joints = np.vstack([atoms_joints, bonds_joints])
            weights = np.vstack([atoms_weights, bonds_weights])
        else:
            # Only atoms
            vertices = atoms_vertices
            faces = atoms_faces
            colors = atoms_colors

            # Create skinning data: each vertex is controlled by one bone (atom)
            joints = np.zeros((len(vertices), 4), dtype=np.uint16)
            weights = np.zeros((len(vertices), 4), dtype=np.float32)

            # Assign each atom's vertices to its corresponding bone
            for atom_idx in range(num_atoms):
                start_vertex = atom_idx * vertices_per_atom
                end_vertex = start_vertex + vertices_per_atom
                joints[start_vertex:end_vertex, 0] = atom_idx
                weights[start_vertex:end_vertex, 0] = 1.0

        logger.info(f"  Total vertices (atoms + bonds): {len(vertices)}")

        # Get atom positions for all frames (with scale factor applied)
        atom_positions_per_frame = []
        for frame in frames:
            positions = frame.molecule.positions * scale_factor
            atom_positions_per_frame.append(positions.astype(np.float32))

        # Create animation time keyframes
        # For N frames at F fps, keyframes are at: 0, 1/F, 2/F, ..., (N-1)/F
        # This gives a duration of (N-1)/F seconds
        # E.g., 10 frames at 10 fps = keyframes 0, 0.1, 0.2, ..., 0.9 (0.9s total)
        times = np.array([i / fps for i in range(num_frames)], dtype=np.float32)

        # Build binary buffer
        buffer_data = b''

        def add_to_buffer(data):
            nonlocal buffer_data
            # Align to 4 bytes
            padding = (4 - (len(buffer_data) % 4)) % 4
            buffer_data += b'\x00' * padding
            offset = len(buffer_data)
            buffer_data += data
            return offset, len(data)

        # Add geometry data
        vertices_offset, vertices_len = add_to_buffer(vertices.tobytes())
        faces_offset, faces_len = add_to_buffer(faces.tobytes())
        colors_offset, colors_len = add_to_buffer(colors.tobytes())
        joints_offset, joints_len = add_to_buffer(joints.tobytes())
        weights_offset, weights_len = add_to_buffer(weights.tobytes())

        # Add inverse bind matrices - transform from bone space to mesh space
        inv_bind_matrices = np.zeros((num_atoms, 4, 4), dtype=np.float32)
        first_frame_positions = atom_positions_per_frame[0]
        for atom_idx in range(num_atoms):
            mat = np.eye(4, dtype=np.float32)
            mat[:3, 3] = -first_frame_positions[atom_idx]
            inv_bind_matrices[atom_idx] = mat

        # glTF requires matrices in column-major order, but NumPy uses row-major by default
        # Transpose each matrix to convert to column-major before serializing
        inv_bind_col_major = inv_bind_matrices.transpose(0, 2, 1).copy()
        inv_bind_offset, inv_bind_len = add_to_buffer(inv_bind_col_major.tobytes())

        # Add animation data (times and translations for each atom)
        times_offset, times_len = add_to_buffer(times.tobytes())

        # Create translation data for each atom (one animation track per bone)
        atom_translation_offsets = []
        for atom_idx in range(num_atoms):
            translations = np.array([positions[atom_idx] for positions in atom_positions_per_frame], dtype=np.float32)
            offset, length = add_to_buffer(translations.tobytes())
            atom_translation_offsets.append((offset, length))

        # Build glTF JSON structure
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "ChemVista Molecular Trajectory Exporter"
            },
            "scene": 0,
            "scenes": [{
                "nodes": [0]
            }],
            "nodes": [],
            "meshes": [{
                "name": "Atoms",
                "primitives": [{
                    "attributes": {
                        "POSITION": 0,
                        "COLOR_0": 1,
                        "JOINTS_0": 2,
                        "WEIGHTS_0": 3
                    },
                    "indices": 4,
                    "material": 0
                }]
            }],
            "skins": [{
                "joints": [],  # Will fill below
                "inverseBindMatrices": 5
            }],
            "materials": [{
                "name": "AtomMaterial",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0]
                },
                "alphaMode": "OPAQUE",
                "doubleSided": True
            }],
            "animations": [{
                "name": "TrajectoryAnimation",
                "channels": [],
                "samplers": []
            }],
            "accessors": [],
            "bufferViews": [],
            "buffers": [{
                "byteLength": len(buffer_data)
            }]
        }

        # Add root node
        gltf["nodes"].append({
            "name": "Root",
            "children": [1, 2]  # MeshNode and SkeletonRoot
        })

        # Add mesh node with skin
        gltf["nodes"].append({
            "name": "MeshNode",
            "mesh": 0,
            "skin": 0
        })

        # Add skeleton root node
        skeleton_children = list(range(3, 3 + num_atoms))
        gltf["nodes"].append({
            "name": "SkeletonRoot",
            "children": skeleton_children
        })

        # Add atom bones and build joints list
        joint_indices = []
        for atom_idx in range(num_atoms):
            node_idx = 3 + atom_idx
            joint_indices.append(node_idx)

            # Get atom info
            element = molecule.symbols[atom_idx]

            # Bone nodes should NOT have initial translation
            # The animation will provide the full transform
            # The inverse bind matrix handles the offset from bind pose
            gltf["nodes"].append({
                "name": f"Atom_{atom_idx}_{element}"
                # No translation - let animation handle it
            })

        # Set joints in skin
        gltf["skins"][0]["joints"] = joint_indices

        # Add accessors for geometry
        gltf["accessors"].extend([
            # 0: POSITION
            {
                "bufferView": 0,
                "componentType": 5126,  # FLOAT
                "count": len(vertices),
                "type": "VEC3",
                "min": vertices.min(axis=0).tolist(),
                "max": vertices.max(axis=0).tolist()
            },
            # 1: COLOR_0
            {
                "bufferView": 1,
                "componentType": 5121,  # UNSIGNED_BYTE
                "normalized": True,
                "count": len(vertices),
                "type": "VEC4"
            },
            # 2: JOINTS_0
            {
                "bufferView": 2,
                "componentType": 5123,  # UNSIGNED_SHORT
                "count": len(vertices),
                "type": "VEC4"
            },
            # 3: WEIGHTS_0
            {
                "bufferView": 3,
                "componentType": 5126,  # FLOAT
                "count": len(vertices),
                "type": "VEC4"
            },
            # 4: indices
            {
                "bufferView": 4,
                "componentType": 5125,  # UNSIGNED_INT
                "count": len(faces) * 3,
                "type": "SCALAR"
            },
            # 5: inverseBindMatrices
            {
                "bufferView": 5,
                "componentType": 5126,  # FLOAT
                "count": num_atoms,
                "type": "MAT4"
            },
            # 6: animation times
            {
                "bufferView": 6,
                "componentType": 5126,  # FLOAT
                "count": num_frames,
                "type": "SCALAR",
                "min": [float(times.min())],
                "max": [float(times.max())]
            }
        ])

        # Add buffer views for geometry
        gltf["bufferViews"].extend([
            {"buffer": 0, "byteOffset": vertices_offset, "byteLength": vertices_len},
            {"buffer": 0, "byteOffset": colors_offset, "byteLength": colors_len},
            {"buffer": 0, "byteOffset": joints_offset, "byteLength": joints_len},
            {"buffer": 0, "byteOffset": weights_offset, "byteLength": weights_len},
            {"buffer": 0, "byteOffset": faces_offset, "byteLength": faces_len},
            {"buffer": 0, "byteOffset": inv_bind_offset, "byteLength": inv_bind_len},
            {"buffer": 0, "byteOffset": times_offset, "byteLength": times_len}
        ])

        # Add animation channels and samplers for each atom
        for atom_idx in range(num_atoms):
            node_idx = joint_indices[atom_idx]
            sampler_idx = atom_idx
            accessor_idx = 7 + atom_idx

            # Add translation accessor for this atom
            offset, length = atom_translation_offsets[atom_idx]
            gltf["accessors"].append({
                "bufferView": 7 + atom_idx,
                "componentType": 5126,  # FLOAT
                "count": num_frames,
                "type": "VEC3"
            })

            # Add buffer view for translations
            gltf["bufferViews"].append({
                "buffer": 0,
                "byteOffset": offset,
                "byteLength": length
            })

            # Add animation channel
            gltf["animations"][0]["channels"].append({
                "sampler": sampler_idx,
                "target": {
                    "node": node_idx,
                    "path": "translation"
                }
            })

            # Add animation sampler
            gltf["animations"][0]["samplers"].append({
                "input": 6,  # times accessor
                "output": accessor_idx,
                "interpolation": "LINEAR"
            })

        # Write GLB file
        json_str = json.dumps(gltf, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        json_padding = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b' ' * json_padding

        total_length = 12 + 8 + len(json_bytes) + 8 + len(buffer_data)

        try:
            with open(output_path, 'wb') as f:
                # GLB header
                f.write(b'glTF')
                f.write(struct.pack('<I', 2))  # version
                f.write(struct.pack('<I', total_length))

                # JSON chunk
                f.write(struct.pack('<I', len(json_bytes)))
                f.write(b'JSON')
                f.write(json_bytes)

                # Binary chunk
                f.write(struct.pack('<I', len(buffer_data)))
                f.write(b'BIN\x00')
                f.write(buffer_data)

            logger.info(f"✅ Successfully exported animated trajectory to {output_path}")
            logger.info(f"   File size: {total_length / 1024:.1f} KB")
            logger.info(f"   Animation: {num_frames} frames at {fps} fps = {num_frames/fps:.1f}s")
        except Exception as e:
            logger.error(f"Failed to export animated GLB: {e}")
            raise RuntimeError(f"Failed to export animated GLB: {e}")

    def export_animated_glb(
        self,
        output_path: Union[str, Path],
        fps: int = 10,
        resolution: int = 10,
        cycle_animation: bool = False,
        scale: Optional[float] = None,
        **kwargs
    ) -> None:
        """
        Export the entire visible scene as an animated GLB file using skeletal animation.

        This method exports all visible trajectories and standalone molecules. Each atom
        becomes a bone in a unified skeleton. Trajectories are animated while standalone
        molecules remain static (but are included in the export).

        Limitations:
        - Scalar fields are not yet supported (warning will be shown)
        - All trajectories must have the same number of frames

        Args:
            output_path: Path where the GLB file will be saved
            fps: Frames per second for animation (default: 10)
            resolution: Mesh resolution for spheres/cylinders (default: 10)
            cycle_animation: If True, adds reverse frames to create a loop (default: False)
            scale: Scale factor. Use "auto" to fit in 2-unit box, or a number.
            **kwargs: Additional options (reserved for future use)

        Raises:
            ValueError: If no exportable objects found or frame count mismatch
            RuntimeError: If export fails
        """
        import json
        import struct
        from .scene_objects import TrajectoryObject, MoleculeObject, ScalarFieldObject
        from dataclasses import asdict

        output_path = Path(output_path)

        # Validate file extension
        if output_path.suffix.lower() not in ['.glb', '.gltf']:
            raise ValueError(
                f"Invalid file extension '{output_path.suffix}'. "
                f"Must be '.glb' or '.gltf'."
            )

        # Collect all visible objects
        trajectories = []
        molecules = []
        scalar_fields = []

        for obj in self.scene_manager.root.iter_visible():
            if obj == self.scene_manager.root:
                continue
            if isinstance(obj, TrajectoryObject):
                trajectories.append(obj)
            elif isinstance(obj, MoleculeObject):
                # Only add if not part of a trajectory
                if not isinstance(obj.parent, TrajectoryObject):
                    molecules.append(obj)
            elif isinstance(obj, ScalarFieldObject):
                scalar_fields.append(obj)

        # Warn about scalar fields
        if scalar_fields:
            logger.warning(
                f"⚠️  {len(scalar_fields)} scalar field(s) found but not yet supported "
                f"in animated export. They will be skipped."
            )
            print(f"⚠️  Warning: {len(scalar_fields)} scalar field(s) skipped (not supported in animated export)")

        # Check what we have to export
        if not trajectories and not molecules:
            raise ValueError("No molecules or trajectories found in scene to export")

        if not trajectories:
            # No trajectories - just static molecules, use regular export
            logger.info("No trajectories found, using static export")
            self.export_glb(output_path)
            return

        logger.info(f"Exporting animated scene to GLB: {output_path}")
        logger.info(f"  Trajectories: {len(trajectories)}")
        logger.info(f"  Standalone molecules: {len(molecules)}")

        # Determine number of frames from trajectories
        # All trajectories must have the same frame count
        frame_counts = [len(t.children) for t in trajectories]
        if len(set(frame_counts)) > 1:
            raise ValueError(
                f"All trajectories must have the same number of frames. "
                f"Found: {frame_counts}"
            )

        num_frames = frame_counts[0]

        # Add reverse frames for cycling if requested
        if cycle_animation and num_frames > 1:
            original_frames = num_frames
            num_frames = num_frames + (num_frames - 2)  # Add reverse frames excluding endpoints
            logger.info(f"  Cycling enabled: {original_frames} -> {num_frames} frames")

        logger.info(f"  Total frames: {num_frames}")
        logger.info(f"  FPS: {fps}")
        logger.info(f"  Duration: {num_frames / fps:.2f} seconds")
        logger.info(f"  Resolution: {resolution}")

        # Use the scene manager's renderer to respect custom palettes
        renderer = self.scene_manager.molecule_renderer

        # Collect all atom positions for bounding box calculation
        all_positions = []
        for traj in trajectories:
            for frame in traj.children:
                all_positions.append(frame.molecule.positions)
        for mol in molecules:
            all_positions.append(mol.molecule.positions)

        all_positions = np.vstack(all_positions)
        bbox_min = all_positions.min(axis=0)
        bbox_max = all_positions.max(axis=0)
        bbox_size = bbox_max - bbox_min
        max_extent = np.max(bbox_size)

        # Handle scale parameter
        if scale == "auto":
            target_size = 2.0
            scale_factor = target_size / max_extent if max_extent > 0 else 1.0
            logger.info(f"  Auto-scaling: {max_extent:.2f} Å -> {target_size:.2f} units (scale={scale_factor:.4f})")
        elif scale is not None:
            scale_factor = float(scale)
            logger.info(f"  Scale factor: {scale_factor}")
        else:
            scale_factor = 1.0
            logger.info(f"  No scaling (max extent: {max_extent:.2f} Å)")

        # Build combined geometry and animation data
        # Each "object" (trajectory or molecule) contributes atoms and bonds
        # Global bone index tracks across all objects
        # We also track alpha per object to create separate primitives/materials

        all_vertices = []
        all_faces = []
        all_colors = []
        all_joints = []
        all_weights = []
        all_alpha_values = []  # Track alpha for each geometry piece
        bone_positions_per_frame = []  # List of lists: [frame][bone_idx] = position

        # Initialize frame position lists
        actual_num_frames = frame_counts[0]  # Original frame count before cycling
        for _ in range(actual_num_frames):
            bone_positions_per_frame.append([])

        global_bone_idx = 0
        global_vertex_offset = 0
        bond_skinning_info = []  # Track bonds for skinning

        # Process each trajectory
        for traj_idx, traj in enumerate(trajectories):
            frames = traj.children
            first_frame = frames[0]
            molecule = first_frame.molecule
            settings = first_frame.render_settings
            settings_dict = asdict(settings) if hasattr(settings, '__dataclass_fields__') else dict(vars(settings))
            settings_dict['resolution'] = resolution

            num_atoms = len(molecule)
            traj_start_bone = global_bone_idx
            obj_alpha = settings_dict.get('alpha', 1.0)

            logger.info(f"  Trajectory '{traj.name}': {num_atoms} atoms, bones {traj_start_bone}-{traj_start_bone + num_atoms - 1}, alpha={obj_alpha}")

            # Create atom spheres for this trajectory (using first frame positions)
            for atom_idx, (position, symbol) in enumerate(zip(molecule.positions, molecule.get_chemical_symbols())):
                if not settings_dict.get('show_hydrogens', True) and symbol == 'H':
                    continue

                atom_settings = renderer.atoms_settings.get(symbol, renderer.atoms_settings['Unknown'])
                scaled_position = position * scale_factor
                scaled_radius = atom_settings['radius'] * scale_factor

                sphere = pv.Sphere(
                    radius=scaled_radius,
                    center=scaled_position,
                    theta_resolution=settings_dict['resolution'],
                    phi_resolution=settings_dict['resolution']
                )
                sphere = sphere.triangulate()

                # Store vertices
                all_vertices.append(sphere.points.astype(np.float32))

                # Adjust face indices
                faces = sphere.faces.reshape(-1, 4)[:, 1:].astype(np.uint32)
                faces = faces + global_vertex_offset
                all_faces.append(faces)

                # Create RGBA colors
                color = np.array(atom_settings['color'], dtype=np.uint8)
                alpha_value = int(obj_alpha * 255)
                rgba = np.zeros((sphere.n_points, 4), dtype=np.uint8)
                rgba[:, :3] = color
                rgba[:, 3] = alpha_value
                all_colors.append(rgba)

                # Track alpha for this geometry
                all_alpha_values.append(np.full(sphere.n_points, obj_alpha, dtype=np.float32))

                # Skinning: all vertices of this sphere belong to this bone
                joints = np.zeros((sphere.n_points, 4), dtype=np.uint16)
                weights = np.zeros((sphere.n_points, 4), dtype=np.float32)
                joints[:, 0] = global_bone_idx
                weights[:, 0] = 1.0
                all_joints.append(joints)
                all_weights.append(weights)

                global_vertex_offset += sphere.n_points
                global_bone_idx += 1

            # Store atom positions for each frame (for animation)
            for frame_idx, frame in enumerate(frames):
                positions = frame.molecule.positions * scale_factor
                for pos in positions:
                    bone_positions_per_frame[frame_idx].append(pos.astype(np.float32))

            # Create bonds for this trajectory
            bond_list = list(molecule.get_all_bonds())
            for bond in bond_list:
                symbol_a = molecule.symbols[bond[0]]
                symbol_b = molecule.symbols[bond[1]]

                if not settings_dict.get('show_hydrogens', True) and 'H' in [symbol_a, symbol_b]:
                    continue

                atom_a, atom_b = bond
                atom_a_pos = molecule.positions[atom_a]
                atom_b_pos = molecule.positions[atom_b]
                bond_type = molecule.G[atom_a][atom_b].get('bond_type', 1)

                # Get atom radii to offset bond endpoints to atom surfaces
                radius_a = renderer.atoms_settings.get(symbol_a, renderer.atoms_settings['Unknown'])['radius']
                radius_b = renderer.atoms_settings.get(symbol_b, renderer.atoms_settings['Unknown'])['radius']

                cylinders = renderer._create_bond_cylinders(
                    atom_a_pos, atom_b_pos, bond_type,
                    obj_alpha, settings_dict['resolution'],
                    radius_a, radius_b
                )

                bond_vertex_start = global_vertex_offset
                for cylinder in cylinders:
                    cylinder = cylinder.triangulate()
                    scaled_verts = (cylinder.points * scale_factor).astype(np.float32)
                    all_vertices.append(scaled_verts)

                    faces = cylinder.faces.reshape(-1, 4)[:, 1:].astype(np.uint32)
                    faces = faces + global_vertex_offset
                    all_faces.append(faces)

                    if 'RGBA' in cylinder.array_names:
                        all_colors.append(cylinder['RGBA'].astype(np.uint8))
                    else:
                        rgba = np.full((cylinder.n_points, 4), 200, dtype=np.uint8)
                        rgba[:, 3] = int(obj_alpha * 255)
                        all_colors.append(rgba)

                    # Track alpha for this geometry
                    all_alpha_values.append(np.full(cylinder.n_points, obj_alpha, dtype=np.float32))

                    # Placeholder skinning (will be set properly below)
                    joints = np.zeros((cylinder.n_points, 4), dtype=np.uint16)
                    weights = np.zeros((cylinder.n_points, 4), dtype=np.float32)
                    all_joints.append(joints)
                    all_weights.append(weights)

                    global_vertex_offset += cylinder.n_points

                bond_vertex_count = global_vertex_offset - bond_vertex_start
                bond_skinning_info.append({
                    'atom_a_bone': traj_start_bone + atom_a,
                    'atom_b_bone': traj_start_bone + atom_b,
                    'vertex_start': bond_vertex_start,
                    'vertex_count': bond_vertex_count,
                    'pos_a': atom_a_pos * scale_factor,
                    'pos_b': atom_b_pos * scale_factor
                })

        # Process standalone molecules (static - same position for all frames)
        for mol_idx, mol_obj in enumerate(molecules):
            molecule = mol_obj.molecule
            settings = mol_obj.render_settings
            settings_dict = asdict(settings) if hasattr(settings, '__dataclass_fields__') else dict(vars(settings))
            settings_dict['resolution'] = resolution

            num_atoms = len(molecule)
            mol_start_bone = global_bone_idx
            obj_alpha = settings_dict.get('alpha', 1.0)

            logger.info(f"  Molecule '{mol_obj.name}': {num_atoms} atoms (static), bones {mol_start_bone}-{mol_start_bone + num_atoms - 1}, alpha={obj_alpha}")

            # Create atom spheres
            for atom_idx, (position, symbol) in enumerate(zip(molecule.positions, molecule.get_chemical_symbols())):
                if not settings_dict.get('show_hydrogens', True) and symbol == 'H':
                    continue

                atom_settings = renderer.atoms_settings.get(symbol, renderer.atoms_settings['Unknown'])
                scaled_position = position * scale_factor
                scaled_radius = atom_settings['radius'] * scale_factor

                sphere = pv.Sphere(
                    radius=scaled_radius,
                    center=scaled_position,
                    theta_resolution=settings_dict['resolution'],
                    phi_resolution=settings_dict['resolution']
                )
                sphere = sphere.triangulate()

                all_vertices.append(sphere.points.astype(np.float32))

                faces = sphere.faces.reshape(-1, 4)[:, 1:].astype(np.uint32)
                faces = faces + global_vertex_offset
                all_faces.append(faces)

                color = np.array(atom_settings['color'], dtype=np.uint8)
                alpha_value = int(obj_alpha * 255)
                rgba = np.zeros((sphere.n_points, 4), dtype=np.uint8)
                rgba[:, :3] = color
                rgba[:, 3] = alpha_value
                all_colors.append(rgba)

                # Track alpha for this geometry
                all_alpha_values.append(np.full(sphere.n_points, obj_alpha, dtype=np.float32))

                joints = np.zeros((sphere.n_points, 4), dtype=np.uint16)
                weights = np.zeros((sphere.n_points, 4), dtype=np.float32)
                joints[:, 0] = global_bone_idx
                weights[:, 0] = 1.0
                all_joints.append(joints)
                all_weights.append(weights)

                global_vertex_offset += sphere.n_points
                global_bone_idx += 1

            # Static molecule: same position for all frames
            static_positions = molecule.positions * scale_factor
            for frame_idx in range(actual_num_frames):
                for pos in static_positions:
                    bone_positions_per_frame[frame_idx].append(pos.astype(np.float32))

            # Create bonds for this molecule
            bond_list = list(molecule.get_all_bonds())
            for bond in bond_list:
                symbol_a = molecule.symbols[bond[0]]
                symbol_b = molecule.symbols[bond[1]]

                if not settings_dict.get('show_hydrogens', True) and 'H' in [symbol_a, symbol_b]:
                    continue

                atom_a, atom_b = bond
                atom_a_pos = molecule.positions[atom_a]
                atom_b_pos = molecule.positions[atom_b]
                bond_type = molecule.G[atom_a][atom_b].get('bond_type', 1)

                # Get atom radii to offset bond endpoints to atom surfaces
                radius_a = renderer.atoms_settings.get(symbol_a, renderer.atoms_settings['Unknown'])['radius']
                radius_b = renderer.atoms_settings.get(symbol_b, renderer.atoms_settings['Unknown'])['radius']

                cylinders = renderer._create_bond_cylinders(
                    atom_a_pos, atom_b_pos, bond_type,
                    obj_alpha, settings_dict['resolution'],
                    radius_a, radius_b
                )

                bond_vertex_start = global_vertex_offset
                for cylinder in cylinders:
                    cylinder = cylinder.triangulate()
                    scaled_verts = (cylinder.points * scale_factor).astype(np.float32)
                    all_vertices.append(scaled_verts)

                    faces = cylinder.faces.reshape(-1, 4)[:, 1:].astype(np.uint32)
                    faces = faces + global_vertex_offset
                    all_faces.append(faces)

                    if 'RGBA' in cylinder.array_names:
                        all_colors.append(cylinder['RGBA'].astype(np.uint8))
                    else:
                        rgba = np.full((cylinder.n_points, 4), 200, dtype=np.uint8)
                        rgba[:, 3] = int(obj_alpha * 255)
                        all_colors.append(rgba)

                    # Track alpha for this geometry
                    all_alpha_values.append(np.full(cylinder.n_points, obj_alpha, dtype=np.float32))

                    joints = np.zeros((cylinder.n_points, 4), dtype=np.uint16)
                    weights = np.zeros((cylinder.n_points, 4), dtype=np.float32)
                    all_joints.append(joints)
                    all_weights.append(weights)

                    global_vertex_offset += cylinder.n_points

                bond_vertex_count = global_vertex_offset - bond_vertex_start
                bond_skinning_info.append({
                    'atom_a_bone': mol_start_bone + atom_a,
                    'atom_b_bone': mol_start_bone + atom_b,
                    'vertex_start': bond_vertex_start,
                    'vertex_count': bond_vertex_count,
                    'pos_a': atom_a_pos * scale_factor,
                    'pos_b': atom_b_pos * scale_factor
                })

        # Combine all arrays
        vertices = np.vstack(all_vertices)
        faces = np.vstack(all_faces)
        colors = np.vstack(all_colors)
        joints = np.vstack(all_joints)
        weights = np.vstack(all_weights)
        alpha_per_vertex = np.concatenate(all_alpha_values)

        total_bones = global_bone_idx
        logger.info(f"  Total bones: {total_bones}")
        logger.info(f"  Total vertices: {len(vertices)}")

        # Apply bond skinning (two-bone weighting for each bond)
        for bond_info in bond_skinning_info:
            bone_a = bond_info['atom_a_bone']
            bone_b = bond_info['atom_b_bone']
            pos_a = bond_info['pos_a']
            pos_b = bond_info['pos_b']
            start = bond_info['vertex_start']
            count = bond_info['vertex_count']

            bond_vec = pos_b - pos_a
            bond_length = np.linalg.norm(bond_vec)
            bond_dir = bond_vec / bond_length if bond_length > 0 else np.array([1, 0, 0])

            for i in range(count):
                vert_pos = vertices[start + i]
                rel_pos = vert_pos - pos_a
                t = np.dot(rel_pos, bond_dir) / bond_length if bond_length > 0 else 0.5
                t = max(0.0, min(1.0, t))

                joints[start + i, 0] = bone_a
                joints[start + i, 1] = bone_b
                weights[start + i, 0] = 1.0 - t
                weights[start + i, 1] = t

        # Handle cycling - add reverse frames
        if cycle_animation and actual_num_frames > 1:
            for frame_idx in range(actual_num_frames - 2, 0, -1):
                bone_positions_per_frame.append(bone_positions_per_frame[frame_idx])

        # Create animation time keyframes
        times = np.array([i / fps for i in range(num_frames)], dtype=np.float32)

        # Build binary buffer
        buffer_data = b''

        def add_to_buffer(data):
            nonlocal buffer_data
            padding = (4 - (len(buffer_data) % 4)) % 4
            buffer_data += b'\x00' * padding
            offset = len(buffer_data)
            buffer_data += data
            return offset, len(data)

        # Add geometry data
        vertices_offset, vertices_len = add_to_buffer(vertices.tobytes())
        faces_offset, faces_len = add_to_buffer(faces.tobytes())
        colors_offset, colors_len = add_to_buffer(colors.tobytes())
        joints_offset, joints_len = add_to_buffer(joints.tobytes())
        weights_offset, weights_len = add_to_buffer(weights.tobytes())

        # Add inverse bind matrices
        inv_bind_matrices = np.zeros((total_bones, 4, 4), dtype=np.float32)
        first_frame_positions = bone_positions_per_frame[0]
        for bone_idx in range(total_bones):
            mat = np.eye(4, dtype=np.float32)
            mat[0, 3] = -first_frame_positions[bone_idx][0]
            mat[1, 3] = -first_frame_positions[bone_idx][1]
            mat[2, 3] = -first_frame_positions[bone_idx][2]
            inv_bind_matrices[bone_idx] = mat

        # glTF requires matrices in column-major order, but NumPy uses row-major by default
        # Transpose each matrix to convert to column-major before serializing
        inv_bind_col_major = inv_bind_matrices.transpose(0, 2, 1).copy()
        inv_bind_offset, inv_bind_len = add_to_buffer(inv_bind_col_major.tobytes())

        # Add animation timestamps
        times_offset, times_len = add_to_buffer(times.tobytes())

        # Add per-bone translations for all frames
        bone_translation_offsets = []
        for bone_idx in range(total_bones):
            translations = np.array([
                bone_positions_per_frame[frame_idx][bone_idx]
                for frame_idx in range(num_frames)
            ], dtype=np.float32)
            offset, length = add_to_buffer(translations.tobytes())
            bone_translation_offsets.append((offset, length))

        # Separate faces into opaque and transparent groups
        # Each face's alpha is determined by its first vertex
        face_alphas = alpha_per_vertex[faces[:, 0]]

        opaque_mask = face_alphas >= 1.0
        transparent_mask = ~opaque_mask

        opaque_faces = faces[opaque_mask]
        transparent_faces = faces[transparent_mask]

        has_opaque = len(opaque_faces) > 0
        has_transparent = len(transparent_faces) > 0

        logger.info(f"  Opaque faces: {len(opaque_faces)}, Transparent faces: {len(transparent_faces)}")

        # Add indices to buffer - opaque first, then transparent
        opaque_indices_offset = None
        opaque_indices_len = 0
        transparent_indices_offset = None
        transparent_indices_len = 0

        if has_opaque:
            opaque_flat = opaque_faces.flatten().astype(np.uint32)
            opaque_indices_offset, opaque_indices_len = add_to_buffer(opaque_flat.tobytes())

        if has_transparent:
            transparent_flat = transparent_faces.flatten().astype(np.uint32)
            transparent_indices_offset, transparent_indices_len = add_to_buffer(transparent_flat.tobytes())

        # Build glTF JSON
        # Create nodes: root + skeleton root + all bone nodes
        joint_indices = list(range(2, 2 + total_bones))

        gltf = {
            "asset": {"version": "2.0", "generator": "ChemVista"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [
                {"name": "Root", "children": [1]},
                {"name": "Skeleton", "children": joint_indices}
            ],
            "meshes": [],
            "materials": [],
            "skins": [{
                "joints": joint_indices,
                "inverseBindMatrices": None  # Will be set below
            }],
            "animations": [{
                "name": "TrajectoryAnimation",
                "channels": [],
                "samplers": []
            }],
            "accessors": [],
            "bufferViews": [],
            "buffers": []
        }

        # Add bone nodes
        for bone_idx in range(total_bones):
            pos = first_frame_positions[bone_idx]
            gltf["nodes"].append({
                "name": f"Bone_{bone_idx}",
                "translation": [float(pos[0]), float(pos[1]), float(pos[2])]
            })

        # Add accessors for shared vertex data
        v_min = vertices.min(axis=0).tolist()
        v_max = vertices.max(axis=0).tolist()

        # Base accessors (shared by all meshes):
        # 0: POSITION
        # 1: COLOR_0
        # 2: JOINTS_0
        # 3: WEIGHTS_0
        # 4: inverseBindMatrices
        # 5: animation times
        # Then: indices for opaque (if any), indices for transparent (if any)
        # Then: animation translations per bone

        gltf["accessors"] = [
            {"bufferView": 0, "componentType": 5126, "count": len(vertices), "type": "VEC3", "min": v_min, "max": v_max},
            {"bufferView": 1, "componentType": 5121, "count": len(colors), "type": "VEC4", "normalized": True},
            {"bufferView": 2, "componentType": 5123, "count": len(joints), "type": "VEC4"},
            {"bufferView": 3, "componentType": 5126, "count": len(weights), "type": "VEC4"},
            {"bufferView": 4, "componentType": 5126, "count": total_bones, "type": "MAT4"},
            {"bufferView": 5, "componentType": 5126, "count": num_frames, "type": "SCALAR", "min": [float(times.min())], "max": [float(times.max())]}
        ]

        gltf["bufferViews"] = [
            {"buffer": 0, "byteOffset": vertices_offset, "byteLength": vertices_len},
            {"buffer": 0, "byteOffset": colors_offset, "byteLength": colors_len},
            {"buffer": 0, "byteOffset": joints_offset, "byteLength": joints_len},
            {"buffer": 0, "byteOffset": weights_offset, "byteLength": weights_len},
            {"buffer": 0, "byteOffset": inv_bind_offset, "byteLength": inv_bind_len},
            {"buffer": 0, "byteOffset": times_offset, "byteLength": times_len}
        ]

        # Set inverseBindMatrices accessor index
        gltf["skins"][0]["inverseBindMatrices"] = 4

        # Animation times accessor index
        times_accessor_idx = 5

        # Add opaque mesh if we have opaque faces
        if has_opaque:
            opaque_indices_accessor = len(gltf["accessors"])
            gltf["accessors"].append({
                "bufferView": len(gltf["bufferViews"]),
                "componentType": 5125,
                "count": len(opaque_flat),
                "type": "SCALAR"
            })
            gltf["bufferViews"].append({
                "buffer": 0,
                "byteOffset": opaque_indices_offset,
                "byteLength": opaque_indices_len
            })

            opaque_material_idx = len(gltf["materials"])
            gltf["materials"].append({
                "name": "OpaqueMaterial",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0]
                },
                "alphaMode": "OPAQUE",
                "doubleSided": True
            })

            opaque_mesh_idx = len(gltf["meshes"])
            gltf["meshes"].append({
                "name": "OpaqueMesh",
                "primitives": [{
                    "attributes": {
                        "POSITION": 0,
                        "COLOR_0": 1,
                        "JOINTS_0": 2,
                        "WEIGHTS_0": 3
                    },
                    "indices": opaque_indices_accessor,
                    "material": opaque_material_idx,
                    "mode": 4
                }]
            })

            # Add mesh node with skin
            opaque_mesh_node_idx = len(gltf["nodes"])
            gltf["nodes"].append({
                "name": "OpaqueMeshNode",
                "mesh": opaque_mesh_idx,
                "skin": 0
            })
            gltf["nodes"][0]["children"].append(opaque_mesh_node_idx)

        # Add transparent mesh if we have transparent faces
        if has_transparent:
            transparent_indices_accessor = len(gltf["accessors"])
            gltf["accessors"].append({
                "bufferView": len(gltf["bufferViews"]),
                "componentType": 5125,
                "count": len(transparent_flat),
                "type": "SCALAR"
            })
            gltf["bufferViews"].append({
                "buffer": 0,
                "byteOffset": transparent_indices_offset,
                "byteLength": transparent_indices_len
            })

            transparent_material_idx = len(gltf["materials"])
            gltf["materials"].append({
                "name": "TransparentMaterial",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0]
                },
                "alphaMode": "BLEND",
                "doubleSided": True
            })

            transparent_mesh_idx = len(gltf["meshes"])
            gltf["meshes"].append({
                "name": "TransparentMesh",
                "primitives": [{
                    "attributes": {
                        "POSITION": 0,
                        "COLOR_0": 1,
                        "JOINTS_0": 2,
                        "WEIGHTS_0": 3
                    },
                    "indices": transparent_indices_accessor,
                    "material": transparent_material_idx,
                    "mode": 4
                }]
            })

            # Add mesh node with skin
            transparent_mesh_node_idx = len(gltf["nodes"])
            gltf["nodes"].append({
                "name": "TransparentMeshNode",
                "mesh": transparent_mesh_idx,
                "skin": 0
            })
            gltf["nodes"][0]["children"].append(transparent_mesh_node_idx)

        for bone_idx in range(total_bones):
            node_idx = joint_indices[bone_idx]
            sampler_idx = bone_idx

            # Get current accessor/bufferView indices
            accessor_idx = len(gltf["accessors"])
            buffer_view_idx = len(gltf["bufferViews"])

            offset, length = bone_translation_offsets[bone_idx]
            gltf["accessors"].append({
                "bufferView": buffer_view_idx,
                "componentType": 5126,
                "count": num_frames,
                "type": "VEC3"
            })

            gltf["bufferViews"].append({
                "buffer": 0,
                "byteOffset": offset,
                "byteLength": length
            })

            gltf["animations"][0]["channels"].append({
                "sampler": sampler_idx,
                "target": {"node": node_idx, "path": "translation"}
            })

            gltf["animations"][0]["samplers"].append({
                "input": times_accessor_idx,
                "output": accessor_idx,
                "interpolation": "LINEAR"
            })

        # Finalize buffer
        gltf["buffers"] = [{"byteLength": len(buffer_data)}]

        # Write GLB file
        json_str = json.dumps(gltf, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        json_padding = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b' ' * json_padding

        total_length = 12 + 8 + len(json_bytes) + 8 + len(buffer_data)

        try:
            with open(output_path, 'wb') as f:
                f.write(b'glTF')
                f.write(struct.pack('<I', 2))
                f.write(struct.pack('<I', total_length))

                f.write(struct.pack('<I', len(json_bytes)))
                f.write(b'JSON')
                f.write(json_bytes)

                f.write(struct.pack('<I', len(buffer_data)))
                f.write(b'BIN\x00')
                f.write(buffer_data)

            logger.info(f"✅ Successfully exported animated scene to {output_path}")
            logger.info(f"   File size: {total_length / 1024:.1f} KB")
            logger.info(f"   Animation: {num_frames} frames at {fps} fps = {num_frames/fps:.1f}s")
        except Exception as e:
            logger.error(f"Failed to export animated GLB: {e}")
            raise RuntimeError(f"Failed to export animated GLB: {e}")

    def export_scene_to_glb(
        self,
        output_path: Union[str, Path],
        **kwargs
    ) -> None:
        """
        Convenience method that exports the entire scene to GLB.

        This is an alias for export_glb() for clarity.

        Args:
            output_path: Path where the GLB file will be saved
            **kwargs: Additional arguments passed to export_glb()
        """
        self.export_glb(output_path, **kwargs)
