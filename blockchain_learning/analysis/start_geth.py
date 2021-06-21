import os
import sys
import subprocess
from threading import Thread


class Setup:
    """https://geth.ethereum.org/docs/install-and-build/installing-geth"""

    signer = r'\\.\pipe\clef.ipc'
    chainid = {
        'mainnet': 1,
        'Ropsten': 3,
        'Rinkeby': 4,
        'Goerli': 5,
    }

    def run_cmd(self, cmd, new_shell=True, thread=False):

        if new_shell:
            os.system(f'start cmd /k {cmd}')
            return input('Press enter to continue: ')

        def run(stdout=False):
            if stdout:
                return subprocess.run(cmd.split(' '), stderr=sys.stderr, stdout=sys.stdout)
            return subprocess.run(cmd.split(' '))

        if not thread:
            return run()

        th = Thread(target=run, args=())
        th.start()

    def start_clef(self, chain):
        return self.run_cmd(f'clef --chainid {self.chainid[chain]}', new_shell=True)

    def start_geth(self, chain, syncmode='light'):
        return self.run_cmd(f'geth --{chain.lower()} --syncmode "{syncmode}" --http --signer={self.signer} --ws')
    
    def start_goerli(self):
        return self.run_chain('Goerli')

    def start_mainnet(self):
        return self.run_chain('mainnet')

    def start_ropsten(self):
        return self.run_chain('Ropsten')

    def start_rinkeby(self):
        return self.run_chain('Rinkeby')
    
    def run_chain(self, chain):
        self.start_clef(chain)
        self.start_geth(chain)


if __name__ == '__main__':
    Setup().start_goerli()
