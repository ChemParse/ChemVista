"""
Palette settings dialog for customizing atom colors and radii.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QColorDialog, QListWidget,
    QListWidgetItem, QWidget, QDoubleSpinBox, QComboBox,
    QFileDialog, QScrollArea, QFrame, QMessageBox, QLineEdit,
    QTabWidget, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from typing import Dict, Any, Optional
from copy import deepcopy
import logging

from ...renderer.palettes import (
    load_palette, load_default_settings, get_available_palettes,
    save_palette, BUILTIN_PALETTES
)

logger = logging.getLogger("chemvista.gui.widgets.palette_dialog")


class ElementColorWidget(QWidget):
    """Widget for editing a single element's color and radius."""

    def __init__(self, symbol: str, color: list, radius: float, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self._color = color.copy() if isinstance(color, list) else list(color)
        self._radius = radius

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # Element symbol label
        self.symbol_label = QLabel(f"{symbol}:")
        self.symbol_label.setMinimumWidth(60)
        self.symbol_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.symbol_label)

        # Color preview
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(24, 24)
        self._update_color_preview()
        layout.addWidget(self.color_preview)

        # Color button
        self.color_button = QPushButton("Color")
        self.color_button.setFixedWidth(60)
        self.color_button.clicked.connect(self._choose_color)
        layout.addWidget(self.color_button)

        # Radius spinbox
        layout.addWidget(QLabel("r:"))
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.01, 3.0)
        self.radius_spin.setSingleStep(0.01)
        self.radius_spin.setDecimals(3)
        self.radius_spin.setValue(radius)
        self.radius_spin.setMinimumWidth(90)
        self.radius_spin.valueChanged.connect(self._on_radius_changed)
        layout.addWidget(self.radius_spin)

        layout.addStretch()

    def _update_color_preview(self):
        """Update the color preview label."""
        r, g, b = self._color[:3]
        self.color_preview.setStyleSheet(
            f"background-color: rgb({r}, {g}, {b}); border: 1px solid #888;"
        )

    def _choose_color(self):
        """Open color dialog to choose element color."""
        r, g, b = self._color[:3]
        current = QColor(r, g, b)
        color = QColorDialog.getColor(
            initial=current,
            parent=self,
            title=f"Choose Color for {self.symbol}"
        )
        if color.isValid():
            self._color = [color.red(), color.green(), color.blue()]
            self._update_color_preview()

    def _on_radius_changed(self, value):
        """Handle radius change."""
        self._radius = value

    def get_settings(self) -> Dict[str, Any]:
        """Return current settings for this element."""
        return {
            "color": self._color.copy(),
            "radius": self.radius_spin.value()
        }

    def set_settings(self, color: list, radius: float):
        """Set settings for this element."""
        self._color = color.copy() if isinstance(color, list) else list(color)
        self._radius = radius
        self._update_color_preview()
        self.radius_spin.setValue(radius)


class BondSettingsWidget(QWidget):
    """Widget for editing bond rendering settings."""

    DEFAULT_BOND_SETTINGS = {
        "color": [211, 211, 211],
        "single": {"radius": 0.05},
        "double": {"radius": 0.025, "offset": 0.03},
        "triple": {"radius": 0.02, "offset": 0.05}
    }

    def __init__(self, bond_settings: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self._settings = bond_settings.copy() if bond_settings else self.DEFAULT_BOND_SETTINGS.copy()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Bond color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Bond Color:"))

        self.color_preview = QLabel()
        self.color_preview.setFixedSize(24, 24)
        self._update_color_preview()
        color_layout.addWidget(self.color_preview)

        self.color_button = QPushButton("Choose...")
        self.color_button.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        layout.addSpacing(10)

        # Single bond settings
        single_group = QGroupBox("Single Bond")
        single_layout = QFormLayout()
        self.single_radius_spin = QDoubleSpinBox()
        self.single_radius_spin.setRange(0.001, 0.5)
        self.single_radius_spin.setSingleStep(0.005)
        self.single_radius_spin.setDecimals(3)
        self.single_radius_spin.setValue(self._settings.get('single', {}).get('radius', 0.05))
        single_layout.addRow("Radius:", self.single_radius_spin)
        single_group.setLayout(single_layout)
        layout.addWidget(single_group)

        # Double bond settings
        double_group = QGroupBox("Double Bond")
        double_layout = QFormLayout()
        self.double_radius_spin = QDoubleSpinBox()
        self.double_radius_spin.setRange(0.001, 0.5)
        self.double_radius_spin.setSingleStep(0.005)
        self.double_radius_spin.setDecimals(3)
        self.double_radius_spin.setValue(self._settings.get('double', {}).get('radius', 0.025))
        double_layout.addRow("Radius:", self.double_radius_spin)

        self.double_offset_spin = QDoubleSpinBox()
        self.double_offset_spin.setRange(0.001, 0.2)
        self.double_offset_spin.setSingleStep(0.005)
        self.double_offset_spin.setDecimals(3)
        self.double_offset_spin.setValue(self._settings.get('double', {}).get('offset', 0.03))
        double_layout.addRow("Offset:", self.double_offset_spin)
        double_group.setLayout(double_layout)
        layout.addWidget(double_group)

        # Triple bond settings
        triple_group = QGroupBox("Triple Bond")
        triple_layout = QFormLayout()
        self.triple_radius_spin = QDoubleSpinBox()
        self.triple_radius_spin.setRange(0.001, 0.5)
        self.triple_radius_spin.setSingleStep(0.005)
        self.triple_radius_spin.setDecimals(3)
        self.triple_radius_spin.setValue(self._settings.get('triple', {}).get('radius', 0.02))
        triple_layout.addRow("Radius:", self.triple_radius_spin)

        self.triple_offset_spin = QDoubleSpinBox()
        self.triple_offset_spin.setRange(0.001, 0.2)
        self.triple_offset_spin.setSingleStep(0.005)
        self.triple_offset_spin.setDecimals(3)
        self.triple_offset_spin.setValue(self._settings.get('triple', {}).get('offset', 0.05))
        triple_layout.addRow("Offset:", self.triple_offset_spin)
        triple_group.setLayout(triple_layout)
        layout.addWidget(triple_group)

        layout.addStretch()

    def _update_color_preview(self):
        """Update the color preview label."""
        color = self._settings.get('color', [211, 211, 211])
        r, g, b = color[:3]
        self.color_preview.setStyleSheet(
            f"background-color: rgb({r}, {g}, {b}); border: 1px solid #888;"
        )

    def _choose_color(self):
        """Open color dialog to choose bond color."""
        color = self._settings.get('color', [211, 211, 211])
        r, g, b = color[:3]
        current = QColor(r, g, b)
        new_color = QColorDialog.getColor(
            initial=current,
            parent=self,
            title="Choose Bond Color"
        )
        if new_color.isValid():
            self._settings['color'] = [new_color.red(), new_color.green(), new_color.blue()]
            self._update_color_preview()

    def get_settings(self) -> Dict[str, Any]:
        """Return current bond settings."""
        return {
            "color": self._settings.get('color', [211, 211, 211]),
            "single": {"radius": self.single_radius_spin.value()},
            "double": {
                "radius": self.double_radius_spin.value(),
                "offset": self.double_offset_spin.value()
            },
            "triple": {
                "radius": self.triple_radius_spin.value(),
                "offset": self.triple_offset_spin.value()
            }
        }

    def set_settings(self, settings: Dict[str, Any]):
        """Set bond settings."""
        self._settings = settings.copy() if settings else self.DEFAULT_BOND_SETTINGS.copy()
        self._update_color_preview()
        self.single_radius_spin.setValue(self._settings.get('single', {}).get('radius', 0.05))
        self.double_radius_spin.setValue(self._settings.get('double', {}).get('radius', 0.025))
        self.double_offset_spin.setValue(self._settings.get('double', {}).get('offset', 0.03))
        self.triple_radius_spin.setValue(self._settings.get('triple', {}).get('radius', 0.02))
        self.triple_offset_spin.setValue(self._settings.get('triple', {}).get('offset', 0.05))


class PaletteSettingsDialog(QDialog):
    """Dialog for customizing atom color palette and radii."""

    # Default bond settings
    DEFAULT_BOND_SETTINGS = {
        "color": [211, 211, 211],
        "single": {"radius": 0.05},
        "double": {"radius": 0.025, "offset": 0.03},
        "triple": {"radius": 0.02, "offset": 0.05}
    }

    # Common elements shown at the top
    COMMON_ELEMENTS = ['H', 'C', 'N', 'O', 'F', 'P', 'S', 'Cl', 'Br', 'I']

    # Periodic table order for all elements (used to maintain consistent ordering)
    PERIODIC_TABLE_ORDER = [
        'Unknown',  # Special case, keep first
        'H', 'He',
        'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
        'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
        'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
        'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr',
        'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd',
        'In', 'Sn', 'Sb', 'Te', 'I', 'Xe',
        'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy',
        'Ho', 'Er', 'Tm', 'Yb', 'Lu',
        'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
        'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
        'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf',
        'Es', 'Fm', 'Md', 'No', 'Lr',
        'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt',
    ]

    def __init__(self, current_settings: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Palette Settings")
        self.setMinimumSize(500, 600)
        self.resize(550, 700)

        # Store a deep copy of current settings
        self._settings = deepcopy(current_settings)
        self._original_settings = deepcopy(current_settings)

        # Extract bond settings (they're stored separately)
        self._bond_settings = self._settings.pop('bonds', self.DEFAULT_BOND_SETTINGS.copy())
        self._original_bond_settings = deepcopy(self._bond_settings)

        # Element widgets dict
        self._element_widgets: Dict[str, ElementColorWidget] = {}

        # Bond settings widget
        self._bond_widget: Optional[BondSettingsWidget] = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Palette selection group
        palette_group = QGroupBox("Palette")
        palette_layout = QHBoxLayout()

        palette_layout.addWidget(QLabel("Load preset:"))
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(get_available_palettes())
        self.palette_combo.currentTextChanged.connect(self._on_palette_selected)
        palette_layout.addWidget(self.palette_combo)

        palette_layout.addStretch()

        self.load_file_btn = QPushButton("Load from File...")
        self.load_file_btn.clicked.connect(self._load_from_file)
        palette_layout.addWidget(self.load_file_btn)

        self.save_file_btn = QPushButton("Save to File...")
        self.save_file_btn.clicked.connect(self._save_to_file)
        palette_layout.addWidget(self.save_file_btn)

        palette_group.setLayout(palette_layout)
        layout.addWidget(palette_group)

        # Global radius scale
        scale_group = QGroupBox("Global Radius Scale")
        scale_layout = QHBoxLayout()

        scale_layout.addWidget(QLabel("Scale factor:"))
        self.radius_scale_spin = QDoubleSpinBox()
        self.radius_scale_spin.setRange(0.1, 5.0)
        self.radius_scale_spin.setSingleStep(0.1)
        self.radius_scale_spin.setValue(1.0)
        self.radius_scale_spin.setDecimals(2)
        scale_layout.addWidget(self.radius_scale_spin)

        self.apply_scale_btn = QPushButton("Apply Scale")
        self.apply_scale_btn.clicked.connect(self._apply_radius_scale)
        scale_layout.addWidget(self.apply_scale_btn)

        scale_layout.addStretch()

        scale_group.setLayout(scale_layout)
        layout.addWidget(scale_group)

        # Element settings with tabs
        elements_group = QGroupBox("Element Colors and Radii")
        elements_layout = QVBoxLayout()

        self.tab_widget = QTabWidget()

        # Common elements tab
        common_tab = QWidget()
        common_layout = QVBoxLayout(common_tab)
        self.common_scroll = QScrollArea()
        self.common_scroll.setWidgetResizable(True)
        self.common_scroll.setFrameShape(QFrame.NoFrame)
        common_content = QWidget()
        self.common_elements_layout = QVBoxLayout(common_content)
        self.common_scroll.setWidget(common_content)
        common_layout.addWidget(self.common_scroll)
        self.tab_widget.addTab(common_tab, "Common")

        # All elements tab
        all_tab = QWidget()
        all_layout = QVBoxLayout(all_tab)
        self.all_scroll = QScrollArea()
        self.all_scroll.setWidgetResizable(True)
        self.all_scroll.setFrameShape(QFrame.NoFrame)
        all_content = QWidget()
        self.all_elements_layout = QVBoxLayout(all_content)
        self.all_scroll.setWidget(all_content)
        all_layout.addWidget(self.all_scroll)
        self.tab_widget.addTab(all_tab, "All Elements")

        # Bonds tab
        bonds_tab = QWidget()
        bonds_layout = QVBoxLayout(bonds_tab)
        self._bond_widget = BondSettingsWidget(self._bond_settings, parent=self)
        bonds_layout.addWidget(self._bond_widget)
        self.tab_widget.addTab(bonds_tab, "Bonds")

        elements_layout.addWidget(self.tab_widget)
        elements_group.setLayout(elements_layout)
        layout.addWidget(elements_group, stretch=1)

        # Populate element widgets
        self._populate_elements()

        # Buttons
        button_layout = QHBoxLayout()

        self.reset_btn = QPushButton("Reset to Original")
        self.reset_btn.clicked.connect(self._reset_to_original)
        button_layout.addWidget(self.reset_btn)

        button_layout.addStretch()

        save_button = QPushButton("Apply")
        save_button.setObjectName("Apply")
        save_button.clicked.connect(self.accept)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def _get_element_order(self, symbols):
        """
        Sort element symbols in periodic table order.

        Known elements are ordered by their position in the periodic table.
        Unknown elements (not in PERIODIC_TABLE_ORDER) are appended at the end
        in alphabetical order.
        Non-element keys (like 'bonds') are filtered out.
        """
        # Create a lookup for periodic table position
        order_lookup = {sym: i for i, sym in enumerate(self.PERIODIC_TABLE_ORDER)}

        # Separate known and unknown elements (filter out non-element keys)
        known = []
        unknown = []
        for sym in symbols:
            # Skip non-element keys
            if sym == 'bonds':
                continue
            if sym in order_lookup:
                known.append(sym)
            else:
                unknown.append(sym)

        # Sort known by periodic table order, unknown alphabetically
        known.sort(key=lambda s: order_lookup[s])
        unknown.sort()

        return known + unknown

    def _populate_elements(self):
        """Populate element widgets from current settings."""
        # Clear existing widgets
        for widget in self._element_widgets.values():
            widget.deleteLater()
        self._element_widgets.clear()

        # Clear layouts
        while self.common_elements_layout.count():
            item = self.common_elements_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        while self.all_elements_layout.count():
            item = self.all_elements_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get elements in periodic table order
        all_symbols = self._get_element_order(self._settings.keys())

        # Create widgets for common elements
        for symbol in self.COMMON_ELEMENTS:
            if symbol in self._settings:
                elem_settings = self._settings[symbol]
                widget = ElementColorWidget(
                    symbol,
                    elem_settings['color'],
                    elem_settings['radius'],
                    parent=self
                )
                self._element_widgets[symbol] = widget
                self.common_elements_layout.addWidget(widget)

        self.common_elements_layout.addStretch()

        # Create widgets for all elements in periodic table order
        for symbol in all_symbols:
            elem_settings = self._settings[symbol]
            widget = ElementColorWidget(
                symbol,
                elem_settings['color'],
                elem_settings['radius'],
                parent=self
            )
            self._element_widgets[f"all_{symbol}"] = widget
            self.all_elements_layout.addWidget(widget)

        self.all_elements_layout.addStretch()

    def _on_palette_selected(self, palette_name: str):
        """Handle palette selection from combo box."""
        try:
            loaded = load_palette(palette_name)
            # Extract bond settings
            self._bond_settings = loaded.pop('bonds', self.DEFAULT_BOND_SETTINGS.copy())
            self._settings = loaded
            self._populate_elements()
            if self._bond_widget:
                self._bond_widget.set_settings(self._bond_settings)
            logger.info(f"Loaded palette: {palette_name}")
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"Failed to load palette '{palette_name}': {e}"
            )

    def _load_from_file(self):
        """Load palette from a JSON file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load Palette",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_name:
            try:
                loaded = load_palette(file_name)
                # Extract bond settings
                self._bond_settings = loaded.pop('bonds', self.DEFAULT_BOND_SETTINGS.copy())
                self._settings = loaded
                self._populate_elements()
                if self._bond_widget:
                    self._bond_widget.set_settings(self._bond_settings)
                logger.info(f"Loaded palette from: {file_name}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load palette: {e}"
                )

    def _save_to_file(self):
        """Save current palette to a JSON file."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Palette",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_name:
            if not file_name.endswith('.json'):
                file_name += '.json'

            try:
                settings = self._collect_settings()
                save_palette(settings, file_name)
                QMessageBox.information(
                    self, "Saved", f"Palette saved to {file_name}"
                )
                logger.info(f"Saved palette to: {file_name}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save palette: {e}"
                )

    def _apply_radius_scale(self):
        """Apply global radius scale to all elements."""
        scale = self.radius_scale_spin.value()

        # Update all widgets
        for key, widget in self._element_widgets.items():
            current_radius = widget.radius_spin.value()
            new_radius = current_radius * scale
            widget.radius_spin.setValue(new_radius)

        # Reset scale to 1.0 after applying
        self.radius_scale_spin.setValue(1.0)

        logger.info(f"Applied radius scale: {scale}")

    def _reset_to_original(self):
        """Reset to original settings."""
        self._settings = deepcopy(self._original_settings)
        # Remove bonds from settings if present (we track them separately)
        self._settings.pop('bonds', None)
        self._bond_settings = deepcopy(self._original_bond_settings)
        self._populate_elements()
        if self._bond_widget:
            self._bond_widget.set_settings(self._bond_settings)
        logger.info("Reset to original settings")

    def _collect_settings(self) -> Dict[str, Any]:
        """Collect current settings from all widgets."""
        result = {}

        # Collect from all elements tab (has complete set)
        for key, widget in self._element_widgets.items():
            if key.startswith("all_"):
                symbol = key[4:]  # Remove "all_" prefix
            else:
                symbol = widget.symbol

            # Only add once (prefer all_ widgets as they're authoritative)
            if symbol not in result or key.startswith("all_"):
                result[symbol] = widget.get_settings()

        # Add bond settings
        if self._bond_widget:
            result['bonds'] = self._bond_widget.get_settings()
        else:
            result['bonds'] = self._bond_settings

        return result

    def get_settings(self) -> Dict[str, Any]:
        """Return the current palette settings."""
        if self.result() == QDialog.Accepted:
            return self._collect_settings()
        return self._original_settings
