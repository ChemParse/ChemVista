import pyvista as pv
from abc import ABC, abstractmethod


class Renderer(ABC):
    """Base class for all renderers"""

    @abstractmethod
    def render(self, obj, plotter: pv.Plotter, settings: dict, show: bool = False) -> None:
        """Render an object to the plotter using provided settings"""
        pass

    @abstractmethod
    def get_default_settings(self) -> dict:
        """Get default rendering settings for this renderer"""
        pass

    @abstractmethod
    def validate_settings(self, settings: dict) -> bool:
        """Validate that the settings are appropriate for this renderer"""
        pass
