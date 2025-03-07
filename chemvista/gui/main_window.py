from PyQt5.QtWidgets import (QMainWindow, QDockWidget, QAction, QFileDialog,
                             QMessageBox, QToolBar, QDialog)
from PyQt5.QtCore import Qt
from pyvistaqt import QtInteractor
import pathlib
from typing import Dict, List, Optional
from ..scene_manager import SceneManager
from .widgets.object_tree import ObjectTreeWidget
from .widgets.settings_dialog import RenderSettingsDialog, ScalarFieldSettingsDialog


class ChemVistaApp(QMainWindow):
    def __init__(self, scene_manager: SceneManager | None = None, init_files: Optional[Dict[str, List[pathlib.Path]]] = None):
        super().__init__()
        self.setWindowTitle("ChemVista")
        self.resize(1200, 800)

        # Use provided scene manager or create new one
        self.scene_manager = scene_manager or SceneManager()

        # Create menu bar
        self.create_menu_bar()

        # Create tool bar
        self.create_tool_bar()

        # Create left panel for object list
        self.create_object_list()

        # Create central PyVista widget
        self.create_pyvista_widget()

        # Set plotter in scene manager
        self.scene_manager.plotter = self.plotter

        # Load initial files if provided
        if init_files:
            self.load_initial_files(init_files)

        # Make sure tree is expanded by default
        self.object_list_widget.expandAll()

        # Show the window and raise it to front
        self.show()
        self.raise_()
        self.activateWindow()

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

        self.object_list_widget = ObjectTreeWidget(self.scene_manager)
        self.object_list_widget.selection_changed.connect(
            self.on_selection_changed)
        self.object_list_widget.visibility_changed.connect(
            self.on_visibility_changed)
        self.object_list_widget.settings_requested.connect(
            self.on_settings_requested)

        dock.setWidget(self.object_list_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def create_pyvista_widget(self):
        self.plotter = QtInteractor(self)
        self.setCentralWidget(self.plotter)

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
        if not self.scene_manager.children:  # Changed from objects to root_objects
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
        self.scene_manager.render(self.plotter)
        self.plotter.update()

    def on_selection_changed(self):
        """Handle object selection in the list"""
        pass

    def on_visibility_changed(self, uuid: str, visible: bool):
        """Handle visibility toggle"""
        print(f"Visibility changed for {uuid}: {visible}")
        self.scene_manager.set_visibility(uuid, visible)
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
            self.refresh_view()
