# Log the visibility change
import logging
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from ..tree_structure import TreeSignals
from .. import SceneManager


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
            logging.getLogger("chemvista.gui").error(
                f"Error refreshing view: {e}")

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
