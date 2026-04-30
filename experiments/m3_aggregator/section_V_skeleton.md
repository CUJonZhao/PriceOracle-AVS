# §V — Aggregator: BLS Signature Aggregation and Median Consensus

> Target length: ~1.0 IEEE column page (≈ 700 words + 2 figures + 1 equation block).
> Author: Jon (M3).
> Status: skeleton complete, awaiting end-to-end Anvil numbers from M4 to fill the
> last paragraph.

---

## V.A  Role of the Aggregator

The Aggregator is a logically centralized but cryptographically untrusted
service that (i) creates new price-quote tasks at a fixed cadence, (ii)
collects BLS-signed responses from the registered operators, (iii)
verifies the aggregated signature once a quorum threshold is met, and
(iv) submits the consensus price together with its observed dispersion
back to the on-chain `PriceOracleTaskManager`. Crucially, the
Aggregator **cannot forge consensus**: any aggregated signature it
publishes must verify against the BLS public-key sum of the operators
who actually signed.

[CITE: EigenLayer Whitepaper §3; AVS Book "Aggregator" chapter; Boneh
multi-sig 2018]

## V.B  BLS Signature Aggregation

We adopt the BLS scheme of Boneh, Lynn, and Shacham over the BLS12-381
pairing-friendly curve, exposed by EVM precompile EIP-2537. Each
operator $i$ holds a key pair $(\mathit{sk}_i, pk_i = g_2^{\mathit{sk}_i})$
and produces a signature on the task message $m$:
$$
\sigma_i = H(m)^{\mathit{sk}_i}, \qquad
\sigma_{\text{agg}} = \prod_{i \in S} \sigma_i,
$$
where $S \subseteq \{1,\dots,n\}$ is the set of signing operators.
A verifier accepts iff
$$
e\!\left(\sigma_{\text{agg}},\, g_2\right)
= e\!\left(H(m),\, \prod_{i \in S} pk_i\right).
$$
This is a single pairing equation regardless of $|S|$, so on-chain
verification cost is *independent* of the number of operators — a
property we exploit in §V.D below to argue the system scales
horizontally.

[CITE: BLS 2004; Boneh multi-sig 2018; EIP-2537]

## V.C  Why Median, Not Mean

Operators in our deployment query four heterogeneous CEX endpoints
(Binance, Coinbase, Kraken, OKX), so honest reports already disagree
by a few basis points due to bid–ask spreads and timestamp skew.  An
arithmetic mean is *unbiased* under these conditions but is **not
robust**: a single operator reporting a wildly wrong price drags the
consensus by $1/n$ of the bias, growing linearly with adversarial
size.

The statistical median, by contrast, is the textbook robust
$L_1$-estimator with a 50% breakdown point — meaning the consensus
remains close to the true price as long as fewer than half of the
operators are dishonest [CITE: Huber, *Robust Statistics*, 1981].
We confirm this empirically.  Figure 1 reports the absolute
percentage error of the consensus price, computed by both estimators,
as the fraction of malicious operators (each biasing by a uniformly
random $[2\%, 12\%]$) increases.  With fewer than half of the operators
malicious, the median's 95th-percentile error remains below $0.09\%$;
once the adversarial set reaches a majority, the theoretical breakdown
guarantee no longer applies and the tail error rises sharply.  The mean,
in contrast, starts drifting from the very first malicious operator.

[INSERT fig\_v1\_median\_robustness.pdf  here]

## V.D  Slashing Threshold Sensitivity

Our `DetectOutliers` rule flags any operator whose individual report
deviates from the consensus median by more than $\tau$ percent, where
$\tau$ is a deployment parameter.  Tightening $\tau$ catches more
adversaries (true positives) but risks slashing honest operators
whose reports are merely noisy (false positives).

To select $\tau$ defensibly we sweep it from 0.25% to 15% and measure
the true-positive and false-positive rates against operators who bias
their reports by a uniformly random $[2\%, 12\%]$.  Honest operators
are modelled with $\sigma{=}5\,\text{bp}$ Gaussian noise around the
truth.  Figure 2 plots the result.

[INSERT fig\_v2\_tolerance\_sensitivity.pdf here]

The honest-operator FPR is essentially zero at every $\tau \geq 0.25\%$
(honest noise never reaches 0.25% in our model), while the TPR drops
from ~100% at $\tau{=}1\%$ to 70% at $\tau{=}5\%$ and to ~0% at
$\tau{=}15\%$.  We adopt $\tau = 5\%$ for the on-chain rule: it
catches the substantial majority of adversaries while preserving a
generous safety margin for transient market dislocations
(e.g.\ a flash crash on a single venue) that should not by themselves
trigger slashing.  The 30% of attackers who bias by less than 5\% are
"caught" instead by economic incentives — their attacks are
unprofitable on a per-task basis.

## V.E  End-to-End Latency

Figure 3 shows the simulated end-to-end latency of one task, from
on-chain `NewTaskCreated` emission to `respondToTask` confirmation,
as the registered operator count grows from 3 to 30.  The model
combines per-operator quote retrieval (Gamma-distributed, mean
$160\,\text{ms}$), BLS sign + RPC round-trip (Gamma, mean $30\,\text{ms}$),
quorum aggregation, and on-chain submission ($\mathcal{N}(2000, 200)\,\text{ms}$).

[INSERT fig\_v3\_aggregation\_latency.pdf here]

P50 latency hovers around $2.23\,\text{s}$ across all sizes; the
on-chain step dominates, and BLS aggregation itself is invisible
(<10 ms) thanks to the constant-cost pairing check derived in §V.B.
This validates the design choice of constant-size aggregated
signatures over schemes with $O(n)$ on-chain cost.

[The final paragraph on real-Anvil numbers is a TODO once M4 finishes
the integration test; replace simulated 2.23 s with the measured
median from `e2e_test.sh`.]

---

## §V references to add to `references.bib`

The following must appear in our shared bibliography (M4 maintains):

```
@article{boneh2004short,
  author    = {Dan Boneh and Ben Lynn and Hovav Shacham},
  title     = {Short Signatures from the {Weil} Pairing},
  journal   = {Journal of Cryptology},
  volume    = {17},
  number    = {4},
  year      = {2004},
}

@inproceedings{boneh2018compact,
  author    = {Dan Boneh and Manu Drijvers and Gregory Neven},
  title     = {Compact Multi-Signatures for Smaller Blockchains},
  booktitle = {ASIACRYPT},
  year      = {2018},
}

@misc{eip2537,
  title  = {{EIP-2537}: Precompile for {BLS12-381} Curve Operations},
  author = {{Ethereum Improvement Proposals}},
  year   = {2020},
}

@book{huber1981robust,
  author  = {Peter J. Huber},
  title   = {Robust Statistics},
  year    = {1981},
  publisher = {Wiley},
}

@misc{eigenlayer2023,
  title  = {{EigenLayer}: The Restaking Collective},
  author = {{EigenLabs}},
  year   = {2023},
  howpublished = {Whitepaper, \url{https://www.eigenlayer.xyz}},
}
```

## What still needs to be inserted before §V is "done"

1. **Real Anvil numbers** — the last paragraph of V.E should cite the median latency of an actual end-to-end test once M4 wires it up.
2. **A photo of the on-chain `respondToTask` transaction on Etherscan** if we deploy to Holesky (optional).
3. **Cross-references** to §III's slashing definition (M1 owns) so the
   $\tau = 5\%$ choice in V.D is consistent with the contract code.

That's all — once the code is integrated and the e2e test runs once,
this section is essentially complete.
