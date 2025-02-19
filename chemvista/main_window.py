from PyQt5.QtWidgets import (QMainWindow, QDockWidget, QListWidget,
                             QMenuBar, QToolBar, QAction, QFileDialog,
                             QMessageBox, QWidget, QVBoxLayout, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal
import pyvista as pv
from pyvistaqt import QtInteractor
import os
from nx_ase.molecule import Molecule
from .scene_objects import SceneManager
import pathlib
from .renderer import MoleculeRenderer


class ObjectListWidget(QWidget):
    selection_changed = pyqtSignal(int)

    def __init__(self, scene_manager, parent=None):
        super().__init__(parent)
        self.scene_manager = scene_manager

        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(
            self._on_selection_changed)
        layout.addWidget(self.list_widget)

        # Connect to scene manager signals
        self.scene_manager.object_added.connect(self._on_object_added)
        self.scene_manager.object_removed.connect(self._on_object_removed)

        self.setLayout(layout)

    def _on_object_added(self, scene_obj):
        self.list_widget.addItem(scene_obj.name)

    def _on_object_removed(self, index):
        self.list_widget.takeItem(index)

    def _on_selection_changed(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            index = self.list_widget.row(selected_items[0])
            self.selection_changed.emit(index)

    def get_selected_index(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            return self.list_widget.row(selected_items[0])
        return None


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
                self.renderer.render_molecule(
                    molecule=scene_obj.molecule,
                    plotter=self.plotter,
                    alpha=scene_obj.opacity
                )

        self.plotter.reset_camera()
        self.plotter.update()

    def on_selection_changed(self):
        """Handle object selection in the list"""
        pass
