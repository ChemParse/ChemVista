import pyvista as pv
from abc import ABC, abstractmethod
from typing import List


class Renderer(ABC):
    """Base class for all renderers"""

    @abstractmethod
    def render(self, obj, plotter: pv.Plotter, settings: dict, show: bool = False) -> List:
        """Render an object to the plotter using provided settings.

        Returns:
            List of VTK actors that were added to the plotter.
            These can be used for visibility control without full re-render.
        """
        pass

    @abstractmethod
    def get_default_settings(self) -> dict:
        """Get default rendering settings for this renderer"""
        pass

    @abstractmethod
    def validate_settings(self, settings: dict) -> bool:
        """Validate that the settings are appropriate for this renderer"""
        pass
