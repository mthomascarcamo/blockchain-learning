const PRICE_FIXED_DIGITS = 4
const DEFAULT_SURROUNDING_TICKS = 300
const TICKS_PER_GROUP = 1

const lodash = require('lodash')
const { Token } = require('@uniswap/sdk-core');
const { TickMath, tickToPrice } = require('@uniswap/v3-sdk')
const JSBI = require('jsbi');
const gql = require('graphql-tag');
const ApolloClient = require('apollo-boost').ApolloClient;
const fetch = require('cross-fetch/polyfill').fetch;
const createHttpLink = require('apollo-link-http').createHttpLink;
const InMemoryCache = require('apollo-cache-inmemory').InMemoryCache;


const FEE_TIER_TO_TICK_SPACING = (feeTier) => {
    switch (feeTier) {
        case '10000':
            return 200
        case '3000':
            return 60
        case '500':
            return 10
        default:
            throw Error(`Tick spacing for fee tier ${feeTier} undefined.`)
    }
}


var client = new ApolloClient({
    link: createHttpLink({
        uri: 'https://api.thegraph.com/subgraphs/name/ianlapham/uniswap-v3-testing',
        fetch: fetch
    }),
    queryDeduplication: false,
    cache: new InMemoryCache(),
    defaultOptions: {
        watchQuery: {
            fetchPolicy: 'cache-and-network',
        },
    },
})


const fetchInitializedTicks = async (
    poolAddress,
) => {
    const tickQuery = gql`
      query surroundingTicks(
        $poolAddress: String!
        $skip: Int!
      ) {
        ticks(
          first: 1000
          skip: $skip
          where: { poolAddress: $poolAddress }
        ) {
          tickIdx
          liquidityGross
          liquidityNet
          price0
          price1
        }
      }
    `

    let surroundingTicks = []
    let surroundingTicksResult = []
    let skip = 0
    do {
        const { data, error, loading } = await client.query({
            query: tickQuery,
            fetchPolicy: 'network-only',
            variables: {
                poolAddress,
                skip,
            },
        })

        // console.log({ data, error, loading }, 'Result. Skip: ' + skip)

        if (loading) {
            continue
        }

        if (error) {
            return { error: Boolean(error), loading, ticks: surroundingTicksResult }
        }

        surroundingTicks = data.ticks
        surroundingTicksResult = surroundingTicksResult.concat(surroundingTicks)
        skip += 1000
    } while (surroundingTicks.length > 0)

    return { ticks: surroundingTicksResult, loading: false, error: false }
}

async function fetchTicksSurroundingPrice(poolAddress,
    numSurroundingTicks) {
    const poolQuery = gql`
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
    `
    const { data: poolResult, error, loading } = await client.query({
        query: poolQuery,
        variables: {
            poolAddress,
        },
    })

    if (loading || error || !poolResult) {
        return {
            loading,
            error: Boolean(error),
            data: undefined,
        }
    }

    const {
        pool: {
            tick: poolCurrentTick,
            feeTier,
            liquidity,
            token0: { id: token0Address, decimals: token0Decimals },
            token1: { id: token1Address, decimals: token1Decimals },
        },
    } = poolResult
    const poolCurrentTickIdx = parseInt(poolCurrentTick)
    const tickSpacing = FEE_TIER_TO_TICK_SPACING(feeTier)

    // The pools current tick isn't necessarily a tick that can actually be initialized.
    // Find the nearest valid tick given the tick spacing.
    const activeTickIdx = Math.floor(poolCurrentTickIdx / tickSpacing) * tickSpacing

    const initializedTicksResult = await fetchInitializedTicks(poolAddress)
    if (initializedTicksResult.error || initializedTicksResult.loading) {
        return {
            error: initializedTicksResult.error,
            loading: initializedTicksResult.loading,
        }
    }

    const { ticks: initializedTicks } = initializedTicksResult

    const tickIdxToInitializedTick = lodash.keyBy(initializedTicks, 'tickIdx')

    const token0 = new Token(1, token0Address, parseInt(token0Decimals))
    const token1 = new Token(1, token1Address, parseInt(token1Decimals))

    // console.log({ activeTickIdx, poolCurrentTickIdx }, 'Active ticks')

    // If the pool's tick is MIN_TICK (-887272), then when we find the closest
    // initializable tick to its left, the value would be smaller than MIN_TICK.
    // In this case we must ensure that the prices shown never go below/above.
    // what actual possible from the protocol.
    let activeTickIdxForPrice = activeTickIdx
    if (activeTickIdxForPrice < TickMath.MIN_TICK) {
        activeTickIdxForPrice = TickMath.MIN_TICK
    }
    if (activeTickIdxForPrice > TickMath.MAX_TICK) {
        activeTickIdxForPrice = TickMath.MAX_TICK
    }

    const activeTickProcessed = {
        liquidityActive: JSBI.BigInt(liquidity),
        tickIdx: activeTickIdx,
        liquidityNet: JSBI.BigInt(0),
        price0: tickToPrice(token0, token1, activeTickIdxForPrice).toFixed(PRICE_FIXED_DIGITS),
        price1: tickToPrice(token1, token0, activeTickIdxForPrice).toFixed(PRICE_FIXED_DIGITS),
        liquidityGross: JSBI.BigInt(0),
    }

    // If our active tick happens to be initialized (i.e. there is a position that starts or
    // ends at that tick), ensure we set the gross and net.
    // correctly.
    const activeTick = tickIdxToInitializedTick[activeTickIdx]
    if (activeTick) {
        activeTickProcessed.liquidityGross = JSBI.BigInt(activeTick.liquidityGross)
        activeTickProcessed.liquidityNet = JSBI.BigInt(activeTick.liquidityNet)
    }

    // Direction = {
    //     'ASC'=0,
    //     'DESC'=1,
    // }

    // Computes the numSurroundingTicks above or below the active tick.
    const computeSurroundingTicks = (
        activeTickProcessed,
        tickSpacing,
        numSurroundingTicks,
        direction
    ) => {
        let previousTickProcessed = {
            ...activeTickProcessed,
        }

        // Iterate outwards (either up or down depending on 'Direction') from the active tick,
        // building active liquidity for every tick.
        let processedTicks = []
        for (let i = 0; i < numSurroundingTicks; i++) {
            const currentTickIdx =
                direction == 0
                    ? previousTickProcessed.tickIdx + tickSpacing
                    : previousTickProcessed.tickIdx - tickSpacing

            if (currentTickIdx < TickMath.MIN_TICK || currentTickIdx > TickMath.MAX_TICK) {
                break
            }

            const currentTickProcessed = {
                liquidityActive: previousTickProcessed.liquidityActive,
                tickIdx: currentTickIdx,
                liquidityNet: JSBI.BigInt(0),
                price0: tickToPrice(token0, token1, currentTickIdx).toFixed(PRICE_FIXED_DIGITS),
                price1: tickToPrice(token1, token0, currentTickIdx).toFixed(PRICE_FIXED_DIGITS),
                liquidityGross: JSBI.BigInt(0),
            }

            // Check if there is an initialized tick at our current tick.
            // If so copy the gross and net liquidity from the initialized tick.
            const currentInitializedTick = tickIdxToInitializedTick[currentTickIdx.toString()]
            if (currentInitializedTick) {
                currentTickProcessed.liquidityGross = JSBI.BigInt(currentInitializedTick.liquidityGross)
                currentTickProcessed.liquidityNet = JSBI.BigInt(currentInitializedTick.liquidityNet)
            }

            // Update the active liquidity.
            // If we are iterating ascending and we found an initialized tick we immediately apply
            // it to the current processed tick we are building.
            // If we are iterating descending, we don't want to apply the net liquidity until the following tick.
            if (direction == 0 && currentInitializedTick) {
                currentTickProcessed.liquidityActive = JSBI.add(
                    previousTickProcessed.liquidityActive,
                    JSBI.BigInt(currentInitializedTick.liquidityNet)
                )
            } else if (direction == 1 && JSBI.notEqual(previousTickProcessed.liquidityNet, JSBI.BigInt(0))) {
                // We are iterating descending, so look at the previous tick and apply any net liquidity.
                currentTickProcessed.liquidityActive = JSBI.subtract(
                    previousTickProcessed.liquidityActive,
                    previousTickProcessed.liquidityNet
                )
            }
            processedTicks.push(currentTickProcessed)
            previousTickProcessed = currentTickProcessed
        }

        if (direction == 1) {
            processedTicks = processedTicks.reverse()
        }

        return processedTicks
    }

    const subsequentTicks = computeSurroundingTicks(
        activeTickProcessed,
        tickSpacing,
        numSurroundingTicks, // 300
        0
    )

    const previousTicks = computeSurroundingTicks(
        activeTickProcessed,
        tickSpacing,
        numSurroundingTicks, // 300
        1
    )

    const ticksProcessed = previousTicks.concat(activeTickProcessed).concat(subsequentTicks)

    return {
        data: {
            ticksProcessed,
            feeTier,
            tickSpacing,
            activeTickIdx,
        },
    }
}

async function formattedData(poolTickData) {
    if (poolTickData) {
        let currentGroup = 1
        let currentEntry = {
            index: 0,
            isCurrent: 0,
            activeLiquidity: 0,
            price0: 0,
            price1: 0,
        }

        var grouped = []
        for (i = 0; i < poolTickData.ticksProcessed.length; i++) {

            t = poolTickData.ticksProcessed[i]
            const active = t.tickIdx === poolTickData.activeTickIdx

            // check if need to update current entry
            if (i % TICKS_PER_GROUP === 0 && i !== 0) {
                currentGroup = currentGroup + 1
                grouped.push(currentEntry)
                currentEntry = {
                    index: currentEntry.index + 1,
                    activeLiquidity: 0,
                    isCurrent: 0,
                    price0: 0,
                    price1: 0,
                }
            }
            currentEntry.isCurrent = active ? parseFloat(t.liquidityActive.toString()) : 0
            currentEntry.activeLiquidity = active
                ? 0
                : currentEntry.activeLiquidity + parseFloat(t.liquidityActive.toString())
            currentEntry.price0 = currentEntry.price0 + parseFloat(t.price0)
            currentEntry.price1 = currentEntry.price1 + parseFloat(t.price1)

        }
        return grouped;
    }
    return undefined
}

async function fetchTicksFormattedDataFromPool(poolAddress) {
    var poolTickData = await fetchTicksSurroundingPrice(poolAddress, DEFAULT_SURROUNDING_TICKS);
    var formattedDatResult = await formattedData(poolTickData.data)
    return formattedDatResult;
}

async function main(){
    var result = await fetchTicksFormattedDataFromPool(process.argv[2]);
    console.log(JSON.stringify(result));
}

main()