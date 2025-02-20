import numpy as np
import pyvista as pv
from nx_ase.scalar_field import ScalarField
from .base import Renderer


class ScalarFieldRenderer(Renderer):
    def get_default_settings(self) -> dict:
        return {
            'isosurface_value': 0.1,
            'opacity': 0.3,
            'show_grid_surface': False,
            'show_grid_points': False,
            'color': 'blue',
            'grid_surface_color': 'blue',
            'grid_points_color': 'red',
            'grid_points_size': 5,
            'smooth_surface': True,
            'show_filtered_points': False,
            'point_value_range': (0.0, 1.0)
        }

    def validate_settings(self, settings: dict) -> bool:
        required = {
            'isosurface_value', 'opacity', 'show_grid_surface',
            'show_grid_points', 'color', 'grid_surface_color',
            'grid_points_color', 'grid_points_size', 'smooth_surface',
            'show_filtered_points', 'point_value_range'
        }
        return all(key in settings for key in required)

    def render(self, field: ScalarField, plotter: pv.Plotter, settings: dict) -> None:
        if not self.validate_settings(settings):
            raise ValueError("Invalid settings for scalar field rendering")

        # Create structured grid using the field coordinates
        grid = pv.StructuredGrid(
            field.points[..., 0],
            field.points[..., 1],
            field.points[..., 2]
        )

        # Add scalar field data
        grid.point_data["scalar_field"] = field.scalar_field.ravel(order='F')

        # Create isosurface if value provided
        if settings['isosurface_value'] is not None:
            try:
                contour = grid.contour(
                    scalars="scalar_field",
                    isosurfaces=[settings['isosurface_value']]
                )

                # Only try to smooth if we have valid triangles
                if contour.n_points > 0:
                    try:
                        if settings['smooth_surface']:
                            contour = contour.subdivide(
                                nsub=2, subfilter='loop')
                            contour = contour.smooth(n_iter=50)
                    except pv.core.errors.NotAllTrianglesError:
                        # If smoothing fails, just use the unsmoothed contour
                        pass

                    plotter.add_mesh(
                        contour,
                        color=settings['color'],
                        opacity=settings['opacity'],
                        show_scalar_bar=False
                    )
                else:
                    print(
                        f"No isosurface found for value {settings['isosurface_value']}")
                    print(
                        f"Data range: [{grid.get_data_range()[0]}, {grid.get_data_range()[1]}]")

            except Exception as e:
                # Log the error but continue with the rest of the visualization
                print(f"Error creating isosurface: {str(e)}")
                print(f"Scalar field statistics:")
                print(f"Mean: {np.mean(field.scalar_field)}")
                print(f"STD: {np.std(field.scalar_field)}")
                print(f"Min: {np.min(field.scalar_field)}")
                print(f"Max: {np.max(field.scalar_field)}")

        # Show grid surface if requested
        if settings['show_grid_surface']:
            plotter.add_mesh(
                grid.outline(),
                color=settings['grid_surface_color'],
                opacity=0.1
            )

        # Show grid points if requested
        if settings['show_grid_points']:
            plotter.add_mesh(
                grid,
                style='points',
                point_size=settings['grid_points_size'],
                color=settings['grid_points_color'],
                render_points_as_spheres=True
            )

        # Show filtered points if requested
        if settings['show_filtered_points']:
            points_flat = field.points.reshape(-1, 3)
            scalar_flat = field.scalar_field.ravel()
            value_range = settings['point_value_range']

            mask = (scalar_flat >= value_range[0]) & (
                scalar_flat <= value_range[1])
            selected_points = points_flat[mask]

            if len(selected_points) > 0:
                plotter.add_points(
                    selected_points,
                    color=settings['grid_points_color'],
                    point_size=settings['grid_points_size'],
                    render_points_as_spheres=True
                )
            else:
                print(f"No points found in range {value_range}")
