from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
                             QSpinBox, QDoubleSpinBox, QLabel, QPushButton,
                             QGroupBox, QFormLayout, QColorDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from ..render_settings import RenderSettings, ScalarFieldRenderSettings


class ScalarFieldSettingsDialog(QDialog):
    def __init__(self, settings: ScalarFieldRenderSettings, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.setWindowTitle("Scalar Field Settings")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # General settings group
        general_group = QGroupBox("Visualization Settings")
        form_layout = QFormLayout()

        # Isosurface value
        self.isosurface_value = QDoubleSpinBox()
        self.isosurface_value.setRange(-10.0, 10.0)
        self.isosurface_value.setSingleStep(0.01)
        self.isosurface_value.setValue(self.settings.isosurface_value)
        form_layout.addRow("Isosurface Value:", self.isosurface_value)

        # Color selection button with preview label
        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(24, 24)
        self.color_preview.setStyleSheet(
            f"background-color: {self.settings.color};")

        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self._choose_color)

        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        form_layout.addRow("Color:", color_layout)

        # Opacity
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

        general_group.setLayout(form_layout)
        layout.addWidget(general_group)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _choose_color(self):
        # Convert string color name or hex to QColor
        current_color = QColor(self.settings.color)
        color = QColorDialog.getColor(
            initial=current_color,
            parent=self,
            title="Choose Scalar Field Color"
        )

        if color.isValid():
            # Store color as string (either name or hex)
            self.settings.color = color.name()
            self.color_preview.setStyleSheet(
                f"background-color: {color.name()};")

    def get_settings(self) -> ScalarFieldRenderSettings:
        if self.result() == QDialog.Accepted:
            self.settings.isosurface_value = self.isosurface_value.value()
            self.settings.opacity = self.opacity.value()
            self.settings.show_grid_surface = self.show_grid_surface.isChecked()
            self.settings.show_grid_points = self.show_grid_points.isChecked()
        return self.settings


class RenderSettingsDialog(QDialog):
    def __init__(self, settings: RenderSettings, parent=None):
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
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_settings(self) -> RenderSettings:
        if self.result() == QDialog.Accepted:
            self.settings.show_hydrogens = self.show_hydrogens.isChecked()
            self.settings.show_numbers = self.show_numbers.isChecked()
            self.settings.alpha = self.alpha.value()
            self.settings.resolution = self.resolution.value()
        return self.settings
