"""Qt utility functions for ChemVista GUI"""
import os
import glob


def setup_qt_environment():
    """Setup Qt environment variables to prevent common X11 and threading issues"""
    # Set Qt platform to xcb (X11) explicitly
    if 'QT_QPA_PLATFORM' not in os.environ:
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
    
    # Disable MIT-SHM to prevent X11 issues
    if 'QT_X11_NO_MITSHM' not in os.environ:
        os.environ['QT_X11_NO_MITSHM'] = '1'