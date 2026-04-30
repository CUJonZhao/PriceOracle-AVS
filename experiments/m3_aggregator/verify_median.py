"""
Python port of the Go median.go logic, used to verify the algorithm
end-to-end before the user runs `go test`. Mirrors the *_test.go
cases one-for-one so that whatever passes here is what passes there.

Run:   python3 verify_median.py
"""

# ----- algorithm (mirrors median.go) -----

def median(prices):
    n = len(prices)
    if n == 0:
        return 0
    s = sorted(prices)
    if n % 2 == 1:
        return s[n // 2]
    # Even count: integer floor of (a+b)/2 to match big.Int.Div
    return (s[n // 2 - 1] + s[n // 2]) // 2


def variance(prices, center):
    n = len(prices)
    if n == 0:
        return 0
    return sum((p - center) ** 2 for p in prices) // n


def detect_outliers(prices, median_val, tolerance_pct):
    if median_val == 0:
        return None
    threshold = (median_val * tolerance_pct) // 100
    return [i for i, p in enumerate(prices) if abs(p - median_val) > threshold]


# ----- tests (mirror median_test.go) -----

def run():
    failures = []

    def check(name, got, want):
        if got == want:
            print(f"  PASS  {name}")
        else:
            print(f"  FAIL  {name}: got {got!r}, want {want!r}")
            failures.append(name)

    print("Median tests")
    check("Median_OddCount",
          median([3500_00000000, 3505_00000000, 3490_00000000]),
          3500_00000000)
    check("Median_EvenCount",
          median([3500_00000000, 3502_00000000, 3506_00000000, 3508_00000000]),
          3504_00000000)
    check("Median_Empty", median([]), 0)
    check("Median_RobustToOneOutlier",
          median([3500_00000000, 3502_00000000, 3505_00000000, 99999_00000000]),
          3503_50000000)

    # confirm input slice not mutated
    inp = [3, 1, 2]
    _ = median(inp)
    check("Median_DoesNotMutateInput", inp, [3, 1, 2])

    print("\nVariance tests")
    check("Variance_Basic",
          variance([100, 102, 98, 100], 100),
          2)
    check("Variance_Empty", variance([], 100), 0)

    print("\nDetectOutliers tests")
    check("DetectOutliers_FivePercentBand",
          detect_outliers([3500_00000000, 3600_00000000, 3700_00000000,
                           3300_00000000, 3400_00000000],
                          3500_00000000, 5),
          [2, 3])
    check("DetectOutliers_NoneFlagged",
          detect_outliers([3490_00000000, 3505_00000000, 3510_00000000],
                          3500_00000000, 5),
          [])
    check("DetectOutliers_ZeroMedian",
          detect_outliers([1, -1], 0, 5),
          None)

    print(f"\nResult: {10 - len(failures)} / 10 passed")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
