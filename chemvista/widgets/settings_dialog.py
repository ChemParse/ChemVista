from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
                             QSpinBox, QDoubleSpinBox, QLabel, QPushButton,
                             QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt
from ..render_settings import RenderSettings


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
