import subprocess


def generate_icons():
    subprocess.run(["pyrcc5", "-o", "chemvista/resources/icons_rc.py",
                   "chemvista/resources/icons.qrc"], check=True)
