import subprocess


def generate_icons():
    subprocess.run(["pyrcc5", "-o", "chemvista/gui/resources/icons_rc.py",
                   "chemvista/gui/resources/icons.qrc"], check=True)
