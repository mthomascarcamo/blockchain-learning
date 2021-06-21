import os
import math
import json
import subprocess
from datetime import datetime, timedelta, timezone
from threading import Thread
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class UniV3SubgraphClient:

    FACTORY_ADDRESS = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
    _url = "https://api.thegraph.com/subgraphs/name/ianlapham/uniswap-v3-alt"

    def query(self, query, variables=None, operation_name=None):
        """Make graphql query to subgraph"""
        params = {'query': query}
        if variables:
            params = {'query': query, 'variables': variables}
        if variables and operation_name:
            params = {'query': query, 'operationName': operation_name, 'variables': variables}
        response = requests.post(self._url, json=params)
        response.raise_for_status()
        return response.json()


class UniV3Data(UniV3SubgraphClient):


    @property
    def factory(self):
        return self.get_factory()

    @property
    def daily_uniswap_data(self):
        return self.get_daily_uniswap_data()
    
    @property
    def daily_pool_data(self):
        return self.get_daily_pool_data()
    
    @property
    def pools(self):
        return self.get_pools()

    @property
    def block_number(self):
        return self.get_block_number()

    def get_block_number(self):
        raise NotImplementedError()

    def get_factory(self):
        """Get factory data."""
        query = """
        query factory($id: String!){
          factory(id: $id) {
            id
            poolCount
            txCount
            totalVolumeUSD
            totalValueLockedUSD
          }
        }
        """
        variables = {"id": self.FACTORY_ADDRESS}
        return self.query(query, variables)['data']['factory']

    def get_daily_uniswap_data(self):
        """Get aggregated daily data for uniswap v3."""
        query = """
        {
          uniswapDayDatas(
            first: 1000
            orderBy: date
            orderDirection: asc
          ) {
            id
            date
            volumeUSD
            tvlUSD
            txCount
          }
        }
        """

        return self.query(query)['data']['uniswapDayDatas']

    def get_daily_pool_data(self):
        """Get daily data for pools."""

        query = """
        query allDailyPoolData($date: Int!, $skip: Int!){
          poolDayDatas(
            first: 1000
            skip: $skip
            where: { date: $date }
            orderBy: volumeUSD
            orderDirection: desc
          ){
            id
            date
            pool{
              id
              token0{symbol}
              token1{symbol}
            }
            tvlUSD
            volumeUSD
            txCount
          }
        }
        """

        n_skips = int(self.factory['poolCount']) // 1000 + 1
        # Loop through days
        daily_pool_data = []
        for day in self.daily_uniswap_data:
            for i in range(n_skips):
                print(day['date'])
                variables = {"date": day['date'], "skip": i * 1000}
                daily_pool_data.extend((self.query(query, variables))['data']['poolDayDatas'])
        return daily_pool_data

    def get_pools(self):
        """Get latest factory data."""
        query = """
        query allPools($skip: Int!) {
          pools(
            first: 1000
            skip: $skip
            orderBy: volumeUSD
            orderDirection: desc
          ){
            id
            token0{
              symbol
            }
            token1{
              symbol
            }
            volumeUSD
          }
        }
        """

        n_skips = int(self.factory['poolCount']) // 1000 + 1

        pools = []
        for i in range(n_skips):
            variables = {'skip': i * 1000}
            pools.extend(self.query(query, variables)['data']['pools'])
        return pools

    def get_liquidity(self):
        """Get factory data."""
        variables = {}
        query = """
        query pools {
            pools(
                where: {id_in: ["_all_pools"]}
                block: {number: _block_number}
                orderBy: totalValueLockedUSD
                orderDirection: desc
            ) {
                id
                feeTier
                liquidity
                sqrtPrice
                tick
                token0 {
                    id
                    symbol
                    name
                    decimals
                    derivedETH
                    __typename
                    }
                token1 {
                    id
                    symbol
                    name
                    decimals
                    derivedETH
                    __typename
                    }
                token0Price
                token1Price
                volumeUSD
                txCount
                totalValueLockedToken0
                totalValueLockedToken1
                totalValueLockedUSD
                __typename
            }
        }"""
        query = query.replace('_all_pools','","'.join([pool['id'] for pool in self.pools]))
        query = query.replace('_block_number', str(self.block_number))
        return self.query(query, variables)['data']['pools']

    def get_historical_pool_prices(self, pool_address, time_delta):
        query = """
            query poolPrices($id: String!, $timestamp_start: Int!){
                pool(
                    id: $id
                ){
                    swaps(
                        first: 1000
                        orderBy: timestamp
                        orderDirection: asc
                        where: { timestamp_gte: $timestamp_start }
                    ){
                        id
                        timestamp
                        amount0
                        amount1
                    }
                }
            }
        """
        variables = {
            'id': pool_address,
            "timestamp_start": int((datetime.utcnow() - timedelta(time_delta)).replace(
                tzinfo=timezone.utc).timestamp())
        }
        has_data = True
        all_swaps = []
        while has_data:
            swaps = self.query(query, variables)['data']['pool']['swaps']

            all_swaps.extend(swaps)
            timestamps = set([int(swap['timestamp']) for swap in swaps])
            variables['timestamp_start'] = max(timestamps)

            if len(swaps) < 1000:
                has_data = False

        df_swaps = pd.DataFrame(all_swaps, dtype=np.float64)
        df_swaps.timestamp = df_swaps.timestamp.astype(np.int64)
        df_swaps.drop_duplicates(inplace=True)
        df_swaps['priceInToken1'] = abs(df_swaps.amount1 / df_swaps.amount0)
        data = df_swaps.to_dict('records')

        return data

    def uniswap_data(self):
        """Current TVL, volume, transaction count."""
        factory = self.factory
        data = {
            'totalValueLockedUSD': factory['totalValueLockedUSD'],
            'totalVolumeUSD': factory['totalVolumeUSD'],
            'txCount': factory['txCount']
        }
        return data

    def volume_pie_chart_data(self):
        """Data for pie chart of pool volumes"""
        pools = self.pools

        volume = [float(pool['volumeUSD']) for pool in pools]
        labels = [f"{pool['token0']['symbol']}-{pool['token1']['symbol']}" for pool in pools]

        data = {
            "datasets": [{
                "data": volume
            }],
            "labels": labels
        }

        return data

    def daily_volume_by_pair(self):
        """Daily volume by pair"""
        data = [
            {
                'pair': f"{pool_day['pool']['token0']['symbol']}-{pool_day['pool']['token1']['symbol']}",
                'date': datetime.utcfromtimestamp(pool_day['date']).isoformat(),
                'volumeUSD': pool_day['volumeUSD']
            }
            for pool_day in self.daily_pool_data if pool_day['volumeUSD'] != '0'
        ]

        return data

    def cumulative_trade_volume(self):
        """Daily cumulative trade volume."""
        # This assumes data is ordered already
        cumulative = []
        cumulativeVolumeUSD = 0
        for uniswap_day in self.daily_uniswap_data:
            cumulativeVolumeUSD += float(uniswap_day['volumeUSD'])
            cumulative.append(
                {
                    "date": datetime.utcfromtimestamp(uniswap_day['date']).isoformat(),
                    "cumulativeVolumeUSD": cumulativeVolumeUSD
                }
            )

        return cumulative


class UniV3DataSinglePool(UniV3Data):

    @property
    def pools(self):

        if not hasattr(self, 'token_pair'):
            return super().pools

        for pool in self.get_pools():
            if pool['token0']['symbol'] not in self.token_pair:
                continue
            if pool['token1']['symbol'] not in self.token_pair:
                continue
            return [pool]

        raise ValueError('pool not found')


class EtherumUSDCPool(UniV3DataSinglePool):

    token_pair = 'USDC', 'WETH'
    logger = print
    USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
    WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
    POOL = '0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8'

    def get_block_number(self):
        return 1266147

    def get_historical_pool_prices(self, pool_address, time_delta):
        if self.pool_address == pool_address:
            return super().get_historical_pool_prices(pool_address, time_delta)
        self.logger(f'overriding {pool_address} with {self.pool_address}')
        return super().get_historical_pool_prices(self.pool_address, time_delta)

    @property
    def pool_address(self):
        if hasattr(self, '_pool_address'):
            return self._pool_address
        self._pool_address = self.pools[0]['id']
        return self._pool_address

    @property
    def surrounding_ticks(self):
        return self.get_surrounding_ticks()

    def get_surrounding_ticks(self, skip=0):
        """Get Surrounding Ticks"""
        variables = {
            "poolAddress": self.pool_address,
            "skip": skip
            }
        query = """
        query surroundingTicks(
            $poolAddress: String!,
            $skip: Int!
            ) {
                ticks(
                    first: 1000
                    skip: $skip
                    where: {poolAddress: $poolAddress}
                    ) {
                        tickIdx
                        liquidityGross
                        liquidityNet
                        price0
                        price1
                    }
                }
        """
        return self.query(query, variables, operation_name='surroundingTicks')['data']['ticks']

    def fetchInitializedTicks(self, skip=0, surroundingTicksResult=None):

        if not surroundingTicksResult:
            surroundingTicksResult = [] 
        surroundingTicks = self.get_surrounding_ticks(skip)
        if surroundingTicks:
            surroundingTicksResult += surroundingTicks
            return self.fetchInitializedTicks(skip + 1000, surroundingTicksResult)

        return surroundingTicksResult
    
    def fetchTicksSurroundingPrice(self):
        variables = {"poolAddress": self.pool_address}
        query = """
        query pool($poolAddress: String!) {
            pool(id: $poolAddress) {
                tick
                token0 {
                    symbol
                    id
                    decimals
                    }
                token1 {
                    symbol
                    id
                    decimals
                    }
                feeTier
                sqrtPrice
                liquidity
                }
            }
        """
        return self.query(query, variables, operation_name='pool')['data']['pool']


class EtherumUSDCAnalysis(EtherumUSDCPool):
    """
    TODO:
        https://github.com/Uniswap/uniswap-v3-sdk/blob/12f3b7033bd70210a4f117b477cdaec027a436f6/src/utils/priceTickConversions.test.ts
    https://github.com/yossigruner/uniswapv3_liquidity/blob/18c3f8378f8b6c08b28bac4f4507e0cc4c93fee5/liqudity.js#L16
    """
    FEE_TIER_TO_TICK_SPACING = {
        '10000': 200,
        '3000': 60,
        '500': 10
        }
    
    def start_node(self):
        subprocess.check_output('npm install @uniswap/v3-sdk @uniswap/sdk-core'.split(' '))
    
    def activeTickIdx(self, poolCurrentTickIdx, feeTier):
        return math.floor(poolCurrentTickIdx / self.FEE_TIER_TO_TICK_SPACING[feeTier]) * self.FEE_TIER_TO_TICK_SPACING[feeTier]

    def dataframe(func):
        def wrapper(self, *args, **kwargs):
            return pd.DataFrame(func(self, *args, **kwargs))
        return wrapper

    def plot(func):
        def wrapper(self, *args, **kwargs):
            output = func(self, *args, **kwargs)
            output.plot()
            plt.show()
        return wrapper

    def threaded(func):
        def wrapper(self, *args, **kwargs):
            thread = Thread(func, args=(self) + args, kwargs=kwargs)
            thread.start()
        return wrapper

    @property
    @dataframe
    def surrounding_ticks(self):
        return super().surrounding_ticks

    @property
    @dataframe
    def initialized_ticks(self):
        return self.fetchInitializedTicks()
    
    @plot
    def analyze_net_liquidity(self):
        ticks = self.initialized_ticks
        ticks.liquidityNet = ticks.liquidityNet.astype(float)
        return ticks

    @plot
    def analyze_gross_liquidity(self):
        ticks = self.initialized_ticks
        ticks.liquidityGross = ticks.liquidityGross.astype(float)
        return ticks

    @dataframe
    def liquidity(self):
        # data = self.fetchTicksSurroundingPrice()
        # tick = self.get_fee_tier(data)
        # token0_id = data['token0']['id']
        # token1_id = data['token1']['id']
        # token0_decimals = data['token0']['decimals']
        # token1_decimals = data['token1']['decimals']
        # directory = os.path.join(os.path.dirname(__file__), 'usdc_price.js')
        directory = os.path.join(os.path.dirname(__file__), 'liquidity.js')
        # cmd = f'node {directory} {tick} {token0_id} {token1_id} {token0_decimals} {token1_decimals}'
        cmd = f'node {directory} {self.POOL}'
        output = subprocess.check_output(cmd.split(' ')).decode('utf-8')
        return json.loads(output)

    @plot
    def plot_liquidity(self):
        liq = self.liquidity()
        liq.activeLiquidity = liq.activeLiquidity.astype(float)
        liq.price1 = liq.price1.astype(float)
        liq.index = liq.price1
        return liq.activeLiquidity

    def get_fee_tier(self, data):
        poolCurrentTickIdx = int(data['tick'])
        tickSpacing = self.FEE_TIER_TO_TICK_SPACING[data['feeTier']]
        return math.floor(poolCurrentTickIdx / tickSpacing) * tickSpacing
