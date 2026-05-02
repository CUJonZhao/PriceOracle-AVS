# M3 Integration Patch - Staged Against M1 Upstream

Date: 2026-05-01, updated 2026-05-02 after M1/M2 zip review.

This directory holds the M3 changes ready to drop into the upstream
`Decentralized_ETH_USD_oracle_AVS` repo after M1 regenerates the Go
bindings. The 2026-05-02 M1/M2 zip already has the new
`PricePair / PriceDecimals / EthUsdPrice` ABI, so this patch now also
includes the writer mock and key tests that were still using the old
squaring interface.

## What's in here

| File | Destination in upstream | Purpose |
|------|------------------------|---------|
| `aggregator.go.proposed` | `aggregator/aggregator.go` (replace) | New median-consensus aggregator targeting the `pricePair / priceDecimals / ethUsdPrice` ABI |
| `aggregator_test.go.proposed` | `aggregator/aggregator_test.go` (replace) | Updates aggregator unit tests from square tasks to ETH/USD price tasks |
| `rpc_server_test.go.proposed` | `aggregator/rpc_server_test.go` (replace) | Updates signed response tests to use `EthUsdPrice` and asserts quote stashing |
| `aggregator_chain_mock.go.proposed` | `aggregator/mocks/chain.go` (replace) | Updates aggregator helper mocks to emit ETH/USD price tasks |
| `avs_writer.go.proposed` | `core/chainio/avs_writer.go` (replace) | Uses `SendNewPriceTask`, drops the task payload arg, updates `RaiseChallenge` signature |
| `avs_writer_mock.go.proposed` | `core/chainio/mocks/avs_writer.go` (replace until mockgen is rerun) | Updates the generated mock to the new writer interface |
| `challenger.go.proposed` | `challenger/challenger.go` (replace) | M4 helper patch: compares submitted `EthUsdPrice` to a reference ETH/USD price and calls the new `RaiseChallenge(..., referenceEthUsdPrice, ...)` |
| `challenger_test.go.proposed` | `challenger/challenger_test.go` (replace) | Updates challenger tests for `EthUsdPrice` and the new reference-price challenge arg |
| `median.go` | `aggregator/median.go` (new) | Pure `Median / Variance / DetectOutliers` |
| `median_test.go` | `aggregator/median_test.go` (new) | Ten unit tests plus two benchmarks |
| `INTEGRATION_NOTES.md` | (read-only context) | Findings from the 5/1 audit plus open team decisions |
| `apply_patch.sh` | (run from upstream root) | Convenience copier |

## Current blockers

1. **M3 / integration**: production code and the most obvious tests now
   target the new price-oracle ABI, but the team should still rerun
   `mockgen` and `gofmt` in the upstream repo after applying this patch.
2. **M2**: operator now fetches Coinbase and fills `EthUsdPrice`, but
   all operators currently use the same Coinbase source. The paper's
   multi-CEX claim needs source selection such as `OPERATOR_PRICE_SOURCE`.
3. **Team**: must decide the BLS protocol (see `INTEGRATION_NOTES.md`
   section 3). M1's contract verifies signatures against the exact
   submitted `ethUsdPrice`, so heterogeneous operator prices need either
   a two-round median-signing flow or a contract/protocol adjustment.

The included challenger patch is intentionally simple: by default it
uses Coinbase as the independent reference, and it also supports
`CHALLENGER_REFERENCE_ETH_USD_PRICE=3152.47` for deterministic local
tests without network access.

## Apply to upstream

```bash
bash apply_patch.sh /path/to/Decentralized_ETH_USD_oracle_AVS
```

On Windows PowerShell:

```powershell
.\apply_patch.ps1 E:\path\to\Decentralized_ETH_USD_oracle_AVS
```

Then inside the upstream repo:

```bash
gofmt -w aggregator core/chainio challenger
go build ./...
go test ./aggregator/... ./challenger/...
```

I could not run those Go commands in this Codex Windows workspace
because `go` and `gofmt` are not installed here.
