"""
ChemVista color palettes.

This directory contains JSON files defining atom color palettes.
Each JSON file should have the structure:
{
    "Element": {"color": [R, G, B], "radius": float},
    ...
}

Built-in palettes:
- chemvista.json: Default ChemVista colors (Jmol-based)
- cpk.json: Classic CPK (Corey-Pauling-Koltun) coloring
- jmol.json: Jmol/RasMol coloring scheme

Custom palettes can be added by placing JSON files in this directory
or by loading them from any path.
"""
