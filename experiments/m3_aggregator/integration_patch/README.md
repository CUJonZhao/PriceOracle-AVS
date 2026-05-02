# M3 Integration Patch — Staged Against M1 Upstream

Date: 2026-05-01, updated 2026-05-02 after M1/M2 zip review.

This directory holds the M3 changes ready to drop into the upstream
`Decentralized_ETH_USD_oracle_AVS` repo *as soon as M1 regenerates the
Go bindings*. Until then the upstream tree won't compile against the
new contract ABI in any case, so we are staging here.

## What's in here

| File | Destination in upstream | Purpose |
|------|------------------------|---------|
| `aggregator.go.proposed` | `aggregator/aggregator.go` (replace) | New median-consensus aggregator targeting the `pricePair / priceDecimals / ethUsdPrice` ABI |
| `avs_writer.go.proposed` | `core/chainio/avs_writer.go` (replace) | Renames `SendNewTaskNumberToSquare` → `SendNewPriceTask`, drops the `numToSquare` arg, updates `RaiseChallenge` signature |
| `median.go` | `aggregator/median.go` (new) | Pure `Median / Variance / DetectOutliers` (already unit-tested in `experiments/m3_aggregator/median_test.go`) |
| `median_test.go` | `aggregator/median_test.go` (new) | Same 10 unit tests + 2 benchmarks |
| `INTEGRATION_NOTES.md` | (read-only context) | Findings from the 5/1 audit + open team decisions |
| `apply_patch.sh` | (run from upstream root) | Convenience copier |

## Why `.proposed` and not a real PR

Current blockers, listed by who owns them:

1. **M3 / tests**: the 5/2 zip has regenerated contract bindings, but
   `core/chainio/avs_writer.go`, `aggregator/aggregator.go`, and the
   generated `core/chainio/mocks/avs_writer.go` are still old. This
   patch updates the first two; mocks/tests still need regeneration or
   manual cleanup.
2. **M2**: operator now fetches Coinbase and fills `EthUsdPrice`, but
   all operators currently use the same Coinbase source. The paper's
   multi-CEX claim needs source selection such as `OPERATOR_PRICE_SOURCE`.
3. **Team**: must decide the BLS protocol (see `INTEGRATION_NOTES.md`
   §3). M1's contract requires every operator to sign `keccak(abi.encode(taskResponse))`
   for the *same* `ethUsdPrice`, which can't aggregate across
   heterogeneous CEX quotes without either a two-round protocol or
   relaxing on-chain verification. The proposed aggregator is written
   for the cleanest interpretation (single-round, aggregator-trusted
   median submission with BLS as a liveness attestation) but flagged.

Once those resolve, `bash apply_patch.sh` copies these files into the
right places and the team can `go build ./... && go test ./aggregator/...`.

## How to run unit tests right now (no upstream needed)

```bash
cd experiments/m3_aggregator
go test -v        # 10 tests, all green per 4/30 verify_median.py run
```
