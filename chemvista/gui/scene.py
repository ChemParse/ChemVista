# Log the visibility change
import logging
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from ..tree_structure import TreeSignals
from .. import SceneManager
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton, QDoubleSpinBox, QLabel, QDialogButtonBox


logger = logging.getLogger("chemvista.scene")


class SceneWidgetSignals(QObject):
    """Signals for ChemVistaApp"""

    # Signals for render events
    view_updated = pyqtSignal()


class SceneWidget(QWidget):
    """
    PyQt widget that wraps the SceneManager and provides a GUI interface
    to the 3D visualization capabilities.

    This widget embeds a PyVista QtInteractor for rendering and handles
    the communication between the GUI and the SceneManager.
    """

    def __init__(self, scene_manager=None, parent=None, scene_widget_signals: Optional[SceneWidgetSignals] = None, tree_signals: Optional[TreeSignals] = None):
        """
        Initialize the SceneWidget with an optional SceneManager

        Args:
            scene_manager: Optional SceneManager instance
            parent: QWidget parent
        """
        super().__init__(parent)

        # Create or use the provided scene manager
        self.scene_manager = scene_manager if scene_manager else SceneManager()

        # Setup the UI
        self.setup_ui()
        # Initialize signals
        self._scene_signals = None
        self._tree_signals = None
        self.scene_signals = scene_widget_signals
        self.tree_signals = tree_signals

    @property
    def scene_signals(self):
        """Get the scene widget signals object"""
        return self._scene_signals

    @scene_signals.setter
    def scene_signals(self, value):
        """Set the scene widget signals object"""
        self._scene_signals = value
        # Connect signals if available
        if self._scene_signals:
            # Connect any scene-specific signals here
            pass

    @property
    def tree_signals(self):
        """Get the tree signals object"""
        return self._tree_signals

    @tree_signals.setter
    def tree_signals(self, value):
        """Set the tree signals object"""
        self._tree_signals = value
        # Connect signals if available
        if self._tree_signals:
            # Connect the render_changed signal if it exists in tree_signals
            if hasattr(self._tree_signals, "render_changed"):
                self._tree_signals.render_changed.connect(
                    self._on_render_changed)

    def setup_ui(self):
        """Create and setup the UI components"""
        # Create the main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create frame for the plotter
        frame = QFrame(self)
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Sunken)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        # Create the plotter - this is the PyVista QtInteractor
        self.plotter = QtInteractor(frame)
        frame_layout.addWidget(self.plotter)

        # Add the frame to the main layout
        layout.addWidget(frame)

        # Set the plotter in the scene manager
        self.scene_manager.plotter = self.plotter

    def refresh_view(self):
        """Update the 3D visualization"""
        try:
            camera = self.plotter.camera
            logger.info("Refreshing view")
            logger.debug(f'Camera position: {camera.position}')
            self.plotter.clear()
            self.scene_manager.render(self.plotter)
            self.plotter.update()
            self.plotter.camera = camera
            self.scene_signals.view_updated.emit()
        except Exception as e:
            import logging

    def reset_camera(self):
        """Reset the camera to show all objects"""
        if self.plotter:
            self.plotter.reset_camera()
            self.plotter.update()

    def set_background_color(self, color):
        """Set the background color of the scene

        Args:
            color: Color specification (RGB tuple, hex string, or name)
        """
        if self.plotter:
            self.plotter.set_background(color)
            self.plotter.update()

    def _on_render_changed(self, uuid):
        """Handle render changes from the scene manager"""
        logger.info(
            f"Render changed for {uuid} - refreshing view")
        # Refresh the view when rendering needs to be updated
        self.refresh_view()

    def take_screenshot(self, filename=None):
        """
        Take a screenshot of the current view

        Args:
            filename: Optional filename to save the screenshot
                     If None, returns the image as a numpy array

        Returns:
            numpy.ndarray if filename is None, otherwise None
        """
        if self.plotter:
            return self.plotter.screenshot(filename=filename)
        return None

    def render_high_quality(self, filename, settings):
        """Perform high-quality off-screen rendering"""
        import pyvista as pv
        
        # Create off-screen plotter for high-quality rendering
        off_screen_plotter = pv.Plotter(
            off_screen=True,
            window_size=(settings['width'], settings['height'])
        )
        
        # Copy camera settings from current plotter
        off_screen_plotter.camera = self.plotter.camera.copy()
        
        # Re-add all objects to the off-screen plotter
        self.scene_manager.render(off_screen_plotter)
        
        # Configure rendering quality
        if settings.get('anti_aliasing', True):
            off_screen_plotter.enable_anti_aliasing()
        
        if settings.get('shadows', False):
            off_screen_plotter.enable_shadows()
        
        # Set background
        off_screen_plotter.background_color = self.plotter.background_color
        
        # Render and save
        off_screen_plotter.show(
            screenshot=filename,
            return_img=False,
            auto_close=False
        )
        
        off_screen_plotter.close()

    def closeEvent(self, event):
        """Handle widget close event"""
        # Clean up plotter resources
        if self.plotter:
            self.plotter.close()
        super().closeEvent(event)

    def add_axes(self, interactive=False):
        """Add orientation axes to the scene

        Args:
            interactive: Whether the axes can be interactively manipulated
        """
        if self.plotter:
            self.plotter.add_axes(interactive=interactive)
            self.plotter.update()

    def show_camera_settings_dialog(self):
        """Show a dialog to adjust camera settings"""

        if not self.plotter or not hasattr(self.plotter, 'camera'):
            return

        # Get current camera settings
        camera = self.plotter.camera
        position = camera.position
        focal_point = camera.focal_point
        view_up = camera.up
        view_angle = camera.view_angle
        clipping_range = camera.clipping_range

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Camera Settings")
        layout = QVBoxLayout(dialog)

        # Create form layout for camera parameters
        form_layout = QFormLayout()

        # Position inputs
        pos_layout = QHBoxLayout()
        pos_x = QDoubleSpinBox()
        pos_y = QDoubleSpinBox()
        pos_z = QDoubleSpinBox()

        for spin_box in [pos_x, pos_y, pos_z]:
            spin_box.setRange(-1000, 1000)
            spin_box.setDecimals(3)
            pos_layout.addWidget(spin_box)

        pos_x.setValue(position[0])
        pos_y.setValue(position[1])
        pos_z.setValue(position[2])
        form_layout.addRow("Position:", pos_layout)

        # Focal point inputs
        focal_layout = QHBoxLayout()
        focal_x = QDoubleSpinBox()
        focal_y = QDoubleSpinBox()
        focal_z = QDoubleSpinBox()

        for spin_box in [focal_x, focal_y, focal_z]:
            spin_box.setRange(-1000, 1000)
            spin_box.setDecimals(3)
            focal_layout.addWidget(spin_box)

        focal_x.setValue(focal_point[0])
        focal_y.setValue(focal_point[1])
        focal_z.setValue(focal_point[2])
        form_layout.addRow("Look at:", focal_layout)

        # View up vector inputs
        up_layout = QHBoxLayout()
        up_x = QDoubleSpinBox()
        up_y = QDoubleSpinBox()
        up_z = QDoubleSpinBox()

        for spin_box in [up_x, up_y, up_z]:
            spin_box.setRange(-1, 1)
            spin_box.setDecimals(3)
            spin_box.setSingleStep(0.1)
            up_layout.addWidget(spin_box)

        up_x.setValue(view_up[0])
        up_y.setValue(view_up[1])
        up_z.setValue(view_up[2])
        form_layout.addRow("View up:", up_layout)

        # View angle input
        view_angle_spin = QDoubleSpinBox()
        view_angle_spin.setRange(1, 180)
        view_angle_spin.setValue(view_angle)
        form_layout.addRow("Field of view:", view_angle_spin)

        # Clipping range inputs
        clip_layout = QHBoxLayout()
        clip_near = QDoubleSpinBox()
        clip_far = QDoubleSpinBox()

        for spin_box in [clip_near, clip_far]:
            spin_box.setRange(0.01, 1000)
            spin_box.setDecimals(3)
            clip_layout.addWidget(spin_box)

        clip_near.setValue(clipping_range[0])
        clip_far.setValue(clipping_range[1])
        form_layout.addRow("Clipping range:", clip_layout)

        layout.addLayout(form_layout)

        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply | QDialogButtonBox.Reset)
        layout.addWidget(button_box)

        # Connect button signals
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        apply_button = button_box.button(QDialogButtonBox.Apply)
        reset_button = button_box.button(QDialogButtonBox.Reset)

        def apply_settings():
            # Update camera with current dialog values
            new_position = [pos_x.value(), pos_y.value(), pos_z.value()]
            new_focal = [focal_x.value(), focal_y.value(), focal_z.value()]
            new_up = [up_x.value(), up_y.value(), up_z.value()]

            camera.position = new_position
            camera.focal_point = new_focal
            camera.up = new_up
            camera.view_angle = view_angle_spin.value()
            camera.clipping_range = (clip_near.value(), clip_far.value())

            self.plotter.update()

        def reset_camera_view():
            # Reset camera to show all objects
            self.reset_camera()
            # Update spin box values with new camera settings
            camera = self.plotter.camera
            pos = camera.position
            focal = camera.focal_point
            up = camera.up

            pos_x.setValue(pos[0])
            pos_y.setValue(pos[1])
            pos_z.setValue(pos[2])

            focal_x.setValue(focal[0])
            focal_y.setValue(focal[1])
            focal_z.setValue(focal[2])

            up_x.setValue(up[0])
            up_y.setValue(up[1])
            up_z.setValue(up[2])

            view_angle_spin.setValue(camera.view_angle)
            clip_near.setValue(camera.clipping_range[0])
            clip_far.setValue(camera.clipping_range[1])

        apply_button.clicked.connect(apply_settings)
        reset_button.clicked.connect(reset_camera_view)

        # Handle dialog result
        if dialog.exec_():
            apply_settings()  # Apply settings when OK is clicked
