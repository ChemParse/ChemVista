from setuptools import setup, find_packages
from distutils.core import Command
import subprocess


class CompileResourcesCommand(Command):
    description = 'Compile Qt resources'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        subprocess.run([
            'pyrcc5',
            'chemvista/resources/icons.qrc',
            '-o',
            'chemvista/resources/icons_rc.py'
        ])


setup(
    name="chemvista",
    version="0.1.0",
    packages=find_packages(),
    cmdclass={
        'compile_resources': CompileResourcesCommand,
    },
    package_data={
        'chemvista.resources': ['*.png', '*.qrc'],
    },
)
