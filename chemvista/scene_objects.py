import pyvista as pv
from nx_ase import Molecule, ScalarField, Path
import pathlib
from typing import Union, Optional, List, Dict
from .renderer import MoleculeRenderer, ScalarFieldRenderer
from .render_settings import RenderSettings, ScalarFieldRenderSettings
from PyQt5.QtCore import QObject, pyqtSignal


class SceneObject:
    def __init__(self, name: str, molecule: Molecule):
        self.name = name
        self.molecule = molecule
        self.visible = True
        self.render_settings = RenderSettings()


class ScalarFieldObject:
    def __init__(self, name: str, scalar_field: ScalarField):
        self.name = name
        self.scalar_field = scalar_field
        self.visible = True
        self.render_settings = ScalarFieldRenderSettings()


class SceneManager(QObject):
    # Signals
    object_added = pyqtSignal(str)  # emits object name
    object_removed = pyqtSignal(str)  # emits object name
    object_changed = pyqtSignal(str)  # emits object name
    # emits object name and visibility state
    visibility_changed = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self.objects = []
        self.molecule_renderer = MoleculeRenderer()
        self.scalar_field_renderer = ScalarFieldRenderer()
        self.plotter = None

    def __del__(self):
        """Cleanup resources"""
        if self.plotter is not None:
            self.plotter.close()

    def create_plotter(self, off_screen: bool = False) -> pv.Plotter:
        """Create a new plotter or return existing one"""
        if self.plotter is None:
            self.plotter = pv.Plotter(off_screen=off_screen)
        return self.plotter

    def load_molecule(self, filepath: Union[str, pathlib.Path]) -> List[str]:
        """Load molecules from XYZ file"""
        filepath = pathlib.Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File {filepath} not found")
        path = Path.load(filepath)
        if len(path) == 1:
            molecule = path[0]
            return [self.add_object(filepath.stem, molecule)]

        return [self.add_object(f"{filepath.stem}_{i}", molecule) for i, molecule in enumerate(path)]

    def load_molecule_from_cube(self, filepath: Union[str, pathlib.Path]) -> List[str]:
        """Load both molecule and its scalar field from cube file"""
        filepath = pathlib.Path(filepath)
        molecule = Molecule.load_from_cube(filepath)

        # Add molecule first
        mol_name = filepath.name
        names = [self.add_object(mol_name, molecule)]

        # Then add its associated scalar fields
        for field_name, scalar_field in molecule.scalar_fields.items():
            names.append(self.add_object(field_name, scalar_field))

        return names

    def load_scalar_field(self, filepath: Union[str, pathlib.Path]) -> str:
        """Load scalar field from cube file"""
        filepath = pathlib.Path(filepath)
        scalar_field = ScalarField.load_cube(filepath)
        field_name = f"{filepath.stem}_field"
        return self.add_object(field_name, scalar_field)

    def add_object(self, name: str, obj: Union[Molecule, ScalarField]) -> str:
        """Add object to scene and return its name"""
        if isinstance(obj, Molecule):
            scene_obj = SceneObject(name, obj)
        elif isinstance(obj, ScalarField):
            scene_obj = ScalarFieldObject(name, obj)
        else:
            raise ValueError(f"Unsupported object type: {type(obj)}")

        self.objects.append(scene_obj)
        self.object_added.emit(name)  # Emit signal
        return name

    def remove_object(self, name: str) -> None:
        """Remove object from scene"""
        obj = self.get_object_by_name(name)
        self.objects.remove(obj)
        self.object_removed.emit(name)  # Emit signal

    def get_object(self, index: int) -> Union[SceneObject, ScalarFieldObject]:
        """Get object by index"""
        return self.objects[index]

    def get_object_by_name(self, name: str) -> Union[SceneObject, ScalarFieldObject]:
        """Get object by name"""
        for obj in self.objects:
            if obj.name == name:
                return obj
        raise KeyError(f"Object {name} not found")

    def set_visibility(self, name: str, visible: bool) -> None:
        """Set object visibility"""
        obj = self.get_object_by_name(name)
        obj.visible = visible
        self.visibility_changed.emit(name, visible)  # Emit signal

    def update_settings(self, name: str, settings: Union[RenderSettings, ScalarFieldRenderSettings]) -> None:
        """Update object render settings"""
        obj = self.get_object_by_name(name)
        obj.render_settings = settings
        self.object_changed.emit(name)  # Emit signal

    def render(self, plotter: Optional[pv.Plotter] = None, **kwargs) -> pv.Plotter:
        """Render all visible objects

        Args:
            plotter: Optional plotter to use
            **kwargs: Additional arguments passed to plotter creation
        """
        if plotter is None:
            if self.plotter is not None:
                self.plotter.close()
            plotter = pv.Plotter(**kwargs) if kwargs else self.create_plotter()

        plotter.clear()

        for obj in self.objects:
            if obj.visible:
                if isinstance(obj, SceneObject):
                    self.molecule_renderer.render(
                        molecule=obj.molecule,
                        plotter=plotter,
                        settings=vars(obj.render_settings)
                    )
                elif isinstance(obj, ScalarFieldObject):
                    self.scalar_field_renderer.render(
                        field=obj.scalar_field,
                        plotter=plotter,
                        settings=vars(obj.render_settings)
                    )

        plotter.reset_camera()
        return plotter

    def save_molecule(self, name: str, filepath: Union[str, pathlib.Path]) -> None:
        """Save molecule to file"""
        obj = self.get_object_by_name(name)
        if not isinstance(obj, SceneObject):
            raise ValueError(f"Object {name} is not a molecule")
        obj.molecule.save(filepath)
