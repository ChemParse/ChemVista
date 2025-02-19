import sys
from PyQt5.QtWidgets import QApplication
from chemvista import ChemVistaApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set debug=False to disable automatic loading
    window = ChemVistaApp(debug=True)
    sys.exit(app.exec_())
