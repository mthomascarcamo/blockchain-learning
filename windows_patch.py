import os
import subprocess
import sys


EDIT_MAP = []


class Patch:

    repo = None

    def dependencies(self):
        """Not Implemented"""
        return []

    def _init(self):
        """Not Implemented"""

    def execute_patches(self):
        """Not Implemented"""

    @property
    def exists(self):
        return os.path.exists(self.base)
    
    @property
    def patched(self):
        return self.exists and self.__class__.__name__ in EDIT_MAP
    
    @property
    def not_patched_this_sessoon(self):
        return self.exists and not self.patched

    @property
    def cloned(self):
        return os.path.exists(self.base + '/.git')

    def __init__(self):
        self.directory = os.path.join(os.getcwd(), '.dump/')
        self.base = self.directory
        if self.not_patched_this_sessoon:
            self.remove_git_repo()
        if not self.exists:
            os.mkdir(self.base)
        self._init()
  
    def run(self):
        if self.patched:
            return
        for dependency in self.dependencies():
            dependency.run()
        self.clone()
        self.execute_patches()
        EDIT_MAP.append(self.__class__.__name__)

    def _iter(self, data):
        if not self.trigger:
            raise ValueError('something went wrong')
        last_include = None
        for index, line in enumerate(data):
            if line.strip().startswith(self.trigger):
                self.trigger = None
                return data, index
        raise ValueError('something went wrong')

    def clone(self):
        if self.repo and not self.cloned:
            subprocess.check_output(f'git clone {self.repo} {self.base}'.split(' '))

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

    def remove_git_repo(self):
        subprocess.check_output('pip install git-python'.split(' '))
        import git 
        git.rmtree(self.base)


class Ethash(Patch):

    repo = 'git@github.com:ethereum/ethash.git'

    def _init(self):
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

    def dependencies(self):
        return [Ethash()]

    def _init(self):
        self.base = self.base + 'py-evm'
        self.setup = self.base + r'/setup.py'

    def execute_patches(self):
        self.patch(self.setup, self.patch_setup)
    
    def patch_setup(self, data):
        self.trigger = '"pyethash'
        data, last_include = self._iter(data)
        data.pop(last_include)
        return data

class EthBrownie(Patch):

    repo = "git@github.com:eth-brownie/brownie.git"

    def dependencies(self):
        return [Ethash()]

    def _init(self):
        self.base = self.base + 'brownie'
        self.requirements = self.base + r'/requirements.txt'

    def execute_patches(self):
        self.patch(self.requirements, self.patch_eth_hash)
        self.patch(self.requirements, self.patch_rlp)
        self.patch(self.requirements, self.patch_eth_account) # in response to patch_rlp
    
    def patch_eth_hash(self, data):
        self.trigger = 'eth-hash'
        data, last_include = self._iter(data)
        data.pop(last_include)
        return data

    def patch_rlp(self, data):
        """
        ERROR: Cannot install eth-brownie==1.13.1 and py-evm==0.3.0a20 because these package versions have conflicting dependencies.

        The conflict is caused by:
            eth-brownie 1.13.1 depends on rlp==1.2.0
        ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/user_guide/#fixing-conflicting-dependencies    py-evm 0.3.0a20 depends on rlp<3 and >=2
        """
        self.trigger = 'rlp'
        data, last_include = self._iter(data)
        data.pop(last_include)
        return data

    def patch_eth_account(self, data):
        """
        ERROR: Cannot install eth-brownie and py-evm==0.3.0a20 because these package versions have conflicting dependencies.

        The conflict is caused by:
            py-evm 0.3.0a20 depends on rlp<3 and >=2
        ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/user_guide/#fixing-conflicting-dependencies    eth-account 0.5.2 depends on rlp<2 and >=1.0.0
        """
        self.trigger = 'eth-account'
        data, last_include = self._iter(data)
        data.pop(last_include)
        return data


class Trinity:
    """Failed to build plyvel pyethash python-snappy"""

    def dependencies(self):
        return [PyEVM()]


class LocalPatches:

    repos = [PyEVM, EthBrownie]

    def run(self):

        self.cmd('pip install -r requirements.txt')

        if os.name != 'nt':
            return

        init_repos = []
        for repo in self.repos:
            repo_obj = repo()
            init_repos.append(repo_obj)
        
        for repo_obj in init_repos:
            repo_obj.run()
        
        self.cmd("pip install".split(" ") + [repo.base for repo in init_repos])

    def cmd(self, cmd):
        if isinstance(cmd, str):
            cmd  = cmd.split(' ')
        with open("setup.log", "wb") as f:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            for line in iter(process.stdout.readline, b""):
                sys.stdout.write(line.decode("utf-8"))
                f.write(line)
