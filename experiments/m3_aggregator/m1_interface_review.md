# M1 Interface Review for M3 Aggregator

Reviewed repo:
`https://github.com/CHCYLI/Decentralized_ETH_USD_oracle_AVS`

Dates: 2026-04-30 (initial), 2026-05-01 (re-audited at commit
`6824d94 First version, need testing`), 2026-05-02 (reviewed M1/M2
zip branch)

> **2026-05-01 update:** the 4/30 commit is *still* the only delta on
> top of the upstream template. Solidity has indeed been changed (see
> below), but the Go layer (operator / aggregator / challenger /
> avs_writer / contracts/bindings) is untouched, so nothing yet
> compiles end-to-end. A drop-in M3 patch staged for whenever bindings
> regenerate is in `integration_patch/`. See
> `integration_patch/INTEGRATION_NOTES.md` for the full
> what-changed / what-didn't / open-decisions write-up.

> **2026-05-02 update:** the M1/M2 zip now includes regenerated
> contract bindings and a real M2 operator path. `operator/operator.go`
> fetches Coinbase ETH/USD, scales to 8 decimals, and fills
> `EthUsdPrice`; `core/utils.go` hashes `(referenceTaskIndex,
> ethUsdPrice)`. Remaining blockers for M3 are `avs_writer.go`,
> `aggregator.go`, generated mocks/tests, and the BLS-vs-median
> protocol decision.

## What M1 Has Already Changed

The contract interface has moved away from the original squaring task:

```solidity
struct Task {
    bytes32 pricePair;
    uint8 priceDecimals;
    uint32 taskCreatedBlock;
    bytes quorumNumbers;
    uint32 quorumThresholdPercentage;
}

struct TaskResponse {
    uint32 referenceTaskIndex;
    uint256 ethUsdPrice;
}
```

This means M3 should use `EthUsdPrice` after Go bindings are regenerated,
not the older placeholder names `ReportedPrice`, `PriceMedian`, or
`PriceVariance`.

The current M1 contract uses 8 decimals:

```solidity
uint8 public constant ETH_USD_PRICE_DECIMALS = 8;
```

M3's offline code now uses 8 decimals to match this interface. The existing
Monte-Carlo percentage results are scale-invariant, so the conclusions remain
unchanged.

## Current Blocking Issue

The Solidity source has changed, but the checked-in Go binding is still stale.
It still contains:

```go
type IIncredibleSquaringTaskManagerTask struct {
    NumberToBeSquared *big.Int
    ...
}

type IIncredibleSquaringTaskManagerTaskResponse struct {
    ReferenceTaskIndex uint32
    NumberSquared *big.Int
}
```

Until M1 regenerates bindings with `make bindings`, M2/M3 code cannot compile
against the new `PricePair`, `PriceDecimals`, and `EthUsdPrice` fields.

## Protocol Issue to Resolve With M1/M2

The current EigenSDK BLS aggregation flow aggregates signatures over the same
`TaskResponse`. That worked for squaring because every honest operator signs
the exact same `numberSquared`.

For a price oracle, each operator may fetch a slightly different CEX price.
If operators sign different `ethUsdPrice` values, the existing BLS aggregation
service will not naturally produce one quorum signature for a single response.

So the team needs to choose one of these designs:

1. **Two-round median approval.**
   Operators first send individual price reports to the aggregator. The
   aggregator computes the median, then asks operators to sign the final median
   `TaskResponse{referenceTaskIndex, ethUsdPrice}`. This preserves the current
   on-chain BLS verification model but requires an extra round.

2. **Aggregator-trusted median for demo only.**
   Operators send individual prices to the aggregator, the aggregator submits
   the median as `ethUsdPrice`, and the demo treats the BLS path as liveness
   attestation rather than strict approval of the median. This is easier for a
   course demo but should be described honestly in the paper.

3. **Use identical deterministic price source.**
   All operators compute the same normalized ETH/USD price, allowing the
   existing BLS aggregator to work unchanged. This weakens the median-consensus
   story because there are no heterogeneous reports to take a median over.

For M3, option 1 is the cleanest protocol. Option 2 is the quickest demo path.

## Concrete M3 Updates Enabled Now

Once bindings are regenerated, M3 can update:

1. `NewAggregator` hash function:
   `numberSquared` becomes `ethUsdPrice`.
2. `sendNewTask`:
   remove the `numToSquare` argument, because M1's `createNewTask` no longer
   takes a number.
3. `ProcessSignedTaskResponse`:
   store `signedTaskResponse.TaskResponse.EthUsdPrice` in `priceQuotes`.
4. `sendAggregatedResponseToContract`:
   compute median from `priceQuotes[taskIndex]` and submit
   `TaskResponse{ReferenceTaskIndex: taskIdx, EthUsdPrice: medianPrice}`.

If the team chooses option 1, this final submission must happen after operators
sign the median response, not immediately after collecting individual reports.
