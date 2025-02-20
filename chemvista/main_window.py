from PyQt5.QtWidgets import (QMainWindow, QDockWidget, QAction, QFileDialog,
                             QMessageBox, QToolBar, QDialog)
from PyQt5.QtCore import Qt
from pyvistaqt import QtInteractor
import pathlib
from .scene_objects import SceneManager
from .widgets.object_list import ObjectListWidget
from .widgets.settings_dialog import RenderSettingsDialog, ScalarFieldSettingsDialog


class ChemVistaApp(QMainWindow):
    def __init__(self, scene_manager=None, debug=True):
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

        # Debug: Load test files
        if debug:
            try:
                data_dir = pathlib.Path(
                    __file__).parent.parent / 'tests' / 'data'
                test_cube = data_dir / 'C2H4.eldens.cube'
                self.scene_manager.load_molecule_from_cube(test_cube)
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
                        self.scene_manager.load_scalar_field(filepath)
                else:
                    self.scene_manager.load_molecule(filepath)

                self.refresh_view()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to load file: {str(e)}")

    def save_file(self):
        """Save selected object to file"""
        if not self.scene_manager.objects:
            QMessageBox.warning(self, "Warning", "No objects to save!")
            return

        try:
            selected_index = self.object_list_widget.get_selected_index()
            if selected_index is None:
                QMessageBox.warning(self, "Warning", "No object selected!")
                return

            obj = self.scene_manager.get_object(selected_index)

            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                "",
                "XYZ files (*.xyz);;All Files (*)"
            )

            if file_name:
                self.scene_manager.save_molecule(obj.name, file_name)

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

    def on_visibility_changed(self, index: int, visible: bool):
        """Handle visibility toggle"""
        if 0 <= index < len(self.scene_manager.objects):
            obj = self.scene_manager.get_object(index)
            self.scene_manager.set_visibility(obj.name, visible)
            self.refresh_view()

    def on_settings_requested(self, index: int):
        """Handle settings button click"""
        if 0 <= index < len(self.scene_manager.objects):
            obj = self.scene_manager.get_object(index)

            # Create dialog with explicit parent
            if hasattr(obj, 'molecule'):
                dialog = RenderSettingsDialog(obj.render_settings, parent=self)
            else:
                dialog = ScalarFieldSettingsDialog(
                    obj.render_settings, parent=self)

            # Show dialog as modal
            if dialog.exec_() == QDialog.Accepted:
                self.scene_manager.update_settings(
                    obj.name, dialog.get_settings())
                self.refresh_view()
