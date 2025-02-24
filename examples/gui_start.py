import sys
from PyQt5.QtWidgets import QApplication
from chemvista import ChemVistaApp
import pathlib

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load default test file for demonstration
    test_cube = pathlib.Path(__file__).parent.parent / \
        'tests' / 'data' / 'C2H4.eldens.cube'

    window = ChemVistaApp(init_files={
        'cube_mol_files': [test_cube]
    })
    sys.exit(app.exec_())
