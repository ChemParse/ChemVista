import argparse
import pathlib
from typing import Dict, List
import sys

from PyQt5.QtWidgets import QApplication
from chemvista import SceneManager
from chemvista.gui import ChemVistaApp, setup_qt_environment


def main():
    parser = argparse.ArgumentParser(
        description='ChemVista - Chemical Visualization Tool')

    parser.add_argument('--xyz', nargs='*', type=pathlib.Path, default=[],
                        help='List of XYZ files to load')
    parser.add_argument('--cube-mol', nargs='*', type=pathlib.Path, default=[],
                        help='List of cube files to load as molecules with fields')
    parser.add_argument('--cube-field', nargs='*', type=pathlib.Path, default=[],
                        help='List of cube files to load as scalar fields only')

    # Define mutually exclusive group for the three modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('-i', '--interactive', action='store_true',
                            help='Start the GUI in interactive mode')
    mode_group.add_argument('-r', '--render', action='store_true',
                            help='Render the scene with PyVista viewer')
    mode_group.add_argument('-s', '--screenshot', type=pathlib.Path,
                            help='Save a screenshot to the specified file path')

    args = parser.parse_args()

    scene_manager = SceneManager()
    for xyz_file in args.xyz:
        scene_manager.load_xyz(xyz_file)

    for cube_file in args.cube_mol:
        scene_manager.load_molecule_from_cube(cube_file)

    for cube_file in args.cube_field:
        scene_manager.load_scalar_field_from_cube(cube_file)

    if args.interactive:
        # Mode 1: Full PyQt GUI application
        setup_qt_environment()
        app = QApplication(sys.argv)
        window = ChemVistaApp(scene_manager)
        sys.exit(app.exec_())
    elif args.screenshot:
        # Mode 3: Save a screenshot to the specified file
        plotter = scene_manager.render(off_screen=True)
        plotter.screenshot(str(args.screenshot))
        print(f"Screenshot saved to: {args.screenshot}")
    else:
        # Mode 2: Just render with PyVista (default mode)
        plotter = scene_manager.render()
        plotter.show()


if __name__ == '__main__':
    main()
