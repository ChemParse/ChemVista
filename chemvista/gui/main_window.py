import pathlib
from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (QAction, QDialog, QDockWidget, QFileDialog,
                             QMainWindow, QMessageBox, QToolBar, QColorDialog,
                             QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QCheckBox,
                             QPushButton, QComboBox, QDoubleSpinBox)

from ..scene_manager import SceneManager
from ..scene_objects import TrajectoryObject
from ..tree_structure import TreeSignals
from .scene import SceneWidget, SceneWidgetSignals
from .widgets.object_tree import ObjectTreeWidget, TreeWidgetSignals
from .widgets.trajectory_controls import TrajectoryControlsWidget
import logging
from .widgets.settings_dialog import (RenderSettingsDialog,
                                      ScalarFieldSettingsDialog)
from .widgets.palette_dialog import PaletteSettingsDialog

# Set up logger
logger = logging.getLogger("chemvista.gui.main_window")


class ChemVistaApp(QMainWindow):
    def __init__(self, scene_manager: SceneManager | None = None, init_files: Optional[Dict[str, List[pathlib.Path]]] = None):
        super().__init__()
        self.setWindowTitle("ChemVista")
        self.resize(1200, 800)
        self.scene_widget_signals = SceneWidgetSignals()
        self.tree_signals = TreeSignals()
        self.tree_widget_signals = TreeWidgetSignals()
        # Use provided scene manager or create new one
        if scene_manager is None:
            logger.info("Creating new scene manager")
            self.scene_manager = SceneManager(tree_signals=self.tree_signals)
        else:
            logger.info("Using provided scene manager")
            self.scene_manager = scene_manager
            # Set tree signals for the provided scene manager
            self.scene_manager.tree_signals = self.tree_signals

        # Create menu bar
        self.create_menu_bar()

        # Create central SceneWidget first
        self.create_scene_widget()

        # Create left panel for object list and connect signals to scene widget
        self.create_object_list()

        # Create trajectory controls dock
        self.create_trajectory_controls()

        # Load initial files if provided
        if init_files:
            self.load_initial_files(init_files)

        # Make sure tree is expanded by default
        self.object_list_widget.expandAll()

        # Show the window and raise it to front
        self.show()
        self.raise_()
        self.activateWindow()

        self.refresh_view()

    def load_initial_files(self, init_files: Dict[str, List[pathlib.Path]]):
        """Load files specified in initialization dictionary"""
        try:
            # Load XYZ files
            for xyz_file in init_files.get('xyz_files', []):
                self.scene_manager.load_xyz(xyz_file)

            # Load cube files as molecules with fields
            for cube_file in init_files.get('cube_mol_files', []):
                self.scene_manager.load_molecule_from_cube(cube_file)

            # Load cube files as scalar fields
            for cube_file in init_files.get('cube_field_files', []):
                self.scene_manager.load_scalar_field_from_cube(cube_file)

            # Refresh view after loading all files
            if any(len(files) > 0 for files in init_files.values()):
                self.refresh_view()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to load initial files: {str(e)}")

    def create_menu_bar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)

        save_action = QAction("Screenshot", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.on_screenshot)

        # Add render action
        render_action = QAction("High Quality Render", self)
        render_action.setShortcut("Ctrl+Shift+S")
        render_action.triggered.connect(self.on_render)

        # Add export actions
        file_menu.addSeparator()
        export_glb_action = QAction("Export to GLB (Static)", self)
        export_glb_action.setShortcut("Ctrl+E")
        export_glb_action.triggered.connect(self.on_export_glb)

        export_animated_action = QAction("Export to GLB (Animated)", self)
        export_animated_action.setShortcut("Ctrl+Shift+E")
        export_animated_action.triggered.connect(self.on_export_animated_glb)

        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(render_action)
        file_menu.addSeparator()
        file_menu.addAction(export_glb_action)
        file_menu.addAction(export_animated_action)

        # View menu
        view_menu = menubar.addMenu("View")
        refresh_action = QAction("Refresh View", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_view)
        view_menu.addAction(refresh_action)

        # Add reset camera action
        reset_camera_action = QAction("Reset Camera", self)
        reset_camera_action.setShortcut("Ctrl+R")
        reset_camera_action.triggered.connect(self.reset_camera)
        view_menu.addAction(reset_camera_action)

        # Add camera settings action
        camera_settings_action = QAction("Camera Settings", self)
        camera_settings_action.setShortcut("Ctrl+K")
        camera_settings_action.triggered.connect(self.on_camera_settings)
        view_menu.addAction(camera_settings_action)

        # Add background color action
        background_color_action = QAction("Background Color", self)
        background_color_action.setShortcut("Ctrl+B")
        background_color_action.triggered.connect(self.on_background_color)
        view_menu.addAction(background_color_action)

        view_menu.addSeparator()

        # Add palette settings action
        palette_action = QAction("Atom Palette Settings...", self)
        palette_action.setShortcut("Ctrl+P")
        palette_action.triggered.connect(self.on_palette_settings)
        view_menu.addAction(palette_action)

    def create_object_list(self):
        dock = QDockWidget("Objects", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.object_list_widget = ObjectTreeWidget(
            self.scene_manager, self, tree_widget_signals=self.tree_widget_signals, tree_signals=self.tree_signals)

        dock.setWidget(self.object_list_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        # Connect selection signal to update trajectory controls
        self.tree_widget_signals.selection_changed.connect(
            self._on_tree_selection_changed)

    def create_trajectory_controls(self):
        """Create the trajectory animation controls dock widget"""
        self.trajectory_dock = QDockWidget("Trajectory Controls", self)
        self.trajectory_dock.setAllowedAreas(
            Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)

        self.trajectory_controls = TrajectoryControlsWidget(self)
        self.trajectory_controls.frame_changed.connect(
            self._on_trajectory_frame_changed)
        self.trajectory_controls.time_changed.connect(
            self._on_trajectory_time_changed)

        self.trajectory_dock.setWidget(self.trajectory_controls)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.trajectory_dock)

        # Initially hidden until a trajectory is selected
        self.trajectory_dock.hide()

        # Store current animation time for interpolated rendering
        self._animation_time = None
        self._animating_trajectory_uuid = None

    def _on_tree_selection_changed(self, uuid: str):
        """Handle selection changes in the object tree"""
        if uuid:
            obj = self.scene_manager.get_object_by_uuid(uuid)
            if isinstance(obj, TrajectoryObject):
                self.trajectory_controls.set_trajectory(obj)
                self.trajectory_dock.show()
                logger.debug(f"Trajectory controls enabled for '{obj.name}'")
                return

        # Not a trajectory, hide controls
        self.trajectory_controls.clear()
        self.trajectory_dock.hide()

    def _on_trajectory_frame_changed(self, uuid: str):
        """Handle discrete frame change from trajectory controls"""
        self._animation_time = None
        self._animating_trajectory_uuid = None
        self.refresh_view()

    def _on_trajectory_time_changed(self, uuid: str, time_value: float):
        """Handle smooth time change from trajectory controls for interpolated rendering"""
        self._animation_time = time_value
        self._animating_trajectory_uuid = uuid
        self.refresh_interpolated_view()

    def create_scene_widget(self):
        """Create the central SceneWidget"""
        self.scene_widget = SceneWidget(
            self.scene_manager, self, scene_widget_signals=self.scene_widget_signals, tree_signals=self.tree_signals)
        self.setCentralWidget(self.scene_widget)
        self.plotter = self.scene_widget.plotter

    def open_file(self):
        """UI function to handle file opening"""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Open File",
                "",
                "All Supported Files (*.xyz *.cube);;XYZ files (*.xyz);;Cube files (*.cube);;All Files (*)"
            )

            if file_name:
                filepath = pathlib.Path(file_name)
                if filepath.suffix.lower() == '.cube':
                    choice = QMessageBox.question(
                        self,
                        "Load Cube File",
                        "Would you like to load this as molecule with field?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )

                    if choice == QMessageBox.Yes:
                        self.scene_manager.load_molecule_from_cube(filepath)
                    else:
                        self.scene_manager.load_scalar_field_from_cube(
                            filepath)
                else:
                    self.scene_manager.load_xyz(filepath)

                self.refresh_view()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to load file: {str(e)}")

    def on_screenshot(self):
        """Save a screenshot of the current view"""
        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save Screenshot",
                "",
                "PNG Files (*.png);;JPG Files (*.jpg);;All Files (*)"
            )

            if file_name:
                # Add default extension if none specified
                if not pathlib.Path(file_name).suffix:
                    file_name += ".png"

                # Take the screenshot using the existing method
                self.scene_widget.take_screenshot(file_name)

                QMessageBox.information(
                    self,
                    "Screenshot Saved",
                    f"Screenshot saved to {file_name}"
                )

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to save screenshot: {str(e)}"
            )

    def on_render(self):
        """Save a high-quality render of the current view"""
        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save Render",
                "",
                "PNG Files (*.png);;JPG Files (*.jpg);;TIFF Files (*.tiff);;All Files (*)"
            )

            if file_name:
                # Add default extension if none specified
                if not pathlib.Path(file_name).suffix:
                    file_name += ".png"

                # Create render settings dialog
                render_dialog = RenderDialog(parent=self)

                if render_dialog.exec_() == QDialog.Accepted:
                    settings = render_dialog.get_settings()

                    # Perform high-quality render
                    self.scene_widget.render_high_quality(file_name, settings)

                    QMessageBox.information(
                        self,
                        "Render Saved",
                        f"High-quality render saved to {file_name}"
                    )

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to save render: {str(e)}"
            )

    def refresh_view(self):
        """Update the visualization"""
        logger.info("Refreshing view")
        self.scene_widget.refresh_view()

    def refresh_interpolated_view(self):
        """Update the visualization with interpolated trajectory positions"""
        if self._animation_time is not None and self._animating_trajectory_uuid:
            logger.debug(
                f"Refreshing interpolated view at time {self._animation_time:.2f}")
            self.scene_widget.refresh_interpolated_view(
                self._animating_trajectory_uuid,
                self._animation_time
            )
        else:
            self.refresh_view()

    def reset_camera(self):
        """Reset the camera to show all objects"""
        logger.info("Resetting camera")
        self.scene_widget.reset_camera()

    def on_selection_changed(self):
        """Handle object selection in the list"""
        pass

    def on_visibility_changed(self, uuid: str, visible: bool):
        """Handle visibility toggle"""
        logger.debug(f"Visibility changed for {uuid}: {visible}")
        # Update visibility state in scene manager
        if self.scene_manager.set_visibility(uuid, visible):
            # No need to force view refresh here as render_changed signal will handle it
            pass

    def on_render_changed(self, uuid: str = None):
        """Handle render change signal from tree"""
        self.refresh_view()

    def on_structure_changed(self):
        """Handle structure change signal from tree"""
        # Update the tree itself
        self.object_list_widget._refresh_tree()
        # Also refresh the view
        self.refresh_view()

    def on_settings_requested(self, uuid: str):
        """Handle settings button click"""
        obj = self.scene_manager.get_object_by_uuid(uuid)

        # Create dialog with explicit parent
        if hasattr(obj, 'molecule'):
            dialog = RenderSettingsDialog(obj.render_settings, parent=self)
        else:
            dialog = ScalarFieldSettingsDialog(
                obj.render_settings, parent=self)

        # Show dialog as modal
        if dialog.exec_() == QDialog.Accepted:
            self.scene_manager.update_settings(uuid, dialog.get_settings())
            # No need to call refresh_view here as on_render_changed will be triggered
            # by the update_settings method through the scene manager signals

    def on_camera_settings(self):
        """Handle camera settings action"""
        self.scene_widget.show_camera_settings_dialog()

    def on_background_color(self):
        """Handle background color selection"""
        try:
            # Get current background color from the plotter if available
            current_color = None
            if hasattr(self.scene_widget.plotter, 'background_color'):
                current_color = self.scene_widget.plotter.background_color

            # Open color dialog
            color = QColorDialog.getColor(
                parent=self,
                title="Choose Background Color"
            )

            if color.isValid():
                # Set the background color
                self.scene_widget.set_background_color(color.name())
                logger.info(f"Background color changed to: {color.name()}")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to change background color: {str(e)}"
            )

    def on_export_glb(self):
        """Export scene to static GLB file"""
        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Export to GLB",
                "",
                "GLB Files (*.glb);;GLTF Files (*.gltf);;All Files (*)"
            )

            if file_name:
                # Add default extension if none specified
                if not pathlib.Path(file_name).suffix:
                    file_name += ".glb"

                # Show export mode dialog
                export_dialog = StaticExportDialog(parent=self)

                if export_dialog.exec_() == QDialog.Accepted:
                    settings = export_dialog.get_settings()

                    self.scene_manager.export_to_glb(
                        file_name,
                        printing_mode=settings['printing_mode'],
                        printing_resolution=settings['printing_resolution']
                    )

                    mode_str = " (3D printing mode)" if settings['printing_mode'] else ""
                    QMessageBox.information(
                        self,
                        "Export Complete",
                        f"Scene exported to {file_name}{mode_str}"
                    )

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to export GLB: {str(e)}"
            )

    def on_export_animated_glb(self):
        """Export scene to animated GLB file"""
        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Export Animated GLB",
                "",
                "GLB Files (*.glb);;GLTF Files (*.gltf);;All Files (*)"
            )

            if file_name:
                # Add default extension if none specified
                if not pathlib.Path(file_name).suffix:
                    file_name += ".glb"

                # Show export settings dialog
                export_dialog = AnimatedExportDialog(parent=self)

                if export_dialog.exec_() == QDialog.Accepted:
                    settings = export_dialog.get_settings()

                    self.scene_manager.export_animated_glb(
                        file_name,
                        fps=settings['fps'],
                        resolution=settings['resolution'],
                        cycle_animation=settings['cycle'],
                        scale=settings['scale']
                    )

                    QMessageBox.information(
                        self,
                        "Export Complete",
                        f"Animated scene exported to {file_name}"
                    )

        except ValueError as e:
            QMessageBox.warning(
                self, "Export Warning", str(e)
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to export animated GLB: {str(e)}"
            )

    def on_palette_settings(self):
        """Open the atom palette settings dialog."""
        try:
            # Get current palette settings from the molecule renderer
            # Include both atom settings and bond settings
            current_settings = self.scene_manager.molecule_renderer.atoms_settings.copy()
            current_settings['bonds'] = self.scene_manager.molecule_renderer.bond_settings.copy(
            )

            # Create and show the dialog
            dialog = PaletteSettingsDialog(current_settings, parent=self)

            if dialog.exec_() == QDialog.Accepted:
                new_settings = dialog.get_settings()

                # Apply the new settings to the renderer
                self.scene_manager.molecule_renderer.set_atom_settings(
                    new_settings)

                logger.info("Palette settings updated")

                # Refresh the view to show the changes
                self.refresh_view()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to update palette settings: {str(e)}"
            )


class StaticExportDialog(QDialog):
    """Dialog for static GLB export settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GLB Export Settings")
        self.setModal(True)

        layout = QVBoxLayout()

        # Export mode selection
        mode_label = QLabel("<b>Export Mode:</b>")
        layout.addWidget(mode_label)

        self.viz_radio = QCheckBox(
            "Visualization (default - with gaps between atoms and bonds)")
        self.viz_radio.setChecked(True)
        layout.addWidget(self.viz_radio)

        self.print_radio = QCheckBox(
            "3D Printing (no gaps, high resolution, solid)")
        layout.addWidget(self.print_radio)

        # Make them mutually exclusive
        self.viz_radio.stateChanged.connect(
            lambda state: self.print_radio.setChecked(not state))
        self.print_radio.stateChanged.connect(
            lambda state: self.viz_radio.setChecked(not state))

        layout.addSpacing(10)

        # Resolution setting (only for printing mode)
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("3D Printing Resolution:"))
        self.resolution_spin = QSpinBox()
        self.resolution_spin.setRange(16, 64)
        self.resolution_spin.setValue(32)
        self.resolution_spin.setToolTip(
            "Higher = smoother surfaces but larger file")
        self.resolution_spin.setEnabled(False)
        res_layout.addWidget(self.resolution_spin)
        layout.addLayout(res_layout)

        # Enable resolution spin only in printing mode
        self.print_radio.stateChanged.connect(
            lambda state: self.resolution_spin.setEnabled(state))

        layout.addSpacing(10)

        # Info text
        info_label = QLabel(
            "<small><i>3D Printing mode creates watertight meshes with bonds "
            "connected center-to-center for better printing results.</i></small>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Export")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_settings(self):
        return {
            'printing_mode': self.print_radio.isChecked(),
            'printing_resolution': self.resolution_spin.value()
        }


class AnimatedExportDialog(QDialog):
    """Dialog for animated GLB export settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Animated Export Settings")
        self.setModal(True)

        layout = QVBoxLayout()

        # FPS setting
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("Frames per second:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(10)
        fps_layout.addWidget(self.fps_spin)
        layout.addLayout(fps_layout)

        # Resolution setting
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Mesh resolution:"))
        self.resolution_spin = QSpinBox()
        self.resolution_spin.setRange(3, 30)
        self.resolution_spin.setValue(10)
        self.resolution_spin.setToolTip("Lower values = smaller file size")
        res_layout.addWidget(self.resolution_spin)
        layout.addLayout(res_layout)

        # Cycle animation checkbox
        self.cycle_cb = QCheckBox("Loop animation (add reverse frames)")
        layout.addWidget(self.cycle_cb)

        # Scale setting
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Scale:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(
            ["None (Angstroms)", "Auto (fit to 2 units)", "Custom..."])
        self.scale_combo.currentIndexChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self.scale_combo)

        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.001, 100.0)
        self.scale_spin.setValue(0.1)
        self.scale_spin.setDecimals(4)
        self.scale_spin.setVisible(False)
        scale_layout.addWidget(self.scale_spin)
        layout.addLayout(scale_layout)

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Export")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _on_scale_changed(self, index):
        """Show/hide custom scale input"""
        self.scale_spin.setVisible(index == 2)

    def get_settings(self):
        scale_index = self.scale_combo.currentIndex()
        if scale_index == 0:
            scale = None
        elif scale_index == 1:
            scale = "auto"
        else:
            scale = self.scale_spin.value()

        return {
            'fps': self.fps_spin.value(),
            'resolution': self.resolution_spin.value(),
            'cycle': self.cycle_cb.isChecked(),
            'scale': scale
        }


class RenderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Render Settings")
        self.setModal(True)

        layout = QVBoxLayout()

        # Resolution settings
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Width:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 8192)
        self.width_spin.setValue(1920)
        res_layout.addWidget(self.width_spin)

        res_layout.addWidget(QLabel("Height:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 8192)
        self.height_spin.setValue(1080)
        res_layout.addWidget(self.height_spin)

        layout.addLayout(res_layout)

        # Quality settings
        self.anti_aliasing_cb = QCheckBox("Anti-aliasing")
        self.anti_aliasing_cb.setChecked(True)
        layout.addWidget(self.anti_aliasing_cb)

        self.shadows_cb = QCheckBox("Shadows")
        layout.addWidget(self.shadows_cb)

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Render")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_settings(self):
        return {
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'anti_aliasing': self.anti_aliasing_cb.isChecked(),
            'shadows': self.shadows_cb.isChecked()
        }
