import argparse
import pathlib
from typing import Dict, List
import sys

from PyQt5.QtWidgets import QApplication
from chemvista import SceneManager
from chemvista.gui import ChemVistaApp
from chemvista.gui.qt_utils import setup_environment
from chemvista.renderer import get_available_palettes


def main():
    parser = argparse.ArgumentParser(
        description='ChemVista - Chemical Visualization Tool')

    parser.add_argument('--xyz', nargs='*', type=pathlib.Path, default=[],
                        help='List of XYZ files to load')
    parser.add_argument('--cube-mol', nargs='*', type=pathlib.Path, default=[],
                        help='List of cube files to load as molecules with fields')
    parser.add_argument('--cube-field', nargs='*', type=pathlib.Path, default=[],
                        help='List of cube files to load as scalar fields only')

    # Define mutually exclusive group for the modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('-i', '--interactive', action='store_true',
                            help='Start the GUI in interactive mode')
    mode_group.add_argument('-r', '--render', action='store_true',
                            help='Render the scene with PyVista viewer')
    mode_group.add_argument('-s', '--screenshot', type=pathlib.Path,
                            help='Save a screenshot to the specified file path')
    mode_group.add_argument('-g', '--glb', type=pathlib.Path,
                            help='Export scene to GLB file for PowerPoint 3D')
    mode_group.add_argument('--glb-animated', type=pathlib.Path,
                            help='Export trajectory as animated GLB file for PowerPoint')

    # Animation options (used with --glb-animated)
    parser.add_argument('--fps', type=int, default=10,
                        help='Frames per second for animated GLB (default: 10)')
    parser.add_argument('--resolution', type=int, default=10,
                        help='Mesh resolution for animated GLB - lower values reduce file size (default: 10)')
    parser.add_argument('--cycle', action='store_true',
                        help='Add reverse frames to create a seamless loop animation')
    parser.add_argument('--scale', type=str, default=None,
                        help='Scale factor for model size. Use "auto" to fit in 2-unit box, or a number (e.g., 0.1)')

    # Color palette options
    available_palettes = get_available_palettes()
    parser.add_argument('--palette', type=str, default=None,
                        help=f'Color palette for atoms. Built-in: {", ".join(available_palettes)}. '
                             'Or provide path to custom JSON file.')
    parser.add_argument('--radius-scale', type=float, default=1.0,
                        help='Scale factor for atom radii (default: 1.0)')

    args = parser.parse_args()

    scene_manager = SceneManager()
    for xyz_file in args.xyz:
        scene_manager.load_xyz(xyz_file)

    for cube_file in args.cube_mol:
        scene_manager.load_molecule_from_cube(cube_file)

    for cube_file in args.cube_field:
        scene_manager.load_scalar_field_from_cube(cube_file)

    # Apply palette if specified
    if args.palette:
        try:
            scene_manager.set_palette(args.palette, radius_scale=args.radius_scale)
            print(f"Using palette: {args.palette} (radius scale: {args.radius_scale})")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif args.radius_scale != 1.0:
        # Apply radius scale to default palette
        scene_manager.set_palette("chemvista", radius_scale=args.radius_scale)
        print(f"Using default palette with radius scale: {args.radius_scale}")

    if args.interactive:
        # Mode 1: Full PyQt GUI application
        setup_environment()  # This will print system info and setup environment
        app = QApplication(sys.argv)
        window = ChemVistaApp(scene_manager)
        sys.exit(app.exec_())
    elif args.screenshot:
        # Mode 3: Save a screenshot to the specified file
        plotter, _ = scene_manager.render(off_screen=True)
        plotter.screenshot(str(args.screenshot))
        print(f"Screenshot saved to: {args.screenshot}")
    elif args.glb:
        # Mode 4: Export scene to GLB file
        scene_manager.export_to_glb(args.glb)
        print(f"Scene exported to GLB: {args.glb}")
    elif args.glb_animated:
        # Mode 5: Export scene as animated GLB
        # Parse scale parameter
        scale_value = args.scale
        if scale_value is not None and scale_value != "auto":
            try:
                scale_value = float(scale_value)
            except ValueError:
                print(f"Error: Invalid scale value '{args.scale}'. Use 'auto' or a number.")
                sys.exit(1)

        print(f"Exporting scene as animated GLB...")
        print(f"  FPS: {args.fps}")
        print(f"  Resolution: {args.resolution}")
        print(f"  Cycle: {args.cycle}")
        print(f"  Scale: {scale_value if scale_value else 'none (Angstroms)'}")

        try:
            scene_manager.export_animated_glb(
                args.glb_animated,
                fps=args.fps,
                resolution=args.resolution,
                cycle_animation=args.cycle,
                scale=scale_value
            )
            print(f"✅ Animated scene exported to: {args.glb_animated}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # Mode 2: Just render with PyVista (default mode)
        plotter, _ = scene_manager.render()
        plotter.show()


if __name__ == '__main__':
    main()
