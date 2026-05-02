# Integration Notes — M1/M2 Upstream Audit

Reviewed: `https://github.com/CHCYLI/Decentralized_ETH_USD_oracle_AVS`
at commit `6824d94 First version, need testing` (4/30, the only commit
on top of the original `incredible-squaring-avs` template).

Re-reviewed: `M1-M2Decentralized_ETH_USD_oracle_AVS-newbranch.zip`
provided on 2026-05-02.

This memo summarises what M1 has actually changed, what hasn't been
done yet, and the design questions that need a team answer before §V
of the paper can be locked.

---

## 1. What M1 changed (Solidity layer)

In `contracts/src/IIncredibleSquaringTaskManager.sol` and
`contracts/src/IncredibleSquaringTaskManager.sol`:

| Field / function | Before | After |
|-------------------|--------|-------|
| `Task.numberToBeSquared` | `uint256` | removed |
| `Task.pricePair` | — | `bytes32` (= `keccak256("ETH/USD")`) |
| `Task.priceDecimals` | — | `uint8` (= 8) |
| `TaskResponse.numberSquared` | `uint256` | replaced by `ethUsdPrice : uint256` (8 decimals) |
| `createNewTask(num, qThr, qNums)` | takes a number | now `createNewTask(qThr, qNums)` |
| `respondToTask` | checks square | now requires `ethUsdPrice > 0` |
| `raiseAndResolveChallenge` | per-operator squaring check | takes `referenceEthUsdPrice` and slashes *all signing operators* if `isPriceWithinTolerance(submitted, reference)` returns false |
| New constants | — | `BPS_DENOMINATOR = 10_000`, `DEFAULT_PRICE_DEVIATION_TOLERANCE_BPS = 100` (= **1%**), `WADS_TO_SLASH = 10%`, `ETH_USD_PRICE_PAIR_HASH`, `ETH_USD_PRICE_DECIMALS` |
| New helper | — | `isPriceWithinTolerance(submitted, reference)` ↔ uses `priceDeviationToleranceBps` |
| New admin fn | — | `setPriceDeviationToleranceBps` (`onlyOwner`) |

Notable design difference vs. our original M3 plan:
**slashing is collective on the aggregated response, not per-operator.**
The contract has no concept of "operator i reported X, slash i because
X is far from median." It only knows the aggregator's submitted
`ethUsdPrice` and a challenger's `referenceEthUsdPrice`; if the two
diverge by more than `priceDeviationToleranceBps`, every signing
operator is slashed `WADS_TO_SLASH` (10%).

---

## 2. What M1 has NOT done yet

| Layer | State | Impact |
|-------|-------|--------|
| Go bindings (`contracts/bindings/IncredibleSquaringTaskManager/binding.go`) | **Resolved in the 5/2 M1-M2 zip** — now has `PricePair`, `PriceDecimals`, `EthUsdPrice` | M3 can now target the real generated struct names |
| `operator/operator.go` | **Partially resolved in the 5/2 M1-M2 zip** — fetches Coinbase ETH/USD, scales to 8 decimals, fills `EthUsdPrice` | Good enough for M3 static integration; still only one price source |
| `aggregator/aggregator.go` | Untouched (still calls `SendNewTaskNumberToSquare`) | M3 (us) — patched here |
| `core/chainio/avs_writer.go` | Untouched | Needs new function name + new `RaiseChallenge` signature → patched here |
| `challenger/challenger.go` | Untouched (still reads `NumberSquared`) | M4 hasn't shipped |
| `aggregator_test.go`, `challenger_test.go`, `rpc_server_test.go` | Untouched, will fail post-binding-regen | M4 fix later |
| `core/chainio/mocks/avs_writer.go` | Untouched generated mock — still exposes `SendNewTaskNumberToSquare` and old `RaiseChallenge` args | Unit tests need mock regeneration after M3 changes |

**Net as of 5/2 zip**: M1 + M2 have moved Solidity, bindings, digest
hashing, and operator price fetching forward. M3 can now patch
`aggregator/` and `core/chainio/avs_writer.go`, but full tests will
still need regenerated mocks plus updated aggregator/challenger tests.

---

## 2.1 What M2 changed in the 5/2 zip

M2 has made the operator useful for M3:

* `operator/operator.go` now filters tasks by `PricePair == keccak256("ETH/USD")`.
* It normalizes `PriceDecimals`, defaulting to 8.
* It calls Coinbase:
  `https://api.exchange.coinbase.com/products/ETH-USD/ticker`.
* It parses decimal strings into fixed-point `*big.Int`.
* It returns:

```go
&cstaskmanager.IIncredibleSquaringTaskManagerTaskResponse{
    ReferenceTaskIndex: newTaskCreatedLog.TaskIndex,
    EthUsdPrice:        ethUsdPrice,
}
```

* `core/utils.go` now hashes `(referenceTaskIndex, ethUsdPrice)`.
* `operator/operator_test.go` covers `3152.47 -> 315247000000`.

M2 has **not** yet implemented multi-CEX selection. All operators use
Coinbase unless they run modified binaries. For the paper narrative,
we should either describe the current implementation as single-source
for the first demo or ask M2 to add `OPERATOR_PRICE_SOURCE` so operators
can be pinned to Coinbase / Binance / Kraken / OKX.

---

## 3. Open team-level design decision: BLS aggregation over heterogeneous prices

This is the most important issue surfaced by today's audit.

The current contract verifies operator signatures against
`keccak256(abi.encode(taskResponse))`, where `taskResponse =
{referenceTaskIndex, ethUsdPrice}`. The EigenSDK
`BlsAggregationService` aggregates BLS signatures **only over an
identical message digest**. So if four operators report four different
ETH/USD prices, they sign four *different* messages, the BLS service
puts each into its own bucket, and no quorum is ever reached on any
single message.

Three viable paths (one must be chosen):

### Path A — Two-round aggregation (most "correct")
* Round 1 (price collection): each operator POSTs `(taskIndex, p_i)`
  to aggregator, *unsigned* (or signed with an ECDSA op key, not BLS).
* Aggregator computes `median = Median(p_1, …, p_n)`.
* Round 2 (consensus signing): aggregator broadcasts the canonical
  `TaskResponse{taskIndex, median}` to operators. Each operator
  BLS-signs it (optionally with a sanity check: refuse to sign if the
  median diverges from one's own reported price by > X%).
* Aggregator collects BLS sigs, aggregates, submits.
* **Cost**: requires changes in `operator/operator.go` and a new
  `RequestSignatureOnMedian` RPC on the aggregator. M2 work.

### Path B — Single-round, aggregator-trusted median (demo-fast)
* Operators sign `(taskIndex, p_i)` over their own price (current
  flow).
* Aggregator stashes `p_i` per operator, computes `median`.
* Aggregator submits `TaskResponse{taskIndex, median}` to the contract
  with whatever BLS aggregate sig the SDK produces.
* On-chain `respondToTask` will fail signature verification because the
  message hash won't match. To make the demo run end-to-end one of:
  * (i) Patch `respondToTask` to skip signature verification (defeats
    the whole point of the AVS).
  * (ii) Operators agree to BLS-sign just `(taskIndex, "PRICE_QUOTE")`
    as a liveness attestation (we drop binding the signature to the
    actual price). Honest in §V if framed as "BLS attests
    participation; median is aggregator-side."
* **Cost**: single-line change in operator (sign canonical bytes
  instead of price), no contract change.

### Path C — Deterministic price source
* All operators query an identical, normalized price source (e.g., a
  fixed CoinGecko endpoint with floor-rounded value).
* All operators sign the same `TaskResponse` ⇒ BLS aggregation works
  as in the original template.
* **Cost**: kills the "robust median over heterogeneous CEXes"
  narrative. §V loses Figure 1 and most of V.C.

### M3 recommendation
Path A is the right architecture and what §V already describes.
Path B unblocks a working demo this week with minimal operator-side
work and is honest if framed as "BLS-as-liveness-attestation."
Path C is a non-starter for the paper.

**The proposed `aggregator.go.proposed` here computes the median, but
submits the median only when the BLS quorum has actually signed that
median.** If the quorum signed a different individual price, the code
logs the mismatch and submits the BLS-signed price instead so the
on-chain signature check does not fail. This keeps the demo runnable
while making the protocol limitation visible in logs. A true median
consensus demo still needs Path A.

---

## 4. Tolerance discrepancy: 1% on-chain vs 5% in §V

M1 hard-coded `DEFAULT_PRICE_DEVIATION_TOLERANCE_BPS = 100` (= 1%) as
the contract's challenge tolerance. The current §V draft argues for
τ = 5% in `DetectOutliers`.

These are not quite the same parameter:

* **On-chain `priceDeviationToleranceBps`** — tolerance for the
  *aggregated median* vs a challenger's reference. Wrong-by-more-than-1%
  median ⇒ all signing operators slashed.
* **Off-chain `tolerancePct` in `DetectOutliers`** — the band a single
  operator's individual report must lie within around the median to
  *not* be flagged. Currently used aggregator-side as a logging /
  reputation signal (the M1 contract has no per-operator slash hook
  to consume it).

Three ways to reconcile:
1. **Keep both, frame separately in §V**: 1% on-chain median tolerance
   (challenger flow), 5% off-chain per-operator outlier filter
   (aggregator pre-processing). Cleanest narrative — would re-use the
   existing Figure 2 to motivate 5% for the *off-chain* knob, and
   point to M1's 1% as the *on-chain* sister knob.
2. **Drop §V's τ = 5% sweep, redo at τ = 1%**: re-run `simulate_avs.py`
   for τ ∈ {0.05%, …, 3%}, regenerate Figure 2, argue 1% is the chosen
   value. Aligns with the contract default.
3. **Push back to M1 to use 5%**: change one constant in
   `IncredibleSquaringTaskManager.sol`. Cheapest if team is amenable.

I recommend option 1 — it's intellectually defensible, requires no
code changes, and gives §V more material rather than less.

---

## 5. Concrete next steps

| # | Action | Owner | Blocks |
|---|--------|-------|--------|
| 1 | Apply this M3 patch (`bash apply_patch.sh <upstream>`) | Jon | Aggregator compile |
| 2 | Regenerate `core/chainio/mocks/avs_writer.go` after M3 changes | Jon / whoever has Go tools | Aggregator tests |
| 3 | Update aggregator tests away from `NumberToSquare` | Jon | Unit tests |
| 4 | Decide Path A / B / C | All four | BLS + median correctness |
| 5 | Add multi-CEX source selection (`OPERATOR_PRICE_SOURCE`) | M2 | Paper's heterogeneous-source claim |
| 6 | If Path A: add aggregator round-2 RPC | Jon + M2 | Correct BLS median demo |
| 7 | Update §V tex with 1%/5% framing decision | Jon | Paper |
