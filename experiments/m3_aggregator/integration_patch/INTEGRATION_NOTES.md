# Integration Notes - M1/M2 Upstream Audit

Reviewed upstream repo `CHCYLI/Decentralized_ETH_USD_oracle_AVS` and
the `M1-M2Decentralized_ETH_USD_oracle_AVS-newbranch.zip` shared on
2026-05-02.

This memo records what changed in M1/M2, what this M3 patch covers, and
the remaining team decisions before the demo/paper story is fully
consistent.

---

## 1. M1 Contract / Binding Changes

M1 replaced the original squaring task with an ETH/USD oracle task:

| Item | Old | New |
|------|-----|-----|
| `Task` payload | `numberToBeSquared` | `pricePair`, `priceDecimals` |
| `TaskResponse` payload | `numberSquared` | `ethUsdPrice` |
| `createNewTask` | `createNewTask(num, qThr, qNums)` | `createNewTask(qThr, qNums)` |
| challenge input | recompute square | compare submitted ETH/USD price against `referenceEthUsdPrice` |
| tolerance | n/a | `priceDeviationToleranceBps`, default 100 bps = 1% |

The generated Go binding in the 2026-05-02 zip now exposes:

```go
type IIncredibleSquaringTaskManagerTask struct {
    PricePair                 [32]byte
    PriceDecimals             uint8
    TaskCreatedBlock          uint32
    QuorumNumbers             []byte
    QuorumThresholdPercentage uint32
}

type IIncredibleSquaringTaskManagerTaskResponse struct {
    ReferenceTaskIndex uint32
    EthUsdPrice        *big.Int
}
```

Important contract limitation: challenge/slashing is collective over
the submitted aggregate response. The contract does not know each
operator's individual price, so aggregator-side outlier detection is a
logging/reputation signal unless M1 adds a per-operator slash path.

---

## 2. M2 Operator Changes

M2 moved the operator onto the new ABI:

* Validates `PricePair == keccak256("ETH/USD")`.
* Fetches Coinbase `ETH-USD` ticker.
* Scales the decimal price by `task.PriceDecimals`, normally 8.
* Sends `TaskResponse{ReferenceTaskIndex, EthUsdPrice}`.
* Skips invalid tasks, failed API calls, bad JSON, invalid prices, and
  non-positive prices.
* Updated `core/utils.go` so the signed digest is
  `keccak256(abi.encode(uint32 referenceTaskIndex, uint256 ethUsdPrice))`.

Still open for M2/paper alignment: every operator currently uses the
same Coinbase source. If the final paper claims heterogeneous CEX
aggregation, M2 should add source selection such as
`OPERATOR_PRICE_SOURCE=coinbase|kraken|binance|okx`.

---

## 3. What This M3 Patch Covers

Files staged in this directory:

| File | Upstream destination | Status |
|------|----------------------|--------|
| `aggregator.go.proposed` | `aggregator/aggregator.go` | Sends price tasks, stores per-operator quotes, computes median/variance/outliers, submits `EthUsdPrice` |
| `rpc_server.go.proposed` | `aggregator/rpc_server.go` | Stashes each operator's `EthUsdPrice` before forwarding the BLS signature |
| `median.go` / `median_test.go` | `aggregator/` | Pure median, variance, and outlier helper logic |
| `avs_writer.go.proposed` | `core/chainio/avs_writer.go` | Updates `CreateNewTask` and `RaiseChallenge` wrappers for the new ABI |
| `avs_writer_mock.go.proposed` | `core/chainio/mocks/avs_writer.go` | Manual mock update until `mockgen` is rerun |
| `aggregator_chain_mock.go.proposed` | `aggregator/mocks/chain.go` | Updates helper mocks to emit ETH/USD tasks |
| `aggregator_test.go.proposed` | `aggregator/aggregator_test.go` | Updates send-task test to `SendNewPriceTask` |
| `rpc_server_test.go.proposed` | `aggregator/rpc_server_test.go` | Updates signed response test to `EthUsdPrice` |
| `challenger.go.proposed` | `challenger/challenger.go` | Adds reference ETH/USD price checking and new challenge arg |
| `challenger_test.go.proposed` | `challenger/challenger_test.go` | Updates basic challenger tests for `EthUsdPrice` |

Apply with:

```bash
bash apply_patch.sh /path/to/Decentralized_ETH_USD_oracle_AVS
```

Or on Windows PowerShell:

```powershell
.\apply_patch.ps1 E:\path\to\Decentralized_ETH_USD_oracle_AVS
```

Then run in the upstream repo:

```bash
gofmt -w aggregator core/chainio challenger
go build ./...
go test ./aggregator/... ./challenger/...
```

This Codex workspace does not have `go` or `gofmt` on PATH, so those
commands must be run by someone with a Go toolchain.

---

## 4. BLS Aggregation Decision

This is the main team-level issue.

The EigenSDK BLS aggregation service aggregates signatures over an
identical message digest. If operators fetch slightly different ETH/USD
prices and sign `(taskIndex, ownPrice)`, they sign different messages,
so no quorum forms for a true median response.

Viable paths:

| Path | Summary | Tradeoff |
|------|---------|----------|
| A. Two-round median signing | Operators first report prices; aggregator computes median; operators then BLS-sign the canonical median | Architecturally correct, but needs M2/operator RPC work |
| B. Single-round demo path | Current aggregator computes median but only submits it if the BLS quorum actually signed that value; otherwise submits the BLS-signed price and logs the mismatch | Keeps on-chain verification working, but true median consensus is not guaranteed |
| C. Deterministic source | All operators use an identical normalized source so they sign the same price | Simple demo, but weakens the heterogeneous median story |

M3 recommendation: use Path B for near-term demo stability, and clearly
state that Path A is the correct final architecture if the paper claims
robust heterogeneous-source median aggregation.

---

## 5. Tolerance Framing

There are two different tolerances:

* On-chain `priceDeviationToleranceBps`: default 1%, used by challenger
  to compare the submitted aggregate price against a reference price.
* Off-chain `tolerancePct`: default 5%, used by M3 to flag individual
  operator quotes around the median for logs/reputation.

Recommended paper framing: keep both and explain them separately.
The 1% value is the on-chain challenge threshold; the 5% value is the
off-chain operator outlier band.

---

## 6. Remaining Work

| # | Action | Owner |
|---|--------|-------|
| 1 | Apply this patch to the M1/M2 upstream branch | Jon |
| 2 | Run `gofmt`, `go build ./...`, and `go test ./aggregator/... ./challenger/...` | Jon / teammate with Go installed |
| 3 | Rerun `mockgen` and compare against the manual proposed mocks | Jon / teammate with Go installed |
| 4 | Decide Path A vs B for demo and paper | Whole team |
| 5 | Add multi-source operator selection if paper keeps heterogeneous CEX claim | M2 |
| 6 | If Path A is selected, add median-signing round between aggregator and operators | M2 + M3 |
