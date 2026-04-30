# M3 — Aggregator 模块工作目录

> Jon 的工作区。最终代码会被推到 fork 出来的 `PriceOracle-AVS` repo 的 `aggregator/` 目录下。

## 文件清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `median.go` | 中位数 / 方差 / outlier 检测的纯算法实现 | ✅ skeleton 已写 |
| `median_test.go` | 对应的单元测试，10 个 test case | ✅ skeleton 已写 |
| `aggregator_modifications.md` | aggregator.go 4 处改动的 diff | 等环境搭好后再写 |
| `section_V_skeleton.md` | 论文 §V 章节的英文骨架 | 等实验数据出来后再写 |

## 离线测 median.go（不需要装 EigenLayer 工具链）

只要装了 Go 1.21+：

```bash
cd experiments/m3_aggregator
go mod init m3_test
go test -v
```

期望输出：所有 10 个 test PASS。

## 等 fork 好之后

把 `median.go` 和 `median_test.go` 拷进 `PriceOracle-AVS/aggregator/` 目录，跑：

```bash
cd PriceOracle-AVS/aggregator
go test -run TestMedian -v
go test -run TestVariance -v
go test -run TestDetectOutliers -v
```

如果要在论文里展示，跑：
```bash
go test -bench=. -benchmem -count=5 ./aggregator/...
```
能拿到聚合性能数据。

## 代码改动思路（对应 M3_GUIDE.md 的 Step 3）

参见根目录 `M3_GUIDE.md` 第 3 节。等你把环境搭好、看完原版 aggregator.go，告诉我，我把这 4 处的具体 diff 写在 `aggregator_modifications.md` 里。
