"""setup.py install runs this file"""

import distutils.command.build_py as orig
import os
import sys
from windows_patch import LocalPatches
from setuptools import find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install


NAME = "blockchain_learning"
VERSION_REQUIREMENT = 3.7


with open("requirements.txt", "r") as f:
    REQUIREMENTS = f.read().splitlines()


with open("test-requirements.txt", "r") as f:
    TEST_REQUIREMENTS = f.read().splitlines()

class PreDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        check_python_version()
        super().run()


class PreInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        check_python_version()
        LocalPatches().run()
        super().run()


def package_files(package, directory):
    paths = []
    for (path, directories, filenames) in os.walk(os.path.join(package, directory)):
        for filename in filenames:
            paths.append(os.path.join(path, filename))
    return paths


def check_python_version():
    if float(sys.version[:3]) < VERSION_REQUIREMENT:
        print("Python version must be greater than or equal to {}".format(VERSION_REQUIREMENT))
        print("Python version:  {}".format(sys.version))
        print("exiting")
        sys.exit(0)


if __name__ == "__main__":

    setup(
        name=NAME,
        version="1.0.0",
        maintainer="Matthew Thomas-Carcamo",
        maintainer_email="matthew.thomascarcamo@gmail.com",
        description="Blockchain Learning",
        url="git@github.com:mthomascarcamo/blockchain-learning.git",
        package_dir={"": NAME},
        packages=find_packages(NAME, exclude=["tests*"]),
        python_requires=">={}".format(VERSION_REQUIREMENT),
        install_requires=REQUIREMENTS + TEST_REQUIREMENTS,
        package_data={NAME: package_files(NAME, ".")},
        cmdclass={
            "build_py": orig.build_py,
            'develop': PreDevelopCommand,
            'install': PreInstallCommand,
            },
        entry_points={
            "console_scripts": []
        }
    )