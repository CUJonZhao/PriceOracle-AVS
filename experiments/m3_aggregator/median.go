// Package aggregator: median consensus utilities for PriceOracle-AVS.
//
// This file implements the "Median Consensus" component of the modified
// Incredible Squaring AVS. Prices reported by operators are aggregated
// using the statistical median rather than an arithmetic mean, so that
// a small number of malicious or buggy operators cannot move the
// consensus price arbitrarily far from the truth.
//
// All prices are represented as *big.Int with 6 fixed decimal places,
// matching Chainlink's USD pair convention (e.g., 3500_000000 == $3500.00).
package aggregator

import (
	"math/big"
	"sort"
)

// Median returns the statistical median of the given prices.
// For an even-length input the returned value is the floor-mean
// of the two middle elements.
//
// Empty input returns 0.
func Median(prices []*big.Int) *big.Int {
	n := len(prices)
	if n == 0 {
		return big.NewInt(0)
	}

	// Defensive copy so we don't mutate the caller's slice.
	sorted := make([]*big.Int, n)
	for i, p := range prices {
		sorted[i] = new(big.Int).Set(p)
	}
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Cmp(sorted[j]) < 0
	})

	if n%2 == 1 {
		return new(big.Int).Set(sorted[n/2])
	}

	// Even count: floor((a+b)/2) of the two central elements.
	sum := new(big.Int).Add(sorted[n/2-1], sorted[n/2])
	return new(big.Int).Div(sum, big.NewInt(2))
}

// Variance returns the population variance of prices about the
// supplied center (typically the Median). The result is in units
// of price^2 and may be very large; callers commonly take its
// square root or compare it against a fixed threshold.
//
// Empty input returns 0.
func Variance(prices []*big.Int, center *big.Int) *big.Int {
	n := len(prices)
	if n == 0 {
		return big.NewInt(0)
	}
	sumSq := big.NewInt(0)
	for _, p := range prices {
		diff := new(big.Int).Sub(p, center)
		sq := new(big.Int).Mul(diff, diff)
		sumSq.Add(sumSq, sq)
	}
	return new(big.Int).Div(sumSq, big.NewInt(int64(n)))
}

// DetectOutliers returns the indices of prices whose absolute
// deviation from the supplied median exceeds tolerancePct percent
// of the median (e.g., tolerancePct = 5 -> ±5% band).
//
// Indices are returned in ascending order. A median of zero
// (degenerate) returns no outliers.
func DetectOutliers(prices []*big.Int, median *big.Int, tolerancePct uint64) []int {
	if median.Sign() == 0 {
		return nil
	}

	// threshold = median * tolerancePct / 100
	threshold := new(big.Int).Mul(median, new(big.Int).SetUint64(tolerancePct))
	threshold.Div(threshold, big.NewInt(100))

	var outliers []int
	for i, p := range prices {
		diff := new(big.Int).Sub(p, median)
		absDiff := new(big.Int).Abs(diff)
		if absDiff.Cmp(threshold) > 0 {
			outliers = append(outliers, i)
		}
	}
	return outliers
}
