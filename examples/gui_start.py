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
    test_cube = pathlib.Path(__file__).parent.parent / \
        'tests' / 'data' / 'C2H4.eldens.cube'

    logger.info(f"Loading test cube file: {test_cube}")

    # Create and show window
    window = ChemVistaApp(init_files={
        'cube_mol_files': [test_cube]
    })

    # Print scene tree structure after a short delay
    def print_scene_tree():
        if hasattr(window.scene_manager, 'log_tree_changes'):
            window.scene_manager.log_tree_changes(
                "Initial scene tree structure")
        else:
            logger.info("Current scene tree structure:")
            if hasattr(window.scene_manager, 'format_tree'):
                logger.info(window.scene_manager.format_tree())
            else:
                logger.info("<Tree display not available>")

    QTimer.singleShot(1000, print_scene_tree)

    # Keep application running
    sys.exit(app.exec_())
