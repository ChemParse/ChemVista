import pathlib
from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (QAction, QDialog, QDockWidget, QFileDialog,
                             QMainWindow, QMessageBox, QToolBar)

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

        # Create tool bar
        self.create_tool_bar()

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

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)

        file_menu.addAction(open_action)
        file_menu.addAction(save_action)

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

    def create_tool_bar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Add basic tools (will be implemented later)
        toolbar.addAction(QAction("Select", self))
        toolbar.addAction(QAction("Rotate", self))
        toolbar.addAction(QAction("Pan", self))

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

    def save_file(self):
        """Save selected object to file"""
        if not self.scene_manager.root_objects:
            QMessageBox.warning(self, "Warning", "No objects to save!")
            return

        try:
            selected_uuid = self.object_list_widget.get_selected_uuid()
            if selected_uuid is None:
                QMessageBox.warning(self, "Warning", "No object selected!")
                return

            obj = self.scene_manager.get_object_by_uuid(selected_uuid)

            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                "",
                "XYZ files (*.xyz);;All Files (*)"
            )

            if file_name:
                if hasattr(obj, 'molecule'):
                    obj.molecule.save(file_name)
                else:
                    QMessageBox.warning(
                        self, "Warning", "Can only save molecules!")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to save file: {str(e)}")

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

    def take_screenshot(self, filename=None):
        """Take a screenshot of the current view"""
        return self.scene_widget.take_screenshot(filename)
