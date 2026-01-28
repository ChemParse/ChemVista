import pathlib
from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (QAction, QDialog, QDockWidget, QFileDialog,
                             QMainWindow, QMessageBox, QToolBar, QColorDialog,
                             QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QCheckBox, QPushButton)

from ..scene_manager import SceneManager
from ..tree_structure import TreeSignals
from .scene import SceneWidget, SceneWidgetSignals
from .widgets.object_tree import ObjectTreeWidget, TreeWidgetSignals
import logging
from .widgets.settings_dialog import (RenderSettingsDialog,
                                      ScalarFieldSettingsDialog)

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

        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(render_action)

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

    def create_object_list(self):
        dock = QDockWidget("Objects", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.object_list_widget = ObjectTreeWidget(
            self.scene_manager, self, tree_widget_signals=self.tree_widget_signals, tree_signals=self.tree_signals)

        dock.setWidget(self.object_list_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

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
