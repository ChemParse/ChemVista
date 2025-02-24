import argparse
import pathlib
from typing import Dict, List

import sys
from PyQt5.QtWidgets import QApplication
from chemvista import ChemVistaApp
import pathlib


def create_init_dict(xyz_files: List[pathlib.Path],
                     cube_mol_files: List[pathlib.Path],
                     cube_field_files: List[pathlib.Path]) -> Dict[str, List[pathlib.Path]]:
    """Create initialization dictionary from file lists"""
    return {
        'xyz_files': xyz_files,
        'cube_mol_files': cube_mol_files,
        'cube_field_files': cube_field_files
    }


def main():
    parser = argparse.ArgumentParser(
        description='ChemVista - Chemical Visualization Tool')

    parser.add_argument('--xyz', nargs='*', type=pathlib.Path, default=[],
                        help='List of XYZ files to load')
    parser.add_argument('--cube-mol', nargs='*', type=pathlib.Path, default=[],
                        help='List of cube files to load as molecules with fields')
    parser.add_argument('--cube-field', nargs='*', type=pathlib.Path, default=[],
                        help='List of cube files to load as scalar fields only')

    args = parser.parse_args()

    init_files = create_init_dict(args.xyz, args.cube_mol, args.cube_field)

    app = QApplication(sys.argv)

    window = ChemVistaApp(init_files=init_files)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
