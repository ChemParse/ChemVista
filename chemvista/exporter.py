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

        # Import renderer
        from .renderer.molecule import MoleculeRenderer
        from dataclasses import asdict
        renderer = MoleculeRenderer()

        # Convert settings to dict (renderer expects dict)
        settings_dict = asdict(settings) if hasattr(settings, '__dataclass_fields__') else settings

        # Override resolution with user-provided value
        settings_dict['resolution'] = resolution

        # Create sphere geometry for each atom (using first frame positions)
        atoms_mesh = renderer._create_atoms_mesh(molecule, settings_dict)

        # Convert to trimesh
        atoms_mesh = atoms_mesh.triangulate()
        atoms_vertices = atoms_mesh.points.astype(np.float32)
        atoms_faces = atoms_mesh.faces.reshape(-1, 4)[:, 1:].astype(np.uint32)

        # Get RGBA colors for atoms
        if 'RGBA' in atoms_mesh.array_names:
            atoms_colors = atoms_mesh['RGBA'].astype(np.uint8)
        else:
            # Fallback: white
            atoms_colors = np.full((len(atoms_vertices), 4), 255, dtype=np.uint8)

        # Calculate vertices per atom (assuming spheres have same resolution)
        vertices_per_atom = len(atoms_vertices) // num_atoms
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
            if not settings_dict['show_hydrogens'] and 'H' in [molecule.symbols[i] for i in bond]:
                continue

            atom_a, atom_b = bond
            atom_a_pos = molecule.positions[atom_a]
            atom_b_pos = molecule.positions[atom_b]
            bond_type = molecule.G[atom_a][atom_b].get('bond_type', 1)

            # Create cylinders for this bond (same as renderer does)
            cylinders = renderer._create_bond_cylinders(
                atom_a_pos, atom_b_pos, bond_type,
                settings_dict['alpha'], settings_dict['resolution']
            )

            # Merge cylinders for this bond
            bond_mesh = None
            for cylinder in cylinders:
                if bond_mesh is None:
                    bond_mesh = cylinder
                else:
                    bond_mesh = bond_mesh.merge(cylinder)

            if bond_mesh is not None:
                bond_mesh = bond_mesh.triangulate()
                vertex_start = total_bond_vertices
                vertex_count = bond_mesh.n_points

                # Store vertices and faces
                bonds_vertices_list.append(bond_mesh.points.astype(np.float32))

                # Adjust face indices
                faces = bond_mesh.faces.reshape(-1, 4)[:, 1:].astype(np.uint32)
                faces = faces + total_bond_vertices  # Offset by current vertex count
                bonds_faces_list.append(faces)

                # Get colors
                if 'RGBA' in bond_mesh.array_names:
                    bonds_colors_list.append(bond_mesh['RGBA'].astype(np.uint8))
                else:
                    bonds_colors_list.append(np.full((vertex_count, 4), 200, dtype=np.uint8))

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

        # Get atom positions for all frames
        atom_positions_per_frame = []
        for frame in frames:
            positions = frame.molecule.positions
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
