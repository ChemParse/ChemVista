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
