#!/usr/bin/env bash
# Apply the M3 staged patch to a clone of
# Decentralized_ETH_USD_oracle_AVS.
#
# Usage:
#   bash apply_patch.sh <path-to-upstream-clone-root>
#
# Pre-condition: M1 has run `make bindings` in the upstream so that
# contracts/bindings/IncredibleSquaringTaskManager/binding.go contains
# PricePair / PriceDecimals / EthUsdPrice fields. Without that, the
# patched aggregator.go and avs_writer.go will not compile.

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <path-to-upstream-clone-root>" >&2
  exit 1
fi

UPSTREAM="$1"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "$UPSTREAM/aggregator" || ! -d "$UPSTREAM/core/chainio" ]]; then
  echo "error: $UPSTREAM does not look like the upstream repo (missing aggregator/ or core/chainio/)" >&2
  exit 1
fi

# Sanity check: warn if M1 hasn't regenerated bindings.
if grep -q "NumberToBeSquared" "$UPSTREAM/contracts/bindings/IncredibleSquaringTaskManager/binding.go" 2>/dev/null; then
  echo "WARNING: $UPSTREAM/contracts/bindings/IncredibleSquaringTaskManager/binding.go still references"
  echo "         NumberToBeSquared.  M1 has not regenerated bindings yet."
  echo "         The patch will be applied, but the upstream will not compile until M1 runs"
  echo "         'cd contracts && ./generate-go-bindings.sh' (or 'make bindings')."
  echo
fi

echo "Backing up upstream files to .preM3.bak ..."
cp -n "$UPSTREAM/aggregator/aggregator.go"     "$UPSTREAM/aggregator/aggregator.go.preM3.bak"     || true
cp -n "$UPSTREAM/aggregator/rpc_server.go"     "$UPSTREAM/aggregator/rpc_server.go.preM3.bak"     || true
cp -n "$UPSTREAM/core/chainio/avs_writer.go"   "$UPSTREAM/core/chainio/avs_writer.go.preM3.bak"   || true
cp -n "$UPSTREAM/challenger/challenger.go"      "$UPSTREAM/challenger/challenger.go.preM3.bak"      || true

echo "Copying staged files into upstream ..."
cp "$HERE/aggregator.go.proposed"   "$UPSTREAM/aggregator/aggregator.go"
cp "$HERE/rpc_server.go.proposed"   "$UPSTREAM/aggregator/rpc_server.go"
cp "$HERE/avs_writer.go.proposed"   "$UPSTREAM/core/chainio/avs_writer.go"
cp "$HERE/median.go"                "$UPSTREAM/aggregator/median.go"
cp "$HERE/median_test.go"           "$UPSTREAM/aggregator/median_test.go"
cp "$HERE/challenger.go.proposed"   "$UPSTREAM/challenger/challenger.go"

cat <<EOF

Done. Files written into $UPSTREAM:
  aggregator/aggregator.go      (replaced; original at .preM3.bak)
  aggregator/rpc_server.go      (replaced; original at .preM3.bak)
  aggregator/median.go          (new)
  aggregator/median_test.go     (new)
  core/chainio/avs_writer.go    (replaced; original at .preM3.bak)
  challenger/challenger.go      (replaced; original at .preM3.bak)

Next steps inside \$UPSTREAM:
  1) make bindings   # if M1 hasn't already
  2) go build ./...  # confirms compile
  3) go test ./aggregator/... -run "TestMedian|TestVariance|TestDetectOutliers"
  4) make e2e-test   # once M2 ships operator changes
EOF
