package aggregator

import (
	"math/big"
	"testing"
)

// helper: compact big-int construction from int64 literals.
func bi(x int64) *big.Int { return big.NewInt(x) }

func TestMedian_OddCount(t *testing.T) {
	prices := []*big.Int{bi(3500_00000000), bi(3505_00000000), bi(3490_00000000)}
	got := Median(prices)
	want := bi(3500_00000000)
	if got.Cmp(want) != 0 {
		t.Errorf("Median odd: got %v, want %v", got, want)
	}
}

func TestMedian_EvenCount(t *testing.T) {
	prices := []*big.Int{bi(3500_00000000), bi(3502_00000000), bi(3506_00000000), bi(3508_00000000)}
	got := Median(prices)
	// floor((3502 + 3506) / 2) = 3504
	want := bi(3504_00000000)
	if got.Cmp(want) != 0 {
		t.Errorf("Median even: got %v, want %v", got, want)
	}
}

func TestMedian_Empty(t *testing.T) {
	got := Median(nil)
	if got.Sign() != 0 {
		t.Errorf("Median empty: got %v, want 0", got)
	}
}

func TestMedian_RobustToOneOutlier(t *testing.T) {
	// One operator reports a wildly wrong number — median should
	// barely move, demonstrating the robustness motivation.
	prices := []*big.Int{
		bi(3500_00000000),
		bi(3502_00000000),
		bi(3505_00000000),
		bi(99999_00000000), // outlier
	}
	got := Median(prices)
	// sorted: [3500, 3502, 3505, 99999]; median = floor((3502+3505)/2) = 3503
	want := bi(3503_50000000)
	if got.Cmp(want) != 0 {
		t.Errorf("Median robust: got %v, want %v", got, want)
	}
}

func TestMedian_DoesNotMutateInput(t *testing.T) {
	prices := []*big.Int{bi(3), bi(1), bi(2)}
	_ = Median(prices)
	if prices[0].Cmp(bi(3)) != 0 || prices[1].Cmp(bi(1)) != 0 || prices[2].Cmp(bi(2)) != 0 {
		t.Errorf("Median must not mutate caller's slice; got %v", prices)
	}
}

func TestVariance_Basic(t *testing.T) {
	// sample {100,102,98,100} about center 100 -> deviations {0,2,-2,0}
	// population variance = (0 + 4 + 4 + 0) / 4 = 2
	got := Variance([]*big.Int{bi(100), bi(102), bi(98), bi(100)}, bi(100))
	want := bi(2)
	if got.Cmp(want) != 0 {
		t.Errorf("Variance: got %v, want %v", got, want)
	}
}

func TestVariance_Empty(t *testing.T) {
	got := Variance(nil, bi(100))
	if got.Sign() != 0 {
		t.Errorf("Variance empty: got %v, want 0", got)
	}
}

func TestDetectOutliers_FivePercentBand(t *testing.T) {
	// median = 3500, 5% band -> [3325, 3675].
	median := bi(3500_00000000)
	prices := []*big.Int{
		bi(3500_00000000), // in
		bi(3600_00000000), // in (+2.86%)
		bi(3700_00000000), // OUT (+5.71%)
		bi(3300_00000000), // OUT (-5.71%)
		bi(3400_00000000), // in
	}
	got := DetectOutliers(prices, median, 5)
	want := []int{2, 3}
	if !sliceEqual(got, want) {
		t.Errorf("DetectOutliers: got %v, want %v", got, want)
	}
}

func TestDetectOutliers_NoneFlagged(t *testing.T) {
	median := bi(3500_00000000)
	prices := []*big.Int{bi(3490_00000000), bi(3505_00000000), bi(3510_00000000)}
	got := DetectOutliers(prices, median, 5)
	if len(got) != 0 {
		t.Errorf("DetectOutliers expected none, got %v", got)
	}
}

func TestDetectOutliers_ZeroMedian(t *testing.T) {
	got := DetectOutliers([]*big.Int{bi(1), bi(-1)}, bi(0), 5)
	if got != nil {
		t.Errorf("DetectOutliers zero median should return nil, got %v", got)
	}
}

func sliceEqual(a, b []int) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func BenchmarkMedianSevenOperators(b *testing.B) {
	prices := []*big.Int{
		bi(3500_00000000),
		bi(3502_00000000),
		bi(3498_00000000),
		bi(3501_00000000),
		bi(3499_00000000),
		bi(3504_00000000),
		bi(3300_00000000),
	}

	for i := 0; i < b.N; i++ {
		_ = Median(prices)
	}
}

func BenchmarkDetectOutliersSevenOperators(b *testing.B) {
	median := bi(3500_00000000)
	prices := []*big.Int{
		bi(3500_00000000),
		bi(3502_00000000),
		bi(3498_00000000),
		bi(3700_00000000),
		bi(3499_00000000),
		bi(3504_00000000),
		bi(3300_00000000),
	}

	for i := 0; i < b.N; i++ {
		_ = DetectOutliers(prices, median, 5)
	}
}
