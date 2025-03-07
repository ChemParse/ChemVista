import subprocess
import pathlib


def main():
    resources_dir = pathlib.Path(__file__).parent
    subprocess.run([
        'pyrcc5',
        str(resources_dir / 'icons.qrc'),
        '-o',
        str(resources_dir / 'icons_rc.py')
    ])


if __name__ == "__main__":
    main()
