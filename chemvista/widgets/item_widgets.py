from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon
import pathlib


class MoleculeListItem(QWidget):
    visibility_changed = pyqtSignal(bool)
    settings_clicked = pyqtSignal()

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.is_visible = True

        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)

        # Name label
        self.label = QLabel(name)
        layout.addWidget(self.label)

        # Add stretch to push buttons to the right
        layout.addStretch()

        # Visibility toggle button
        self.vis_button = QPushButton()
        self.vis_button.setFixedSize(24, 24)
        self.vis_button.setToolTip("Toggle visibility")  # Add tooltip
        self.vis_button.setIcon(QIcon(":/icons/icons/eye-outline.svg"))
        self.vis_button.clicked.connect(self._toggle_visibility)
        self.vis_button.setFlat(True)  # Make button background transparent
        layout.addWidget(self.vis_button)

        # Settings button
        self.settings_button = QPushButton()
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.setToolTip("Open settings")  # Add tooltip
        self.settings_button.setIcon(QIcon(":/icons/icons/cog-outline.svg"))
        self.settings_button.clicked.connect(self.settings_clicked.emit)
        # Make button background transparent
        self.settings_button.setFlat(True)
        layout.addWidget(self.settings_button)

        self.setLayout(layout)

    def _toggle_visibility(self):
        self.is_visible = not self.is_visible
        icon_name = ":/icons/icons/eye-outline.svg" if self.is_visible else ":/icons/icons/eye-off-outline.svg"
        self.vis_button.setIcon(QIcon(icon_name))
        self.visibility_changed.emit(self.is_visible)
