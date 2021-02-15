import os
import subprocess
import sys


EDIT_MAP = set()


class Patch:

    repo = None
    logfile = 'setup.log'

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
    def not_patched_this_session(self):
        return self.exists and self.__class__.__name__ not in EDIT_MAP

    @property
    def cloned(self):
        return os.path.exists(self.base + '/.git')

    def __init__(self):
        self.directory = os.path.join(os.getcwd(), '.dump/')
        self.base = self.directory
        if self.not_patched_this_session:
            self.remove_git_repo()
        if not self.exists:
            os.mkdir(self.base)
        self.base = self.base + self.repo.split('/')[-1][:-len('.git')]
        self._init()

    def run(self):
        if self.patched:
            return
        for dependency in self.dependencies():
            dependency.run()
        self.clone()
        self.execute_patches()
        EDIT_MAP.add(self.__class__.__name__)
        self.cmd(f"pip install {self.base}")

    def cmd(self, cmd):
        if isinstance(cmd, str):
            cmd  = cmd.split(' ')
        with open(self.logfile, "wb") as f:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            for line in iter(process.stdout.readline, b""):
                sys.stdout.write(line.decode("utf-8"))
                f.write(line)

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
            self.cmd(f'git clone {self.repo} {self.base}')

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
        self.cmd('pip install git-python')
        import git 
        git.rmtree(self.base)


class Ethash(Patch):

    repo = 'git@github.com:ethereum/ethash.git'

    def _init(self):
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


class EthBrownie(Patch):

    repo = "git@github.com:eth-brownie/brownie.git"

    def dependencies(self):
        return [Ethash()]

    def _init(self):
        self.requirements = self.base + r'/requirements.txt'

    def execute_patches(self):
        self.patch(self.requirements, self.patch_eth_hash)
        self.patch(self.requirements, self.patch_rlp)
        self.patch(self.requirements, self.patch_eth_account)    # in response to patch_rlp

        # ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
        # This behaviour is the source of the following dependency conflicts.
        # ipython 7.9.0 requires prompt-toolkit<2.1.0,>=2.0.0, but you have prompt-toolkit 3.0.8 which is incompatible.
        self.patch(self.requirements, self.patch_prompt_toolkit)
        self.patch(self.requirements, self.patch_pygments)
        self.patch(self.requirements, self.patch_web3)

    def patch_prompt_toolkit(self, data):
        self.trigger = 'prompt-toolkit'
        data, last_include = self._iter(data)
        data.pop(last_include)
        data += ['prompt-toolkit']
        return data

    def patch_web3(self, data):
        """trinity 0.1.0a36 requires web3<6,>=5.12.1, but you have web3 5.11.1 which is incompatible."""
        self.trigger = 'web3'
        data, last_include = self._iter(data)
        data.pop(last_include)
        data += ['web3<6,>=5.12.1']
        return data

    def patch_pygments(self, data):
        self.trigger = 'pygments'
        data, last_include = self._iter(data)
        data.pop(last_include)
        data += ['pygments']
        return data
    
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


class PyEVM(Patch):

    repo = "git@github.com:ethereum/py-evm.git"

    def dependencies(self):
        """It's actually Ethash that's a dep; trying to be more serial"""
        return [EthBrownie()]

    def _init(self):
        self.setup = self.base + r'/setup.py'

    def execute_patches(self):
        self.patch(self.setup, self.patch_setup)
    
    def patch_setup(self, data):
        self.trigger = '"pyethash'
        data, last_include = self._iter(data)
        data.pop(last_include)
        return data


class Trinity(Patch):
    """Failed to build plyvel pyethash python-snappy"""

    repo = "git@github.com:ethereum/trinity.git"

    def _init(self):
        self.setup = self.base + r'/setup.py'

    def dependencies(self):
        return [PyEVM()]

    def execute_patches(self):
        self.patch(self.setup, self.patch_plyvel)
        self.patch(self.setup, self.patch_python_snappy)
        self.patch(self.setup, self.patch_ipython)

    def patch_ipython(self, data):
        self.trigger = '"ipython'
        data, last_include = self._iter(data)
        data.pop(last_include)
        self.cmd('pip install ipython')
        return data        
    
    def patch_plyvel(self, data):
        self.trigger = '"plyvel'
        data, last_include = self._iter(data)
        data.pop(last_include)
        self.cmd('pip install plyvel-win32')
        return data

    def patch_python_snappy(self, data):
        self.trigger = '"python-snappy'
        data, last_include = self._iter(data)
        data.pop(last_include)
        self.cmd('pip install python_snappy-0.6.0-cp37-cp37m-win_amd64.whl')
        return data


class LocalPatches(Patch):

    def __init__(self):
        self.repos = [Trinity]

    def run(self):

        self.cmd('pip install -r requirements.txt')

        if os.name != 'nt':
            return

        for repo in self.repos:
            repo_obj = repo()
            repo_obj.run()
