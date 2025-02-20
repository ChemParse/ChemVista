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


@dataclass
class ScalarFieldRenderSettings:
    visible: bool = True
    isosurface_value: float = 0.1
    show_grid_surface: bool = False
    show_grid_points: bool = False
    opacity: float = 0.3
    color: str = 'blue'
    grid_surface_color: str = 'blue'
    grid_points_color: str = 'red'
    grid_points_size: int = 5
    smooth_surface: bool = True
    show_filtered_points: bool = False
    point_value_range: tuple = (0.0, 1.0)

    def copy(self):
        return copy.deepcopy(self)


class GlobalSettings:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.render_settings = RenderSettings()
            cls._instance.scalar_field_settings = ScalarFieldRenderSettings()
        return cls._instance

    @classmethod
    def get_default_settings(cls) -> RenderSettings:
        return cls().render_settings.copy()

    @classmethod
    def get_default_scalar_field_settings(cls) -> ScalarFieldRenderSettings:
        return cls().scalar_field_settings.copy()
