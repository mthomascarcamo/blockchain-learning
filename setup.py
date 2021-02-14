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
EDIT_MAP = []


class Patch:

    repos = []
    repo = None

    def __init__(self):
        self.directory = os.path.join(os.getcwd(), '_dump/')
        self.base = self.directory
        if not os.path.exists(self.base):
            os.mkdir(self.base)

    def _iter(self, data):
        if not self.trigger:
            raise ValueError('something went wrong')
        last_include = None
        for index, line in enumerate(data):
            if line.strip().startswith(self.trigger):
                self.trigger = None
                return data, index
        raise ValueError('something went wrong')

    def run(self):
        self.add_repo()
        self.clone()
        self.execute_patches()

    def clone(self):
        print(self.repos)
        for repo in self.repos:
            subprocess.check_output(f'git clone {repo} {self.base}'.split(' '))

    def execute_patches(self):
        """Not Implemented"""

    def patch(self, filename, callback):
        data = self.read(filename).splitlines()
        data = callback(data)
        self.write(filename, '\n'.join(data))

    def read(self, filename):
        with open(filename, 'r') as file_:
            data = file_.read()
        return data
    
    def write(self, filename, data):
        with open(filename, 'w+') as file_:
            file_.write(data)
    
    def add_repo(self):
        if self.repo:
            self.repos += [self.repo]


class Ethash(Patch):

    repo = 'git@github.com:ethereum/ethash.git'

    def __init__(self):
        super().__init__()
        self.base = self.base + 'ethash'
        self.mmap_win32 = self.base + r'/src/libethash/mmap_win32.c'
        self.python_core = self.base + r'/src/python/core.c'
        self.trigger = None

    def execute_patches(self):
        self.patch(self.mmap_win32, self.patch_mmap_win32)
        self.patch(self.python_core, self.patch_python_core)

    def patch_mmap_win32(self, data):
        self.trigger = '#include'
        data, last_include = self._iter(data)
        data.insert(last_include + 1, '#pragma comment(lib, "Shell32.lib")')
        return data

    def patch_python_core(self, data):
        self.trigger = '#include <alloca.h>'
        data, last_include = self._iter(data)
        data[last_include] = '#if defined(_WIN32) || defined(WIN32)\n#include <malloc.h>\n#else\n#include <alloca.h>\n#endif'
        return data

class PyEVM(Patch):

    repo = "git@github.com:ethereum/py-evm.git"

    def __init__(self):
        super().__init__()
        print('tests')
        self.base = self.base + 'py-evm/'
        self.setup = self.base + r'setup.py'

    def execute_patches(self):
        self.patch(self.setup, self.patch_setup)
    
    def patch_setup(self, data):
        self.trigger = '"pyethash'
        data, last_include = self._iter(data)
        data.pop(last_include)
        return data

class RequirementsTXT(Patch):

    def __init__(self):
        super().__init__()
        self.base = os.path.join(os.getcwd(), "requirements.txt")

    def execute_patches(self):
        self.patch(self.base, self.add)
    
    def add(self, data):
        eth = Ethash().run()
        evm = PyEVM().run()
        data += [eth.base, evm.base]
        return data


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
        RequirementsTXT().run()
        try:
            if self.is_tox_env:
                with open("requirements.txt", "w") as reqs:
                    reqs.write("\n".join(REQUIREMENTS))
                with open("test-requirements.txt", "w") as treqs:
                    treqs.write("\n".join(TEST_REQUIREMENTS))

            for file_ in ["requirements.txt", "test-requirements.txt"]:
                cmd = [sys.executable] + "-m pip install -r {}".format(file_).split(" ")
                with open("setup.log", "wb") as f:
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                    for line in iter(process.stdout.readline, b""):
                        sys.stdout.write(line.decode("utf-8"))
                        f.write(line)
        finally:
            if self.is_tox_env:
                os.remove("requirements.txt")
                os.remove("test-requirements.txt")
        super().run()

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