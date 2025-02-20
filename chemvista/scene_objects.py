from dataclasses import dataclass, field
from typing import Optional, Dict
import numpy as np
from nx_ase.molecule import Molecule
from nx_ase.scalar_field import ScalarField
from PyQt5.QtCore import QObject, pyqtSignal
from .render_settings import RenderSettings, GlobalSettings, ScalarFieldRenderSettings


@dataclass
class SceneObject:
    name: str
    molecule: Molecule
    visible: bool = True
    render_settings: RenderSettings = field(
        default_factory=GlobalSettings.get_default_settings)


@dataclass
class ScalarFieldObject:
    name: str
    scalar_field: ScalarField
    visible: bool = True
    render_settings: ScalarFieldRenderSettings = field(
        default_factory=GlobalSettings.get_default_scalar_field_settings)


class SceneManager(QObject):
    # Can be SceneObject or ScalarFieldObject
    object_added = pyqtSignal(object)
    object_removed = pyqtSignal(int)
    object_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.objects = []  # Can contain both SceneObject and ScalarFieldObject

    def add_object(self, name: str, obj) -> object:
        if isinstance(obj, Molecule):
            scene_obj = SceneObject(name=name, molecule=obj)
        elif isinstance(obj, ScalarField):
            scene_obj = ScalarFieldObject(name=name, scalar_field=obj)
        else:
            raise ValueError("Object must be either Molecule or ScalarField")

        self.objects.append(scene_obj)
        self.object_added.emit(scene_obj)
        return scene_obj

    def remove_object(self, index: int):
        if 0 <= index < len(self.objects):
            self.objects.pop(index)
            self.object_removed.emit(index)

    def get_object(self, index: int) -> Optional[object]:
        if 0 <= index < len(self.objects):
            return self.objects[index]
        return None

    def get_names(self):
        return [obj.name for obj in self.objects]
