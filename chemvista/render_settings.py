from dataclasses import dataclass, field
from typing import Dict
import copy


@dataclass
class RenderSettings:
    show_hydrogens: bool = True
    show_numbers: bool = False
    alpha: float = 1.0  # Changed from opacity to alpha
    resolution: int = 20
    # Override colors for specific elements
    custom_colors: Dict[str, list] = field(default_factory=dict)

    def copy(self):
        return copy.deepcopy(self)


class GlobalSettings:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.render_settings = RenderSettings()
        return cls._instance

    @classmethod
    def get_default_settings(cls) -> RenderSettings:
        return cls().render_settings.copy()
