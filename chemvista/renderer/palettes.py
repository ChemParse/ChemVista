"""
Color palette system for molecule rendering.

Provides discovery and loading of color palettes from the settings/palettes
directory, as well as utilities for loading custom palettes from JSON files.

Built-in palettes are stored as JSON files in chemvista/settings/palettes/:
- chemvista.json: Default ChemVista colors
- cpk.json: Classic CPK (Corey-Pauling-Koltun) coloring
- jmol.json: Jmol/RasMol coloring scheme

Custom palettes can be loaded from any path or added to the palettes directory.
"""

import json
import pathlib
import logging
from typing import Dict, Any, List
from copy import deepcopy

# Path to palettes directory
PALETTES_DIR = pathlib.Path(__file__).parent.parent / 'settings' / 'palettes'

# Default palette name
DEFAULT_PALETTE = 'chemvista'

logger = logging.getLogger("chemvista.renderer.palettes")


def _discover_palettes() -> Dict[str, pathlib.Path]:
    """
    Discover all available palette files in the palettes directory.

    Returns:
        Dictionary mapping palette names (without .json extension) to file paths
    """
    palettes = {}
    if PALETTES_DIR.exists():
        for json_file in PALETTES_DIR.glob('*.json'):
            name = json_file.stem.lower()
            palettes[name] = json_file
    return palettes


# Discover built-in palettes at module load time
BUILTIN_PALETTES = _discover_palettes()


def get_available_palettes() -> List[str]:
    """
    Return list of available built-in palette names.

    Palettes are discovered from JSON files in the settings/palettes directory.
    """
    return sorted(BUILTIN_PALETTES.keys())


def load_default_settings() -> Dict[str, Any]:
    """
    Load the default ChemVista atom settings.

    Returns:
        Dictionary of atom settings with colors and radii
    """
    return load_palette(DEFAULT_PALETTE)


def load_palette(name_or_path: str, radius_scale: float = 1.0) -> Dict[str, Any]:
    """
    Load a color palette by name or from a file path.

    Args:
        name_or_path: Either a built-in palette name ('chemvista', 'cpk', 'jmol')
                     or a path to a JSON file with custom settings
        radius_scale: Scale factor to apply to all radii (default: 1.0)

    Returns:
        Full atom settings dictionary ready for use by renderers

    Raises:
        ValueError: If palette name is unknown and path doesn't exist
        json.JSONDecodeError: If JSON file is invalid

    Example:
        >>> settings = load_palette('cpk')
        >>> settings = load_palette('jmol', radius_scale=0.8)
        >>> settings = load_palette('/path/to/custom_palette.json')
    """
    name_lower = name_or_path.lower()

    # Check if it's a built-in palette
    if name_lower in BUILTIN_PALETTES:
        palette_path = BUILTIN_PALETTES[name_lower]
        logger.debug(f"Loading built-in palette '{name_lower}' from {palette_path}")
        with open(palette_path) as f:
            settings = json.load(f)
    else:
        # Try as file path
        path = pathlib.Path(name_or_path)
        if path.exists():
            logger.debug(f"Loading palette from file: {path}")
            with open(path) as f:
                settings = json.load(f)
        else:
            # Neither built-in nor valid path
            available = ", ".join(get_available_palettes())
            raise ValueError(
                f"Unknown palette '{name_or_path}'. "
                f"Available built-in palettes: {available}. "
                f"Or provide a path to a custom JSON palette file."
            )

    # Apply radius scale if needed
    if radius_scale != 1.0:
        settings = deepcopy(settings)
        for symbol in settings:
            if "radius" in settings[symbol]:
                settings[symbol]["radius"] = settings[symbol]["radius"] * radius_scale

    return settings


def save_palette(settings: Dict[str, Any], output_path: str) -> None:
    """
    Save atom settings to a JSON file.

    Args:
        settings: Atom settings dictionary
        output_path: Path to save the JSON file

    Example:
        >>> save_palette(my_settings, '/path/to/my_palette.json')
    """
    path = pathlib.Path(output_path)
    with open(path, 'w') as f:
        json.dump(settings, f, indent=4)
    logger.info(f"Saved palette to {path}")


def create_settings_from_colors(color_dict: Dict[str, List[int]],
                                 base_settings: Dict[str, Any] = None,
                                 radius_scale: float = 1.0) -> Dict[str, Any]:
    """
    Create full atom settings from a color dictionary.

    Uses the base settings (or default ChemVista settings) for radii,
    and applies the provided colors.

    Args:
        color_dict: Dictionary mapping element symbols to [R, G, B] colors
        base_settings: Base settings to use for radii. If None, uses default.
        radius_scale: Scale factor to apply to all radii (default: 1.0)

    Returns:
        Full settings dictionary with colors and radii for each element
    """
    if base_settings is None:
        base_settings = load_default_settings()

    # Deep copy to avoid modifying the original
    result = deepcopy(base_settings)

    # Apply colors from color_dict
    for symbol, color in color_dict.items():
        if symbol in result:
            result[symbol]["color"] = color
        else:
            # Create entry for new elements not in base
            # Use Unknown radius as default
            unknown_radius = base_settings.get("Unknown", {"radius": 0.2})["radius"]
            result[symbol] = {"color": color, "radius": unknown_radius}

    # Apply radius scale (skip non-element keys like 'bonds')
    if radius_scale != 1.0:
        for symbol in result:
            if symbol != 'bonds' and 'radius' in result[symbol]:
                result[symbol]["radius"] = result[symbol]["radius"] * radius_scale

    return result


def get_palette_path(name: str) -> pathlib.Path:
    """
    Get the file path for a built-in palette.

    Args:
        name: Palette name (case-insensitive)

    Returns:
        Path to the palette JSON file

    Raises:
        ValueError: If palette name is unknown
    """
    name_lower = name.lower()
    if name_lower in BUILTIN_PALETTES:
        return BUILTIN_PALETTES[name_lower]
    raise ValueError(f"Unknown palette '{name}'. Available: {', '.join(get_available_palettes())}")


def refresh_palettes() -> None:
    """
    Re-discover palettes from the palettes directory.

    Call this after adding new palette files to the directory
    to make them available.
    """
    global BUILTIN_PALETTES
    BUILTIN_PALETTES = _discover_palettes()
    logger.info(f"Refreshed palettes: {list(BUILTIN_PALETTES.keys())}")
