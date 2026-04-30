# PriceOracle-AVS

PriceOracle-AVS is a course project that modifies EigenLayer's
Incredible Squaring AVS template into a decentralized ETH/USD price
oracle. Operators fetch prices from multiple exchanges, sign their
reports with BLS, and the aggregator computes a robust median consensus
with deviation-based outlier detection.

## Repository Layout

| Path | Purpose |
|------|---------|
| `experiments/m3_aggregator/` | M3 aggregator implementation notes, median consensus code, tests, simulations, and generated figures |
| `paper/` | IEEE-style report draft, bibliography, and figures |
| `setup_dev.sh` | Development-environment setup helper |
| `REPO_AND_TASKS.md` | Team implementation breakdown |

## M3 Aggregator Status

The M3 module is currently self-contained under
`experiments/m3_aggregator/`:

- `median.go`: fixed-point median, variance, and outlier detection.
- `median_test.go`: unit tests and benchmarks.
- `simulate_avs.py`: Monte-Carlo experiments for robustness,
  tolerance sensitivity, and aggregation latency.
- `aggregator_modifications.md`: integration guide for the real
  `aggregator/aggregator.go` once the AVS fork and contract bindings
  are available.

Run the offline algorithm checks with:

```bash
cd experiments/m3_aggregator
go test -v
go test -bench=. -benchmem
```

If Go is not installed, use the Python mirror:

```bash
python verify_median.py
```
