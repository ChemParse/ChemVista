import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from chemvista import ChemVistaApp
import pathlib


def setup_console_logger():
    """Set up a basic console logger"""
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Add handler to logger if not already added
    if not logger.handlers:
        logger.addHandler(handler)

    # Set specific loggers' levels
    logging.getLogger("chemvista.scene").setLevel(logging.INFO)
    logging.getLogger("chemvista.ui.tree").setLevel(logging.INFO)

    return logger


if __name__ == "__main__":
    # Set up logging
    logger = setup_console_logger()
    logger.info("Starting ChemVista application")

    app = QApplication(sys.argv)

    # Load default test file for demonstration
    test_files_dir = pathlib.Path(__file__).parent.parent / 'tests' / 'data'
    test_cube = test_files_dir / 'C2H4.eldens.cube'
    test_molecule = test_files_dir / 'mpf_motor.xyz'
    test_trajectory = test_files_dir / 'mpf_motor_trajectory.xyz'

    logger.info(f"Loading test cube file: {test_cube}")
    logger.info(f"Loading test trajectory file: {test_trajectory}")

    # Create and show window
    window = ChemVistaApp(init_files={
        'cube_mol_files': [test_cube],
        'xyz_files': [test_molecule, test_trajectory]
    })

    # Keep application running
    sys.exit(app.exec_())
