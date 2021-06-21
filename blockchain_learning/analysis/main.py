import os
import time
import json
import subprocess
from threading import Thread
import pandas as pd
import matplotlib.pyplot as plt
import cbpro


class _LiquidityAnalysis:

    POOL = NotImplemented
    PRODUCTS = NotImplemented
    # copied from https://github.com/yossigruner/uniswapv3_liquidity/
    filename = 'liquidity.js'
    _url = "wss://ws-feed.pro.coinbase.com"
    logger = print

    def __init__(self):
        self.wsClient = cbpro.WebsocketClient(
            url=self._url,
            products=self.PRODUCTS,
            channels=["ticker"]
            )
        self.__thread = True

    def get_liquidity(self, index='price1'):
        directory = os.path.join(os.path.dirname(__file__), self.filename)
        cmd = f'node {directory} {self.POOL}'
        output = subprocess.check_output(cmd.split(' ')).decode('utf-8')
        df = pd.DataFrame(json.loads(output))
        for column in df.columns:
            df[column] = df[column].astype(float)
        df.index = df[index].astype(float)
        return df.activeLiquidity

    def sleep(self, sleep):
        for _ in range(sleep):
            if self.__thread:
                time.sleep(1)

    def check_new_liquidity(self, sleep=60):

        def loop():
            liquidity = set(self.liquidity.to_dict().items())
            while self.__thread:
                self.logger('checking liquidity')
                self.sleep(sleep)
                new_liquidity = liquidity - set(self.get_liquidity().to_dict().items())
                if new_liquidity:
                    self.new_liquidity = new_liquidity
                    self.callback()
            self.logger('stopped loop')

        th = Thread(target=loop, args=())
        th.start()

    def callback(self):
        self.logger('liquidity has changed')
        df = pd.DataFrame(sorted(list(self.new_liquidity)))
        df.index = df[0]
        df[[1]].plot()
        plt.show()

    def stop(self):
        self.__thread = False

    @property
    def liquidity(self):
        if hasattr(self, '_liquidity'):
            return self._liquidity
        self._liquidity = self.get_liquidity()
        return self._liquidity


class WETHUSDCPool(_LiquidityAnalysis):
    PRODUCTS = "ETH-USD"
    POOL = '0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8'
