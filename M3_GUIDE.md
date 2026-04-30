# M3 行动手册 — Jon 负责 Aggregator 模块

> 你的目标：把 `aggregator/aggregator.go` 改造成中位数价格聚合器；写论文 §V（BLS聚合 + Median Consensus）。

---

## Step 0：环境搭建（~1小时）

> 在 **WSL2 Ubuntu 22.04** 里做。Windows 原生跑 EigenLayer 工具链经常有奇怪的兼容问题，WSL2 最稳。

### 0.1 装 WSL2 + Ubuntu（如果还没装）

PowerShell（管理员）：
```powershell
wsl --install -d Ubuntu-22.04
```

### 0.2 在 WSL2 里装依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 装基础工具
sudo apt install -y build-essential git curl wget make jq

# 装 Go 1.21+
wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc
go version  # 应该看到 go1.21.5

# 装 Foundry（含 anvil + forge + cast）
curl -L https://foundry.paradigm.xyz | bash
source ~/.bashrc
foundryup
anvil --version  # 应该有版本号

# 装 Docker（aggregator跑Prometheus要用）
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 注销重登一次让 docker 权限生效
```

### 0.3 Fork & Clone

1. 上 GitHub Fork：https://github.com/Layr-Labs/incredible-squaring-avs → 点右上角 Fork（Jon用自己账号fork，命名为 `PriceOracle-AVS`，然后给其他三个组员加 collaborator 权限）
2. Clone：
```bash
mkdir -p ~/6883 && cd ~/6883
git clone https://github.com/<your-github-username>/PriceOracle-AVS.git
cd PriceOracle-AVS
```

### 0.4 跑通原版 squaring demo

按照 [README](https://github.com/Layr-Labs/incredible-squaring-avs#readme) 走一遍：

```bash
# 终端1: 启动 anvil 链 + 部署 EigenLayer 合约
make start-anvil-chain-with-el-and-avs-deployed

# 终端2: 启动 aggregator
make start-aggregator

# 终端3: 启动 operator
make cli-setup-operator
make start-operator
```

**成功标志**：终端2 看到类似 `task index N completed, response: 0xN^2` 的日志。这一步通了你才有把握改造它。

---

## Step 1：理解原版 aggregator.go（~1小时）

打开 `aggregator/aggregator.go`，重点看这几个东西：

| 函数/结构 | 干啥的 | 你要改吗 |
|----------|------|---------|
| `Aggregator` struct | 聚合器主对象，含 logger、avsWriter、blsAggregationService | 改字段（加 mediancfg） |
| `Start(ctx)` | 主循环：每隔 N 秒发一个 task；监听 BLS aggregation service 的 response | 改 task 创建逻辑 |
| `sendNewTaskNumberToSquare(num)` | 调用 TaskManager 合约创建新task | **改名 + 改参数**为 `sendNewPriceTask(assetPair)` |
| `ProcessSignedTaskResponse(reply)` | RPC handler，operator 把签名响应通过这个传给 aggregator | 不改函数签名，改内部分发 |
| `sendAggregatedResponseToContract(blsAggServiceResp)` | 调 TaskManager.respondToTask 把聚合结果上链 | 改：传入 median 价格 + variance |

**给你打个标记**：用 `grep` 找你要改的位置：
```bash
cd ~/6883/PriceOracle-AVS
grep -n "numberToBeSquared\|NumberSquared\|sendNewTaskNumberToSquare" aggregator/*.go
```

---

## Step 2：在 outputs 里写 median.go skeleton（我来帮你写）

新建 `aggregator/median.go`，实现3个函数：
- `Median(prices []*big.Int) *big.Int`
- `Variance(prices []*big.Int, median *big.Int) *big.Int`
- `DetectOutliers(prices []*big.Int, median *big.Int, tolerancePct uint64) []int` — 返回偏离 median > tolerance% 的 operator 索引

这个文件**纯算法、零外部依赖**，可以离线写好测好再丢进 fork 里。

我已经在 `experiments/m3_aggregator/median.go` 给你写了一版，下一步去看。

---

## Step 3：改造 aggregator.go 的关键四处

> 等 contracts 那边（队友）把 ABI 生成好你才能跑通端到端。但你可以先按下面四处改，等他给你 commit 一推送，你 rebase 一下就行。

### 改动点 ① — Task struct 字段引用
全文搜 `numberToBeSquared` / `NumberToBeSquared`，替换成 `assetPair` / `AssetPair`。

### 改动点 ② — `sendNewTaskNumberToSquare` 改名+改逻辑
```go
// 原:
func (agg *Aggregator) sendNewTaskNumberToSquare(numToSquare *big.Int) error {
    newTask, taskIndex, err := agg.avsWriter.SendNewTaskNumberToSquare(...)
    ...
}

// 改成:
func (agg *Aggregator) sendNewPriceTask(assetPair string) error {
    newTask, taskIndex, err := agg.avsWriter.SendNewPriceTask(assetPair, QUORUM_THRESHOLD_NUMERATOR, QUORUM_NUMBERS)
    ...
}
```
然后在 `Start(ctx)` 主循环里把调用从 `sendNewTaskNumberToSquare(big.NewInt(int64(taskNum)))` 改成 `sendNewPriceTask("ETH/USD")`。

### 改动点 ③ — `ProcessSignedTaskResponse` 收集所有operator报价
原版的 BLS aggregation service 收到响应就直接验证签名 → 等阈值 → 上链。
**新版**额外做：把每个 operator 报的价格存进一个 map，等聚合完成后调用 `Median(prices)` 算共识价格。

### 改动点 ④ — `sendAggregatedResponseToContract` 传中位数
```go
func (agg *Aggregator) sendAggregatedResponseToContract(blsAggServiceResp blsagg.BlsAggregationServiceResponse) {
    // 新增: 从 agg.taskResponses[taskIndex] 取出所有 operator 报价
    prices := agg.collectPrices(blsAggServiceResp.TaskIndex)
    median := Median(prices)
    variance := Variance(prices, median)
    outliers := DetectOutliers(prices, median, agg.cfg.TolerancePct) // e.g., 5

    // 然后把 median + variance 传进 TaskResponse 上链
    taskResponse := taskmanager.IPriceOracleTaskManagerTaskResponse{
        ReferenceTaskIndex: blsAggServiceResp.TaskIndex,
        PriceMedian: median,
        PriceVariance: variance,
    }
    agg.avsWriter.SendAggregatedResponse(...)

    // 把 outliers 写到 challenge 队列（可选，给challenger用）
    for _, idx := range outliers {
        agg.challengeQueue <- ChallengeEntry{TaskIndex: ..., OperatorIdx: idx}
    }
}
```

---

## Step 4：写论文 §V（~5小时）

详细骨架我会单独给你一份 `experiments/m3_aggregator/section_V_skeleton.md`。先列结构，到时候填实验数据：

1. **Aggregator 节点职责**（150词）
2. **BLS 签名聚合数学**（200词）：
   - $\sigma_i = H(m)^{sk_i}$, $\sigma_{\text{agg}} = \prod_i \sigma_i$
   - Verify: $e(\sigma_{\text{agg}}, g_2) = e(H(m), \prod_i pk_i)$
3. **中位数 vs 算术平均**（200词）— 中位数对 outlier 的鲁棒性 (cite robust statistics)
4. **Tolerance 阈值灵敏度分析**（200词）— 5% 怎么定的，1%/3%/10% 各自漏报误报率
5. **性能数据**（100词）— 聚合延迟 vs operator 数量

---

## 你今晚的具体步骤

1. ✅ 读完这份 guide
2. 🔄 跑 Step 0 装 WSL2 + Go + Foundry + Docker
3. 🔄 fork repo，invite 三个组员
4. 🔄 跑通原版 squaring demo（看到 `task completed` 才算过关）
5. 📩 在群里同步：`PriceOracle-AVS` repo 已 fork 完毕，分支 `dev` 我来开

完成 Step 0-4 给我个反馈，我立刻把 `median.go` 和 `section_V_skeleton.md` 写出来给你。

如果遇到任何编译/运行错误，把报错完整贴给我我帮 debug。
