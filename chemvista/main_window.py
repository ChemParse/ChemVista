from PyQt5.QtWidgets import (QMainWindow, QDockWidget, QAction, QFileDialog,
                             QMessageBox, QToolBar, QDialog)
from PyQt5.QtCore import Qt
import pyvista as pv
from pyvistaqt import QtInteractor
import os
from nx_ase.molecule import Molecule
from .scene_objects import SceneManager
import pathlib
from .renderer import MoleculeRenderer
from .widgets.object_list import ObjectListWidget
from PyQt5 import QtCore
import chemvista.resources.icons_rc
from .widgets.settings_dialog import RenderSettingsDialog


class ChemVistaApp(QMainWindow):
    def __init__(self, debug=True):
        super().__init__()
        self.setWindowTitle("ChemVista")
        self.resize(1200, 800)

        # Initialize scene manager
        self.scene_manager = SceneManager()

        # Initialize renderer
        self.renderer = MoleculeRenderer()

        # Create menu bar
        self.create_menu_bar()

        # Create tool bar
        self.create_tool_bar()

        # Create left panel for object list
        self.create_object_list()

        # Create central PyVista widget
        self.create_pyvista_widget()

        # Debug: Load test molecule
        if debug:
            try:
                test_file = pathlib.Path(
                    "/home/ivan/Science/hannes_nanomotors/nanomotors/fluorene/0/B3LYP/6_31G_d_p/cis1.xyz")
                if test_file.exists():
                    molecule = Molecule.load(test_file)
                    self.scene_manager.add_object("debug_molecule", molecule)
                    self.refresh_view()
            except Exception as e:
                print(f"Debug load failed: {e}")

        self.show()

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

        self.object_list_widget = ObjectListWidget(self.scene_manager)
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
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Open Molecule File",
                "",
                "XYZ files (*.xyz);;All Files (*)"
            )

            if file_name:
                molecule = Molecule.load(file_name)
                name = os.path.basename(file_name)
                self.scene_manager.add_object(name, molecule)
                self.refresh_view()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to load file: {str(e)}")

    def save_file(self):
        if not self.scene_manager.objects:
            QMessageBox.warning(self, "Warning", "No objects to save!")
            return

        try:
            selected_index = self.object_list_widget.get_selected_index()
            if selected_index is None:
                QMessageBox.warning(self, "Warning", "No object selected!")
                return

            scene_obj = self.scene_manager.get_object(selected_index)

            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save Molecule File",
                "",
                "XYZ files (*.xyz);;All Files (*)"
            )

            if file_name:
                scene_obj.molecule.save(file_name)

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to save file: {str(e)}")

    def refresh_view(self):
        """Update the 3D visualization"""
        self.plotter.clear()

        for scene_obj in self.scene_manager.objects:
            if scene_obj.visible:
                settings = scene_obj.render_settings
                self.renderer.render_molecule(
                    molecule=scene_obj.molecule,
                    plotter=self.plotter,
                    show_hydrogens=settings.show_hydrogens,
                    alpha=settings.alpha,  # Changed from opacity to alpha
                    show_numbers=settings.show_numbers,
                    resolution=settings.resolution
                )

        self.plotter.reset_camera()
        self.plotter.update()

    def on_selection_changed(self):
        """Handle object selection in the list"""
        pass

    def on_visibility_changed(self, index: int, visible: bool):
        """Handle visibility toggle for a molecule"""
        if 0 <= index < len(self.scene_manager.objects):
            self.scene_manager.objects[index].visible = visible
            self.refresh_view()

    def on_settings_requested(self, index: int):
        """Handle settings button click for a molecule"""
        if 0 <= index < len(self.scene_manager.objects):
            scene_obj = self.scene_manager.get_object(index)
            dialog = RenderSettingsDialog(scene_obj.render_settings, self)

            if dialog.exec_() == QDialog.Accepted:
                scene_obj.render_settings = dialog.get_settings()
                self.refresh_view()
