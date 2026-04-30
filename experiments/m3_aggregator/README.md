# M3 — Aggregator 模块

Jon 负责的 M3 工作区：把 EigenLayer Incredible Squaring AVS 的
`aggregator/` 改造成价格预言机的中位数聚合器，并完成论文
Section V（BLS Signature and Median Consensus）。

## 文件清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `go.mod` | 离线测试用 Go module | 已完成 |
| `median.go` | 中位数 / 方差 / outlier 检测的纯算法实现 | 已完成 |
| `median_test.go` | 10 个单元测试 + 2 个 benchmark | 已完成 |
| `verify_median.py` | Python 版校验脚本，不依赖本机 Go 环境 | 已完成 |
| `simulate_avs.py` | Monte-Carlo 实验和画图脚本 | 已完成 |
| `aggregator_modifications.md` | `aggregator.go` 4 处改动说明 | 已完成 |
| `section_V_skeleton.md` | 论文 Section V 英文骨架 | 已完成 |
| `figs/` | 鲁棒性、tolerance、latency 的图和 CSV | 已完成 |

## 离线测 median.go（不需要装 EigenLayer 工具链）

只要装了 Go 1.21+：

```bash
cd experiments/m3_aggregator
go test -v
go test -bench=. -benchmem
```

期望输出：所有 10 个 unit tests PASS，并打印 median / outlier 检测的
benchmark 结果。

如果本机还没有 Go，可以先跑 Python 校验脚本：

```bash
python verify_median.py
```

当前校验结果：10 / 10 passed。

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

现在根目录的临时 guide 已经移除；具体改造步骤保留在
`aggregator_modifications.md`。真正集成时需要先拿到 fork 后的
`PriceOracle-AVS/aggregator/aggregator.go` 和 M1 生成的新 ABI binding，
然后按该文档完成：

1. task 字段从 squaring number 换成 price task 的 `AssetPair`。
2. task generator 从 `sendNewTaskNumberToSquare` 改成 `sendNewPriceTask`。
3. `ProcessSignedTaskResponse` 记录每个 operator 的 `ReportedPrice`。
4. `sendAggregatedResponseToContract` 调用 `Median`、`Variance`、
   `DetectOutliers`，把 median 和 variance 上链。
