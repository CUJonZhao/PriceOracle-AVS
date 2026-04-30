# aggregator.go 4 处改动 — 详细 diff 手册

> 这份手册告诉你**改哪几个函数 + 改成什么样**。线号会随上游版本浮动，所以
> 我们用 `grep` 定位 anchor 行（标注 `[ANCHOR-N]`），你看到 anchor 就知道
> 上下文对。对 anchor 不到的话贴报错给我，10秒解决。

## 改动总览

| # | 文件 | 改动 | 复杂度 |
|---|------|------|--------|
| ① | `aggregator/aggregator.go` | Task struct 字段名替换 | 5 分钟 |
| ② | `aggregator/aggregator.go` | `sendNewTaskNumberToSquare` → `sendNewPriceTask` | 15 分钟 |
| ③ | `aggregator/aggregator.go` | `ProcessSignedTaskResponse` 收集每个 operator 的报价 | 25 分钟 |
| ④ | `aggregator/aggregator.go` | `sendAggregatedResponseToContract` 用 median.go 算共识 | 25 分钟 |

> 整体预算 ~75 分钟编码 + ~15 分钟跑测试。

---

## 改动 ①：Task struct 字段名替换

[ANCHOR-1] 找原版定义：
```bash
grep -n "NumberToBeSquared\|numberToBeSquared" aggregator/*.go
```

替换规则：
- `NumberToBeSquared`  →  `AssetPair`（类型从 `uint32` 改成 `string`）
- `numberToBeSquared`  →  `assetPair`

注意：合约侧（M1）会同步把 ABI binding 重新 generate，所以你这边
import 进来的 binding 类型字段也会变。先编译看哪里红波浪线。

```go
// before（伪代码示意）
type IIncredibleSquaringTaskManagerTask struct {
    NumberToBeSquared        uint32
    TaskCreatedBlock         uint32
    QuorumNumbers            []byte
    QuorumThresholdPercentage uint32
}

// after
type IPriceOracleTaskManagerTask struct {
    AssetPair                string
    TaskCreatedBlock         uint32
    QuorumNumbers            []byte
    QuorumThresholdPercentage uint32
}
```

---

## 改动 ②：task 生成函数改名 + 改逻辑

[ANCHOR-2] 找原版函数：
```bash
grep -n "sendNewTaskNumberToSquare" aggregator/aggregator.go
grep -n "rand.Intn\|big.NewInt" aggregator/aggregator.go  # 原版用的随机数生成器
```

原版（伪代码骨架）：
```go
func (agg *Aggregator) sendNewTaskNumberToSquare() {
    numToSquare := big.NewInt(int64(rand.Intn(1000)))
    newTask, taskIndex, err := agg.avsWriter.SendNewTaskNumberToSquare(
        ctx, numToSquare, QUORUM_THRESHOLD_NUMERATOR, QUORUM_NUMBERS,
    )
    if err != nil { ... }
    // record into agg.tasks map ...
}
```

改成：
```go
// SupportedAssetPairs is the small fixed set of CEX feeds the Operators know.
// Adding more pairs requires the Operator nodes to ship a new release.
var SupportedAssetPairs = []string{"ETH/USD", "BTC/USD"}

func (agg *Aggregator) sendNewPriceTask() {
    // round-robin through the supported pairs so we exercise both feeds
    pair := SupportedAssetPairs[agg.taskCounter%len(SupportedAssetPairs)]
    agg.taskCounter++

    newTask, taskIndex, err := agg.avsWriter.SendNewPriceTask(
        context.Background(),
        pair,
        QUORUM_THRESHOLD_NUMERATOR,
        QUORUM_NUMBERS,
    )
    if err != nil {
        agg.logger.Error("aggregator failed to send new price task", "err", err)
        return
    }
    agg.tasksMu.Lock()
    agg.tasks[taskIndex] = newTask
    agg.priceQuotes[taskIndex] = make(map[sdktypes.OperatorId]*big.Int)
    agg.tasksMu.Unlock()
    agg.logger.Info("created new price task", "pair", pair, "taskIndex", taskIndex)
}
```

> 别忘了在 `Aggregator` struct 里加两个字段：
> - `taskCounter uint64`
> - `priceQuotes map[uint32]map[sdktypes.OperatorId]*big.Int`
> - `tasksMu sync.RWMutex`（如果原版没有的话）

[ANCHOR-3] 主循环里改调用名：
```bash
grep -n "agg.sendNewTaskNumberToSquare\|sendNewTaskNumberToSquare()" aggregator/aggregator.go
```
所有地方改成 `agg.sendNewPriceTask()`。

---

## 改动 ③：ProcessSignedTaskResponse 收集每个 operator 的报价

[ANCHOR-4] 找 RPC handler：
```bash
grep -n "ProcessSignedTaskResponse" aggregator/*.go
```

这个函数是 operator 发回签名响应时通过 JSON-RPC 调进来的。原版只把签名转发给
内部 BLS aggregation service。我们要在转发**之前**把 operator 的报价记下来，
后面 §④ 算 median 用。

原版（伪代码）：
```go
func (agg *Aggregator) ProcessSignedTaskResponse(
    signedResp *SignedTaskResponse, reply *bool,
) error {
    err := agg.blsAggregationService.ProcessNewSignature(
        context.Background(),
        signedResp.TaskResponse.ReferenceTaskIndex,
        signedResp.TaskResponse,
        signedResp.BlsSignature,
        signedResp.OperatorId,
    )
    *reply = (err == nil)
    return err
}
```

改成：
```go
func (agg *Aggregator) ProcessSignedTaskResponse(
    signedResp *SignedTaskResponse, reply *bool,
) error {
    taskIndex := signedResp.TaskResponse.ReferenceTaskIndex

    // NEW: stash the operator's individually reported price BEFORE
    // we forward the signature on for BLS aggregation, so that we
    // can compute median + variance + outliers in §④ below.
    agg.tasksMu.Lock()
    if _, ok := agg.priceQuotes[taskIndex]; !ok {
        agg.priceQuotes[taskIndex] = make(map[sdktypes.OperatorId]*big.Int)
    }
    agg.priceQuotes[taskIndex][signedResp.OperatorId] =
        new(big.Int).Set(signedResp.TaskResponse.ReportedPrice)
    agg.tasksMu.Unlock()

    err := agg.blsAggregationService.ProcessNewSignature(
        context.Background(),
        taskIndex,
        signedResp.TaskResponse,
        signedResp.BlsSignature,
        signedResp.OperatorId,
    )
    *reply = (err == nil)
    return err
}
```

> `signedResp.TaskResponse.ReportedPrice` 这个字段 M1 会在 contracts 里
> 加，然后 abigen 重新生成 binding 后这里就有了。M1 早一步把字段定下来，
> 你这边 import 后填上即可。

---

## 改动 ④：sendAggregatedResponseToContract 用 median.go 算共识

[ANCHOR-5] 找上链提交函数：
```bash
grep -n "sendAggregatedResponseToContract\|SendAggregatedResponse" aggregator/aggregator.go
```

原版（伪代码）：
```go
func (agg *Aggregator) sendAggregatedResponseToContract(
    blsResp blsagg.BlsAggregationServiceResponse,
) {
    nonSignerStakesAndSignature := ...   // unchanged plumbing
    taskResponse := agg.tasks[blsResp.TaskIndex] // original numberSquared
    _, err := agg.avsWriter.SendAggregatedResponse(
        context.Background(),
        taskResponse,
        nonSignerStakesAndSignature,
    )
    if err != nil { ... }
}
```

改成（这是 M3 的核心修改，要塞进 median.go 里的三个函数）：
```go
func (agg *Aggregator) sendAggregatedResponseToContract(
    blsResp blsagg.BlsAggregationServiceResponse,
) {
    taskIdx := blsResp.TaskIndex

    // 1) Collect per-operator quotes that we stashed in §③.
    agg.tasksMu.RLock()
    quotesMap := agg.priceQuotes[taskIdx]
    agg.tasksMu.RUnlock()

    quotes := make([]*big.Int, 0, len(quotesMap))
    operatorIds := make([]sdktypes.OperatorId, 0, len(quotesMap))
    for opId, p := range quotesMap {
        quotes = append(quotes, p)
        operatorIds = append(operatorIds, opId)
    }

    // 2) Compute consensus.  See aggregator/median.go.
    medianPrice := Median(quotes)
    variance    := Variance(quotes, medianPrice)
    outlierIdxs := DetectOutliers(quotes, medianPrice, agg.tolerancePct)

    agg.logger.Info("aggregated price",
        "taskIndex", taskIdx,
        "medianPrice", medianPrice.String(),
        "variance",    variance.String(),
        "nQuotes",     len(quotes),
        "nOutliers",   len(outlierIdxs),
    )

    // 3) Build the on-chain TaskResponse (M1's new struct shape).
    onchainResp := taskmanager.IPriceOracleTaskManagerTaskResponse{
        ReferenceTaskIndex: taskIdx,
        PriceMedian:   medianPrice,
        PriceVariance: variance,
    }

    nonSignerStakesAndSignature := buildNonSignerStakesAndSignature(blsResp)

    _, err := agg.avsWriter.SendAggregatedResponse(
        context.Background(),
        onchainResp,
        nonSignerStakesAndSignature,
    )
    if err != nil {
        agg.logger.Error("submit on-chain response failed", "err", err)
        return
    }

    // 4) For each detected outlier operator, push to challenge queue
    //    (consumed by M4's challenger).  The challenger will independently
    //    fetch a price from a fifth source and decide whether to slash.
    for _, idx := range outlierIdxs {
        agg.challengeQueue <- ChallengeEntry{
            TaskIndex:        taskIdx,
            OperatorId:       operatorIds[idx],
            ReportedPrice:    quotes[idx],
            AggregatorMedian: medianPrice,
        }
    }
}
```

> `agg.tolerancePct` 在 `Aggregator` struct 里加一个字段，从 config (yaml/env) 注入，
> 默认值 `5`（对应 5%）。`agg.challengeQueue` 是 `chan ChallengeEntry`，M4 会消费。

---

## 编译 & 测试自检 checklist

在你 fork 出来的 `PriceOracle-AVS/` 目录下：

```bash
# 1. 接到 M1 推过来的合约改动后，重新生成 ABI binding（按 README）：
make bindings

# 2. 编译
go build ./aggregator/...

# 3. 跑 median 单元测试（你已经写好的 median_test.go）
go test -v ./aggregator/ -run "TestMedian|TestVariance|TestDetectOutliers"

# 4. 跑全套 race detector
go test -race -count=1 ./aggregator/...
```

如果 ① ② ③ ④ 都改完 + 单元测试全过，**M3 的代码部分就完成了**。
端到端联调要等 M1 / M2 / M4 把各自那块也提上来，你 rebase 一下就能跑
`make start-aggregator` 看到价格 task 真的被 squared … 啊不，被 medianed。

---

## 我（Claude）能立刻帮你做的事

1. M1 的 ABI 一推过来，我帮你写出**精确的 line-by-line patch**（不是伪代码，是真 diff）
2. `go build` / `go vet` 报错全贴给我，秒回 fix
3. integration test 失败时，把 anvil 的 log 全贴给我，我帮 trace BLS 失败原因
4. 跑通端到端后我把 `simulate_avs.py` 的图换成真实 Anvil 测得的 latency
