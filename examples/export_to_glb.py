#!/usr/bin/env python3
"""
Example script demonstrating GLB export functionality for PowerPoint 3D

This script shows how to export molecules and scalar fields to GLB format,
which can be imported into PowerPoint as 3D objects.
"""

from pathlib import Path
from chemvista import SceneManager

# Create a scene manager
scene_manager = SceneManager()

# Example 1: Export a simple molecule
print("Example 1: Exporting a simple molecule (benzene)")
scene_manager.load_xyz("../tests/data/C6H6.xyz")
scene_manager.export_to_glb("benzene.glb")
print("✅ Exported to benzene.glb")

# Clear the scene for the next example
scene_manager = SceneManager()

# Example 2: Export a molecule with scalar field (electron density)
print("\nExample 2: Exporting a molecule with electron density field")
scene_manager.load_molecule_from_cube("../tests/data/C2H4.eldens.cube")
scene_manager.export_to_glb("ethylene_with_density.glb")
print("✅ Exported to ethylene_with_density.glb")

# Example 3: Programmatic usage with custom settings
print("\nExample 3: Using the Exporter class directly")
from chemvista import Exporter

scene_manager = SceneManager()
mol_obj = scene_manager.load_xyz("../tests/data/C6H6.xyz")

# Adjust rendering settings before export
mol_obj.render_settings.alpha = 0.8  # Make molecule slightly transparent
mol_obj.render_settings.show_hydrogens = True
mol_obj.render_settings.resolution = 30  # Higher resolution

# Export with custom options
exporter = Exporter(scene_manager)
exporter.export_glb(
    "benzene_custom.glb",
    double_sided=True,
    alpha_mode="BLEND"  # Use BLEND for transparency support
)
print("✅ Exported to benzene_custom.glb with custom settings")

print("\n" + "="*60)
print("All examples completed!")
print("="*60)
print("\nTo use these files in PowerPoint:")
print("1. Open PowerPoint")
print("2. Go to Insert > 3D Models > From a File...")
print("3. Select any of the generated .glb files")
print("4. The molecule will appear as a rotatable 3D object!")
print("\nYou can also view these files in:")
print("- Windows 3D Viewer")
print("- Online viewers like https://gltf-viewer.donmccurdy.com/")
print("- Blender, Sketchfab, and other 3D software")
