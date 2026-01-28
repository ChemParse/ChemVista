from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
                             QSpinBox, QDoubleSpinBox, QLabel, QPushButton,
                             QGroupBox, QFormLayout, QColorDialog, QListWidget,
                             QListWidgetItem, QWidget, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from ...renderer.render_settings import MoleculeRenderSettings, ScalarFieldRenderSettings
import logging

logger = logging.getLogger("chemvista.ui.widgets.settings_dialog")


class ScalarFieldSettingsDialog(QDialog):
    def __init__(self, settings: ScalarFieldRenderSettings, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.setWindowTitle("Scalar Field Settings")
        self.isosurface_list = []  # List to track isosurface value-color pairs
        self.color_previews = []   # List to track color preview widgets
        self.setup_ui()
        self.load_isosurfaces()    # Load existing isosurfaces from settings

    def setup_ui(self):
        layout = QVBoxLayout()

        # Create a group for isosurface settings
        isosurface_group = QGroupBox("Isosurfaces")
        isosurface_layout = QVBoxLayout()

        # Create list for isosurfaces
        self.isosurface_list_widget = QListWidget()
        self.isosurface_list_widget.setMinimumHeight(150)
        isosurface_layout.addWidget(self.isosurface_list_widget)

        # Add buttons for managing isosurfaces
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Isosurface")
        self.remove_button = QPushButton("Remove Selected")
        self.add_button.clicked.connect(self.add_isosurface)
        self.remove_button.clicked.connect(self.remove_isosurface)

        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.remove_button)
        isosurface_layout.addLayout(buttons_layout)

        isosurface_group.setLayout(isosurface_layout)
        layout.addWidget(isosurface_group)

        # General settings group
        general_group = QGroupBox("General Settings")
        form_layout = QFormLayout()

        # Opacity for all isosurfaces
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.0, 1.0)
        self.opacity.setSingleStep(0.1)
        self.opacity.setValue(self.settings.opacity)
        form_layout.addRow("Opacity:", self.opacity)

        # Show grid surface
        self.show_grid_surface = QCheckBox()
        self.show_grid_surface.setChecked(self.settings.show_grid_surface)
        form_layout.addRow("Show Grid Surface:", self.show_grid_surface)

        # Show grid points
        self.show_grid_points = QCheckBox()
        self.show_grid_points.setChecked(self.settings.show_grid_points)
        form_layout.addRow("Show Grid Points:", self.show_grid_points)

        # Smooth surface
        self.smooth_surface = QCheckBox()
        self.smooth_surface.setChecked(self.settings.smooth_surface)
        form_layout.addRow("Smooth Surface:", self.smooth_surface)

        # Grid surface color
        grid_surface_color_layout = QHBoxLayout()
        self.grid_surface_color_preview = QLabel()
        self.grid_surface_color_preview.setFixedSize(24, 24)
        self.grid_surface_color_preview.setStyleSheet(
            f"background-color: {self.settings.grid_surface_color};")

        self.grid_surface_color_button = QPushButton("Choose Color")
        self.grid_surface_color_button.clicked.connect(
            lambda: self._choose_grid_color("surface"))

        grid_surface_color_layout.addWidget(self.grid_surface_color_preview)
        grid_surface_color_layout.addWidget(self.grid_surface_color_button)
        grid_surface_color_layout.addStretch()
        form_layout.addRow("Grid Surface Color:", grid_surface_color_layout)

        # Grid points color
        grid_points_color_layout = QHBoxLayout()
        self.grid_points_color_preview = QLabel()
        self.grid_points_color_preview.setFixedSize(24, 24)
        self.grid_points_color_preview.setStyleSheet(
            f"background-color: {self.settings.grid_points_color};")

        self.grid_points_color_button = QPushButton("Choose Color")
        self.grid_points_color_button.clicked.connect(
            lambda: self._choose_grid_color("points"))

        grid_points_color_layout.addWidget(self.grid_points_color_preview)
        grid_points_color_layout.addWidget(self.grid_points_color_button)
        grid_points_color_layout.addStretch()
        form_layout.addRow("Grid Points Color:", grid_points_color_layout)

        # Grid points size
        self.grid_points_size = QSpinBox()
        self.grid_points_size.setRange(1, 20)
        self.grid_points_size.setValue(self.settings.grid_points_size)
        form_layout.addRow("Grid Points Size:", self.grid_points_size)

        # Show filtered points
        self.show_filtered_points = QCheckBox()
        self.show_filtered_points.setChecked(
            self.settings.show_filtered_points)
        form_layout.addRow("Show Filtered Points:", self.show_filtered_points)

        # Point value range
        point_range_layout = QHBoxLayout()
        self.point_value_min = QDoubleSpinBox()
        self.point_value_min.setRange(-10.0, 10.0)
        self.point_value_min.setSingleStep(0.01)
        self.point_value_min.setValue(self.settings.point_value_range[0])

        self.point_value_max = QDoubleSpinBox()
        self.point_value_max.setRange(-10.0, 10.0)
        self.point_value_max.setSingleStep(0.01)
        self.point_value_max.setValue(self.settings.point_value_range[1])

        point_range_layout.addWidget(QLabel("Min:"))
        point_range_layout.addWidget(self.point_value_min)
        point_range_layout.addWidget(QLabel("Max:"))
        point_range_layout.addWidget(self.point_value_max)

        form_layout.addRow("Point Value Range:", point_range_layout)

        general_group.setLayout(form_layout)
        layout.addWidget(general_group)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.setObjectName("Save")  # Set object name for testing
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("Cancel")  # Set object name for testing
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_isosurfaces(self):
        """Load existing isosurfaces from settings"""
        isosurface_values = self.settings.isosurface_values
        colors = self.settings.colors

        # Ensure we have colors for all isosurfaces
        if len(colors) < len(isosurface_values):
            colors = list(colors) + [colors[-1]] * \
                (len(isosurface_values) - len(colors))

        # Add each isosurface to the list
        for i, (value, color) in enumerate(zip(isosurface_values, colors)):
            self.add_isosurface_item(value, color)

    def add_isosurface_item(self, value=0.1, color='blue'):
        """Add an isosurface item to the list widget"""
        # Create a widget to hold the isosurface controls
        item_widget = QWidget()
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(5, 2, 5, 2)

        # Create a spin box for the isosurface value
        value_spin = QDoubleSpinBox()
        value_spin.setRange(-10.0, 10.0)
        value_spin.setSingleStep(0.01)
        value_spin.setValue(value)

        # Create color preview and button
        color_preview = QLabel()
        color_preview.setFixedSize(24, 24)
        color_preview.setStyleSheet(f"background-color: {color};")

        color_button = QPushButton("Color")
        color_button.clicked.connect(
            lambda: self.choose_isosurface_color(color_preview))

        # Add to layout
        layout.addWidget(QLabel("Value:"))
        layout.addWidget(value_spin)
        layout.addWidget(color_preview)
        layout.addWidget(color_button)

        # Create a list item and set its widget
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())

        self.isosurface_list_widget.addItem(item)
        self.isosurface_list_widget.setItemWidget(item, item_widget)

        # Store reference to the color preview
        self.color_previews.append(color_preview)

    def add_isosurface(self):
        """Add a new isosurface with default values"""
        self.add_isosurface_item(0.1, 'blue')

    def remove_isosurface(self):
        """Remove the selected isosurface"""
        selected_items = self.isosurface_list_widget.selectedItems()

        if not selected_items:
            QMessageBox.information(
                self, "No Selection", "Please select an isosurface to remove.")
            return

        for item in selected_items:
            row = self.isosurface_list_widget.row(item)
            self.isosurface_list_widget.takeItem(row)
            # Remove the corresponding color preview
            if row < len(self.color_previews):
                del self.color_previews[row]

    def choose_isosurface_color(self, color_preview):
        """Open color dialog for an isosurface"""
        current_color = QColor(
            color_preview.styleSheet().split(":")[1].strip(';'))
        color = QColorDialog.getColor(
            initial=current_color,
            parent=self,
            title="Choose Isosurface Color"
        )

        if color.isValid():
            color_preview.setStyleSheet(f"background-color: {color.name()};")

    def _choose_grid_color(self, grid_type):
        """Choose color for grid surface or points"""
        if grid_type == "surface":
            current_color = QColor(self.settings.grid_surface_color)
            preview = self.grid_surface_color_preview
        else:  # points
            current_color = QColor(self.settings.grid_points_color)
            preview = self.grid_points_color_preview

        color = QColorDialog.getColor(
            initial=current_color,
            parent=self,
            title=f"Choose Grid {grid_type.capitalize()} Color"
        )

        if color.isValid():
            preview.setStyleSheet(f"background-color: {color.name()};")
            if grid_type == "surface":
                self.settings.grid_surface_color = color.name()
            else:
                self.settings.grid_points_color = color.name()

    def collect_isosurface_settings(self):
        """Collect all isosurface values and colors from the list widget"""
        isosurface_values = []
        colors = []

        for i in range(self.isosurface_list_widget.count()):
            item = self.isosurface_list_widget.item(i)
            widget = self.isosurface_list_widget.itemWidget(item)

            # Access the isosurface value from the spin box (3rd widget in layout)
            value_spin = widget.layout().itemAt(1).widget()
            isosurface_values.append(value_spin.value())

            # Access the color from the preview label's style (5th widget in layout)
            color_preview = widget.layout().itemAt(2).widget()
            color_style = color_preview.styleSheet()
            color = color_style.split(":")[1].strip(';')
            colors.append(color)

        return tuple(isosurface_values), tuple(colors)

    def get_settings(self) -> ScalarFieldRenderSettings:
        if self.result() == QDialog.Accepted:
            # Collect isosurface values and colors
            isosurface_values, colors = self.collect_isosurface_settings()

            # Ensure we have at least one isosurface
            if not isosurface_values:
                isosurface_values = (0.1,)
                colors = ('blue',)

            self.settings.isosurface_values = isosurface_values
            self.settings.colors = colors

            # Set other settings
            self.settings.opacity = self.opacity.value()
            self.settings.show_grid_surface = self.show_grid_surface.isChecked()
            self.settings.show_grid_points = self.show_grid_points.isChecked()
            self.settings.smooth_surface = self.smooth_surface.isChecked()
            self.settings.grid_points_size = self.grid_points_size.value()
            self.settings.show_filtered_points = self.show_filtered_points.isChecked()

            # Set point value range
            min_val = self.point_value_min.value()
            max_val = self.point_value_max.value()
            self.settings.point_value_range = (min_val, max_val)

        return self.settings


class RenderSettingsDialog(QDialog):
    def __init__(self, settings: MoleculeRenderSettings, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.setWindowTitle("Render Settings")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # General settings group
        general_group = QGroupBox("General Settings")
        form_layout = QFormLayout()

        # Show hydrogens
        self.show_hydrogens = QCheckBox()
        self.show_hydrogens.setChecked(self.settings.show_hydrogens)
        form_layout.addRow("Show Hydrogens:", self.show_hydrogens)

        # Show numbers
        self.show_numbers = QCheckBox()
        self.show_numbers.setChecked(self.settings.show_numbers)
        form_layout.addRow("Show Atom Numbers:", self.show_numbers)

        # Alpha (Opacity)
        self.alpha = QDoubleSpinBox()
        self.alpha.setRange(0.0, 1.0)
        self.alpha.setSingleStep(0.1)
        self.alpha.setValue(self.settings.alpha)
        form_layout.addRow("Opacity:", self.alpha)

        # Resolution
        self.resolution = QSpinBox()
        self.resolution.setRange(4, 32)
        self.resolution.setValue(self.settings.resolution)
        form_layout.addRow("Resolution:", self.resolution)

        general_group.setLayout(form_layout)
        layout.addWidget(general_group)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.setObjectName("Save")  # Set object name for testing
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("Cancel")  # Set object name for testing
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_settings(self) -> MoleculeRenderSettings:
        if self.result() == QDialog.Accepted:
            self.settings.show_hydrogens = self.show_hydrogens.isChecked()
            self.settings.show_numbers = self.show_numbers.isChecked()
            self.settings.alpha = self.alpha.value()
            self.settings.resolution = self.resolution.value()
        return self.settings
