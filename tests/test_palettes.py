"""Tests for the palette system."""

import pytest
import json
import pathlib
import tempfile

from chemvista.renderer.palettes import (
    load_palette,
    load_default_settings,
    get_available_palettes,
    create_settings_from_colors,
    save_palette,
    BUILTIN_PALETTES,
    PALETTES_DIR,
    get_palette_path,
    refresh_palettes,
)
from chemvista.renderer import MoleculeRenderer, AnimatedMoleculeRenderer
from chemvista import SceneManager


class TestPaletteDiscovery:
    """Tests for palette directory discovery."""

    def test_palettes_directory_exists(self):
        """Test that the palettes directory exists."""
        assert PALETTES_DIR.exists()
        assert PALETTES_DIR.is_dir()

    def test_builtin_palettes_discovered(self):
        """Test that built-in palettes are discovered from directory."""
        assert 'chemvista' in BUILTIN_PALETTES
        assert 'cpk' in BUILTIN_PALETTES
        assert 'jmol' in BUILTIN_PALETTES

    def test_builtin_palettes_are_paths(self):
        """Test that discovered palettes are valid paths."""
        for name, path in BUILTIN_PALETTES.items():
            assert isinstance(path, pathlib.Path)
            assert path.exists()
            assert path.suffix == '.json'

    def test_get_palette_path(self):
        """Test getting palette file path."""
        path = get_palette_path('chemvista')
        assert path.exists()
        assert path.name == 'chemvista.json'

    def test_get_palette_path_case_insensitive(self):
        """Test that get_palette_path is case insensitive."""
        path1 = get_palette_path('cpk')
        path2 = get_palette_path('CPK')
        assert path1 == path2

    def test_get_palette_path_unknown_raises(self):
        """Test that unknown palette name raises error."""
        with pytest.raises(ValueError):
            get_palette_path('nonexistent')


class TestPaletteLoading:
    """Tests for palette loading functionality."""

    def test_get_available_palettes(self):
        """Test that available palettes are returned."""
        palettes = get_available_palettes()
        assert 'chemvista' in palettes
        assert 'cpk' in palettes
        assert 'jmol' in palettes
        # Should be sorted
        assert palettes == sorted(palettes)

    def test_load_default_settings(self):
        """Test loading default ChemVista settings."""
        settings = load_default_settings()
        assert 'H' in settings
        assert 'C' in settings
        assert 'O' in settings
        assert 'Unknown' in settings
        # Check structure
        assert 'color' in settings['C']
        assert 'radius' in settings['C']
        assert len(settings['C']['color']) == 3

    def test_load_chemvista_palette(self):
        """Test loading ChemVista palette by name."""
        settings = load_palette('chemvista')
        default = load_default_settings()
        # Should be identical
        assert settings == default

    def test_load_cpk_palette(self):
        """Test loading CPK palette by name."""
        settings = load_palette('cpk')
        # CPK has specific colors
        assert settings['C']['color'] == [80, 80, 80]  # Dark gray
        assert settings['O']['color'] == [255, 0, 0]   # Red
        assert settings['N']['color'] == [0, 0, 255]   # Blue

    def test_load_jmol_palette(self):
        """Test loading Jmol palette by name."""
        settings = load_palette('jmol')
        # Jmol has specific colors (loaded from jmol.json)
        assert settings['C']['color'] == [144, 144, 144]  # Gray
        assert settings['N']['color'] == [48, 80, 248]    # Blue

    def test_load_palette_case_insensitive(self):
        """Test that palette names are case insensitive."""
        settings1 = load_palette('cpk')
        settings2 = load_palette('CPK')
        settings3 = load_palette('Cpk')
        assert settings1 == settings2 == settings3

    def test_load_custom_palette_from_file(self):
        """Test loading palette from custom JSON file."""
        custom_settings = {
            "C": {"color": [100, 100, 100], "radius": 0.2},
            "H": {"color": [200, 200, 200], "radius": 0.1},
            "Unknown": {"color": [0, 255, 0], "radius": 0.15}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(custom_settings, f)
            temp_path = f.name

        try:
            settings = load_palette(temp_path)
            assert settings['C']['color'] == [100, 100, 100]
            assert settings['C']['radius'] == 0.2
        finally:
            pathlib.Path(temp_path).unlink()

    def test_load_unknown_palette_raises(self):
        """Test that unknown palette name raises error."""
        with pytest.raises(ValueError) as exc_info:
            load_palette('nonexistent_palette')
        assert 'Unknown palette' in str(exc_info.value)

    def test_radius_scale(self):
        """Test radius scaling."""
        settings = load_palette('chemvista', radius_scale=2.0)
        default = load_default_settings()

        # Radii should be doubled
        assert settings['C']['radius'] == default['C']['radius'] * 2.0
        assert settings['H']['radius'] == default['H']['radius'] * 2.0

    def test_radius_scale_from_file(self):
        """Test radius scaling for file-loaded palettes."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"C": {"color": [0, 0, 0], "radius": 0.5}}, f)
            temp_path = f.name

        try:
            settings = load_palette(temp_path, radius_scale=0.5)
            assert settings['C']['radius'] == 0.25
        finally:
            pathlib.Path(temp_path).unlink()


class TestCreateSettingsFromColors:
    """Tests for creating settings from color dictionaries."""

    def test_create_settings_basic(self):
        """Test creating settings from color dict."""
        colors = {"C": [50, 50, 50], "H": [255, 255, 255]}
        settings = create_settings_from_colors(colors)

        assert settings['C']['color'] == [50, 50, 50]
        assert settings['H']['color'] == [255, 255, 255]
        # Radii should come from default
        assert 'radius' in settings['C']

    def test_create_settings_with_radius_scale(self):
        """Test creating settings with radius scaling."""
        colors = {"C": [50, 50, 50]}
        settings = create_settings_from_colors(colors, radius_scale=0.5)
        default = load_default_settings()

        assert settings['C']['radius'] == default['C']['radius'] * 0.5


class TestSavePalette:
    """Tests for saving palettes."""

    def test_save_palette(self):
        """Test saving palette to file."""
        settings = {"C": {"color": [100, 100, 100], "radius": 0.2}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            save_palette(settings, temp_path)

            with open(temp_path) as f:
                loaded = json.load(f)

            assert loaded == settings
        finally:
            pathlib.Path(temp_path).unlink()


class TestRendererPalette:
    """Tests for renderer palette methods."""

    def test_molecule_renderer_set_palette(self):
        """Test MoleculeRenderer.set_palette()."""
        renderer = MoleculeRenderer()
        original_c_color = renderer.atoms_settings['C']['color'].copy()

        renderer.set_palette('cpk')

        # Color should change to CPK
        assert renderer.atoms_settings['C']['color'] == [80, 80, 80]
        assert renderer.atoms_settings['C']['color'] != original_c_color

    def test_molecule_renderer_set_atom_settings(self):
        """Test MoleculeRenderer.set_atom_settings()."""
        renderer = MoleculeRenderer()
        custom = {"C": {"color": [1, 2, 3], "radius": 0.99}}

        renderer.set_atom_settings(custom)

        assert renderer.atoms_settings == custom

    def test_animated_renderer_set_palette(self):
        """Test AnimatedMoleculeRenderer.set_palette()."""
        renderer = AnimatedMoleculeRenderer()

        renderer.set_palette('jmol')

        # Jmol C color is gray [144, 144, 144]
        assert renderer.atoms_settings['C']['color'] == [144, 144, 144]

    def test_animated_renderer_set_atom_settings(self):
        """Test AnimatedMoleculeRenderer.set_atom_settings()."""
        renderer = AnimatedMoleculeRenderer()
        custom = {"H": {"color": [10, 20, 30], "radius": 0.5}}

        renderer.set_atom_settings(custom)

        assert renderer.atoms_settings == custom


class TestSceneManagerPalette:
    """Tests for SceneManager palette methods."""

    def test_scene_manager_set_palette(self):
        """Test SceneManager.set_palette() propagates to renderer."""
        manager = SceneManager()

        manager.set_palette('cpk')

        # Check that molecule renderer was updated
        assert manager.molecule_renderer.atoms_settings['C']['color'] == [80, 80, 80]

    def test_scene_manager_set_palette_with_radius_scale(self):
        """Test SceneManager.set_palette() with radius scale."""
        manager = SceneManager()
        default = load_default_settings()

        manager.set_palette('chemvista', radius_scale=0.5)

        # Check that radii were scaled (exclude bonds from default)
        default_c_radius = default['C']['radius']
        assert manager.molecule_renderer.atoms_settings['C']['radius'] == default_c_radius * 0.5


class TestBondSettings:
    """Tests for bond settings in palettes."""

    def test_palette_includes_bond_settings(self):
        """Test that palettes include bond settings."""
        settings = load_default_settings()
        assert 'bonds' in settings
        bonds = settings['bonds']
        assert 'color' in bonds
        assert 'single' in bonds
        assert 'double' in bonds
        assert 'triple' in bonds

    def test_bond_settings_structure(self):
        """Test bond settings have correct structure."""
        settings = load_default_settings()
        bonds = settings['bonds']

        # Check single bond
        assert 'radius' in bonds['single']

        # Check double bond
        assert 'radius' in bonds['double']
        assert 'offset' in bonds['double']

        # Check triple bond
        assert 'radius' in bonds['triple']
        assert 'offset' in bonds['triple']

    def test_cpk_palette_has_bond_settings(self):
        """Test that CPK palette also has bond settings."""
        settings = load_palette('cpk')
        assert 'bonds' in settings

    def test_renderer_has_bond_settings(self):
        """Test MoleculeRenderer has bond_settings attribute."""
        renderer = MoleculeRenderer()
        assert hasattr(renderer, 'bond_settings')
        assert 'color' in renderer.bond_settings

    def test_renderer_set_palette_updates_bonds(self):
        """Test that set_palette updates bond settings."""
        renderer = MoleculeRenderer()

        # Load CPK
        renderer.set_palette('cpk')

        # Bond settings should be present
        assert 'color' in renderer.bond_settings
        assert 'single' in renderer.bond_settings

    def test_animated_renderer_has_bond_settings(self):
        """Test AnimatedMoleculeRenderer has bond_settings attribute."""
        renderer = AnimatedMoleculeRenderer()
        assert hasattr(renderer, 'bond_settings')
        assert 'color' in renderer.bond_settings

    def test_set_atom_settings_with_bonds(self):
        """Test set_atom_settings handles bond settings."""
        renderer = MoleculeRenderer()
        custom = {
            "C": {"color": [1, 2, 3], "radius": 0.99},
            "bonds": {"color": [255, 0, 0], "single": {"radius": 0.1}}
        }

        renderer.set_atom_settings(custom)

        assert renderer.atoms_settings == {"C": {"color": [1, 2, 3], "radius": 0.99}}
        assert renderer.bond_settings['color'] == [255, 0, 0]


class TestPaletteDialog:
    """Tests for the PaletteSettingsDialog widget."""

    def test_dialog_creation(self, qapp):
        """Test that dialog can be created."""
        from chemvista.gui.widgets.palette_dialog import PaletteSettingsDialog

        settings = load_default_settings()
        dialog = PaletteSettingsDialog(settings)

        assert dialog is not None
        assert dialog.windowTitle() == "Palette Settings"
        dialog.close()

    def test_dialog_preserves_settings_on_cancel(self, qapp):
        """Test that canceling preserves original settings."""
        from chemvista.gui.widgets.palette_dialog import PaletteSettingsDialog

        settings = load_default_settings()
        original_c_color = settings['C']['color'].copy()

        dialog = PaletteSettingsDialog(settings)

        # Cancel dialog
        dialog.reject()

        result = dialog.get_settings()
        assert result['C']['color'] == original_c_color
        dialog.close()

    def test_element_widget_creation(self, qapp):
        """Test ElementColorWidget creation."""
        from chemvista.gui.widgets.palette_dialog import ElementColorWidget

        widget = ElementColorWidget('C', [100, 100, 100], 0.16)

        assert widget.symbol == 'C'
        settings = widget.get_settings()
        assert settings['color'] == [100, 100, 100]
        assert settings['radius'] == 0.16
        widget.close()

    def test_element_widget_set_settings(self, qapp):
        """Test ElementColorWidget.set_settings()."""
        from chemvista.gui.widgets.palette_dialog import ElementColorWidget

        widget = ElementColorWidget('C', [100, 100, 100], 0.16)

        widget.set_settings([200, 200, 200], 0.25)

        settings = widget.get_settings()
        assert settings['color'] == [200, 200, 200]
        assert settings['radius'] == 0.25
        widget.close()
