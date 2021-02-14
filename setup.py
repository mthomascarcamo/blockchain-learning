"""setup.py install runs this file"""

import distutils.command.build_py as orig
import os
import subprocess
import sys

from setuptools import find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install


NAME = "blockchain-learning"
VERSION_REQUIREMENT = 3.7


with open("requirements.txt", "r") as f:
    REQUIREMENTS = f.read().splitlines()


with open("test-requirements.txt", "r") as f:
    TEST_REQUIREMENTS = f.read().splitlines()


class PreDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        check_python_version()
        develop.run(self)


class PreInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        check_python_version()
        try:
            if self.is_tox_env:
                with open("requirements.txt", "w") as reqs:
                    reqs.write("\n".join(REQUIREMENTS))
                with open("test-requirements.txt", "w") as treqs:
                    treqs.write("\n".join(TEST_REQUIREMENTS))

            for file_ in ["requirements.txt", "test-requirements.txt"]:
                cmd = [sys.executable] + "-m pip install -r {}".format(file_).split(" ")
                cmd += ['&&']
                cmd += [sys.executable] + '-m textblob.download_corpora'.split(' ')
                with open("setup.log", "wb") as f:
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                    for line in iter(process.stdout.readline, b""):
                        sys.stdout.write(line.decode("utf-8"))
                        f.write(line)
        finally:
            if self.is_tox_env:
                os.remove("requirements.txt")
                os.remove("test-requirements.txt")

        install.run(self)

    @staticmethod
    @property
    def is_tox_env():
        if not os.path.exists("requirements.txt"):
            return True
        if not os.path.exists("test-requirements.txt"):
            return True
        return False


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