from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from nx_ase.molecule import Molecule
from PyQt5.QtCore import QObject, pyqtSignal
from .render_settings import RenderSettings, GlobalSettings


@dataclass
class SceneObject:
    name: str
    molecule: Molecule
    visible: bool = True
    render_settings: RenderSettings = field(
        default_factory=GlobalSettings.get_default_settings)


class SceneManager(QObject):
    object_added = pyqtSignal(SceneObject)
    object_removed = pyqtSignal(int)
    object_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.objects = []

    def add_object(self, name: str, molecule: Molecule) -> SceneObject:
        scene_obj = SceneObject(name=name, molecule=molecule)
        self.objects.append(scene_obj)
        self.object_added.emit(scene_obj)
        return scene_obj

    def remove_object(self, index: int):
        if 0 <= index < len(self.objects):
            self.objects.pop(index)
            self.object_removed.emit(index)

    def get_object(self, index: int) -> Optional[SceneObject]:
        if 0 <= index < len(self.objects):
            return self.objects[index]
        return None

    def get_names(self):
        return [obj.name for obj in self.objects]
