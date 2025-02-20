from PyQt5.QtWidgets import (QMainWindow, QDockWidget, QAction, QFileDialog,
                             QMessageBox, QToolBar, QDialog)
from PyQt5.QtCore import Qt
import pyvista as pv
from pyvistaqt import QtInteractor
import os
from nx_ase import Molecule, ScalarField
from .scene_objects import SceneManager, SceneObject, ScalarFieldObject  # Added imports
import pathlib
from .renderer import MoleculeRenderer, ScalarFieldRenderer
from .widgets.object_list import ObjectListWidget
from PyQt5 import QtCore
import chemvista.resources.icons_rc
from .widgets.settings_dialog import RenderSettingsDialog, ScalarFieldSettingsDialog


class ChemVistaApp(QMainWindow):
    def __init__(self, debug=True):
        super().__init__()
        self.setWindowTitle("ChemVista")
        self.resize(1200, 800)

        # Initialize scene manager
        self.scene_manager = SceneManager()

        # Initialize renderers
        self.molecule_renderer = MoleculeRenderer()
        self.scalar_field_renderer = ScalarFieldRenderer()

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
                test_molecule = pathlib.Path(
                    __file__).parent.parent / 'tests' / 'data' / 'mpf_motor.xyz'
                # self._load_molecule_from_xyz(test_molecule)
                test_scalar_field = pathlib.Path(
                    __file__).parent.parent / 'tests' / 'data' / 'C2H4.eldens.cube'
                # self._load_scalar_field(test_scalar_field)
                self._load_molecule_from_cube(test_scalar_field)
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

    def _load_molecule_from_xyz(self, filepath: pathlib.Path):
        """Load molecule from XYZ file"""
        molecule = Molecule.load(filepath)
        self.scene_manager.add_object(filepath.name, molecule)
        self.refresh_view()

    def _load_molecule_from_cube(self, filepath: pathlib.Path):
        """Load both molecule and its scalar field from cube file"""
        molecule = Molecule.load_from_cube(filepath)

        # Add molecule first
        mol_name = filepath.name
        self.scene_manager.add_object(mol_name, molecule)

        # Then add its associated scalar field
        for field_name, scalar_field in molecule.scalar_fields.items():
            self.scene_manager.add_object(field_name, scalar_field)

        self.refresh_view()

    def _load_scalar_field(self, filepath: pathlib.Path):
        """Load scalar field from cube file"""
        scalar_field = ScalarField.load_cube(filepath)
        field_name = f"{filepath.stem}_field"
        self.scene_manager.add_object(field_name, scalar_field)
        self.refresh_view()

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
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Load Cube File")
                    msg.setText("How would you like to load this cube file?")

                    # Add custom buttons
                    molecule_button = msg.addButton(
                        "As Molecule + Field", QMessageBox.ActionRole)
                    field_button = msg.addButton(
                        "As Scalar Field Only", QMessageBox.ActionRole)
                    msg.addButton(QMessageBox.Cancel)

                    msg.exec_()

                    if msg.clickedButton() == molecule_button:
                        self._load_molecule_from_cube(filepath)
                    elif msg.clickedButton() == field_button:
                        self._load_scalar_field(filepath)
                else:
                    self._load_molecule_from_xyz(filepath)

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
                if isinstance(scene_obj, SceneObject):
                    # Render molecule
                    self.molecule_renderer.render(
                        molecule=scene_obj.molecule,
                        plotter=self.plotter,
                        settings=vars(scene_obj.render_settings)
                    )
                elif isinstance(scene_obj, ScalarFieldObject):
                    # Render scalar field
                    self.scalar_field_renderer.render(
                        field=scene_obj.scalar_field,
                        plotter=self.plotter,
                        settings=vars(scene_obj.render_settings)
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
        """Handle settings button click for a molecule or scalar field"""
        if 0 <= index < len(self.scene_manager.objects):
            scene_obj = self.scene_manager.get_object(index)

            if isinstance(scene_obj, SceneObject):
                dialog = RenderSettingsDialog(scene_obj.render_settings, self)
            else:  # ScalarFieldObject
                dialog = ScalarFieldSettingsDialog(
                    scene_obj.render_settings, self)

            if dialog.exec_() == QDialog.Accepted:
                scene_obj.render_settings = dialog.get_settings()
                self.refresh_view()
