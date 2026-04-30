# 4人详细任务清单 — V4.1（PriceOracle-AVS方案）

**Base repo**: [Layr-Labs/incredible-squaring-avs](https://github.com/Layr-Labs/incredible-squaring-avs)
**Modification target**: 改造为 **PriceOracle-AVS**——operators从CEX拉ETH/USD价格，BLS聚合达成共识，价格偏离会被slash
**人均工作量**: ~15 hours

## 最新分工表（V4.1）

| 成员 | 模块 | 章节 | 备注 |
|------|------|------|------|
| 队友（Solidity熟） | `contracts/` Solidity合约 | §III | 顶替原M1 |
| M2 | `operator/` Go客户端 | §IV | 4个CEX API |
| **Jon** | `aggregator/` Go聚合器 ⭐ | §V | 中位数+BLS聚合 |
| M4 | `challenger/` + 测试 + 多section写作 | §I/II/VI/VII/VIII | 写作偏重 |

---

## 0. 全员前置（4月28日，每人独立做）

```bash
# 1. Fork repo（M1上GitHub fork成 6883-team/PriceOracle-AVS，给所有人推送权限）
# 2. Clone：
git clone https://github.com/<your-team>/PriceOracle-AVS.git
cd PriceOracle-AVS

# 3. 装依赖：
# - Foundry (Solidity 测试框架): curl -L https://foundry.paradigm.xyz | bash && foundryup
# - Go 1.21+: 官网下载
# - Anvil (随Foundry一起): 本地测试链
# - Make
```

**所有人 Day 1 跑通原版 squaring demo**：按 [README](https://github.com/Layr-Labs/incredible-squaring-avs#readme) 执行 `make build-contracts && make start-anvil-chain-with-eigenlayer-deployed && make start-aggregator && make start-operator` —— 看到 task 被 square 并响应，环境就成了。

---

## 👤 M1 — Jon — Smart Contracts

### 改造目标
把 `IncredibleSquaringServiceManager.sol` / `IncredibleSquaringTaskManager.sol` 改造为 `PriceOracleServiceManager.sol` / `PriceOracleTaskManager.sol`。

### 具体改动（~5h）

**文件 1**: `contracts/src/IncredibleSquaringTaskManager.sol`
- 重命名为 `PriceOracleTaskManager.sol`
- 改 `Task` struct：
  ```solidity
  // 原:
  struct Task {
      uint32 numberToBeSquared;
      uint32 taskCreatedBlock;
      bytes quorumNumbers;
      uint32 quorumThresholdPercentage;
  }
  // 改成:
  struct Task {
      string assetPair;        // "ETH/USD"
      uint32 taskCreatedBlock;
      bytes quorumNumbers;
      uint32 quorumThresholdPercentage;
  }
  ```
- 改 `TaskResponse` struct：
  ```solidity
  struct TaskResponse {
      uint32 referenceTaskIndex;
      uint256 priceMedian;     // 6 decimals, e.g., 3500_000000 = $3500.00
      uint256 priceVariance;   // 偏离度
  }
  ```
- 加新函数：`raiseAndResolveDeviationChallenge(taskIndex, operatorAddress, operatorReportedPrice)` — 如果某operator报的价格偏离consensus >5%，slash

**文件 2**: `contracts/src/IncredibleSquaringServiceManager.sol`
- 重命名为 `PriceOracleServiceManager.sol`
- 改名引用 + emit event 时携带新字段

**文件 3**: 新建 `contracts/test/PriceOracleTaskManager.t.sol`
- Foundry 单元测试：测试 Task 创建、Response 提交、Challenge raise、Slashing
- 至少 5 个测试用例

### 论文章节（~5h）
**§III PriceOracle-AVS Smart Contract Design** （~1页）
段落骨架：
1. ServiceManager 与 TaskManager 的职责（150词）
2. Task 与 TaskResponse 数据结构（含代码片段，~150词）
3. **Deviation Slashing Rule** 设计动机与公式（~250词）：
   - $\text{slash}(o_i)$ if $|p_i - \text{median}(P)| / \text{median}(P) > 5\%$
   - 给一段 incentive analysis：为什么operator说真话是Nash均衡
4. Foundry测试覆盖率截图（~100词）

**输出**：1张 contract architecture diagram + 1张 deviation slashing 逻辑流程图

### 读这5篇 (~5h)
1. EigenLayer Whitepaper（重点：ServiceManager接口）
2. Durvasula & Roughgarden "Robust Restaking Networks" 2024
3. EigenLayer "AVS Risk Framework"
4. Chainlink Whitepaper 2.0（slashing 设计参考）
5. Boneh "BLS Multi-Signatures" 2018

### 额外职责
- repo 的 fork 维护者（merge其他人的PR）
- LaTeX 整合 + 提交（first author）

---

## 👤 M2 — Operator (Go)

### 改造目标
把 `operator/operator.go` 里的 `taskCompletion` 函数从"求平方"改为"从CEX拉ETH/USD价格"。

### 具体改动（~5h）

**文件**: `operator/operator.go`

**原逻辑**（伪代码）：
```go
func (o *Operator) ProcessNewTaskCreatedLog(newTask *Task) *TaskResponse {
    return &TaskResponse{
        NumberSquared: newTask.NumberToBeSquared * newTask.NumberToBeSquared,
    }
}
```

**新逻辑**：
```go
func (o *Operator) ProcessNewTaskCreatedLog(newTask *Task) *TaskResponse {
    // 根据 OPERATOR_CEX_SOURCE 环境变量决定从哪家CEX拉数据
    // 4个operator分别从 Binance / Coinbase / Kraken / OKX
    price := fetchPriceFromCEX(o.cexSource, newTask.AssetPair)
    return &TaskResponse{
        ReferenceTaskIndex: newTask.TaskIndex,
        ReportedPrice: price,
    }
}

func fetchPriceFromCEX(source, pair string) uint256 {
    switch source {
    case "binance":
        return fetchBinance(pair)
    case "coinbase":
        return fetchCoinbase(pair)
    // ...
    }
}
```

**新建文件**: `operator/cex_client.go`
- `fetchBinance(pair)` → REST `https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT`
- `fetchCoinbase(pair)` → `https://api.exchange.coinbase.com/products/ETH-USD/ticker`
- `fetchKraken(pair)` → `https://api.kraken.com/0/public/Ticker?pair=ETHUSD`
- 加超时、重试、错误处理

**测试**：跑3-4个operator并发，每个连不同CEX，看aggregator能否收到

### 论文章节（~5h）
**§IV Operator Implementation: Multi-CEX Price Aggregation** （~1页）
段落骨架：
1. Operator 节点角色（150词）
2. CEX API 接入（含代码片段，~200词）
3. BLS 签名生成与发送（~150词）
4. **Decentralization analysis**：为什么用4家不同CEX是关键设计决策（~200词）
5. 性能数据：API延迟分布、成功率（~100词）

**输出**：1张operator架构图 + 1张4家CEX价格延迟箱线图

### 读这5篇 (~5h)
1. EigenLayer AVS Operator Guide
2. Pyth Network Whitepaper（多源聚合参考）
3. UMA Optimistic Oracle paper
4. Boneh "Short signatures from the Weil pairing" 2004
5. Adler "Astraea: A Decentralized Blockchain Oracle" 2018

---

## 👤 M3 — Aggregator (Go)

### 改造目标
把 `aggregator/aggregator.go` 里的求和聚合改成**中位数聚合**，加 tolerance 机制。

### 具体改动（~5h）

**文件**: `aggregator/aggregator.go`

**原逻辑**：每隔10秒生成一个 squaring task，operators 算完后 BLS 聚合签名，提交链上。

**新逻辑**：
1. **Task generation 改造**：每5秒发一个 `assetPair: "ETH/USD"` 的 task
2. **Response collection**：等待 quorum threshold (e.g., 67% operators 响应) 后聚合
3. **Median 聚合**：
   ```go
   func aggregatePrices(responses []TaskResponse) (median, variance uint256) {
       prices := []uint256{}
       for _, r := range responses {
           prices = append(prices, r.ReportedPrice)
       }
       sort(prices)
       median = prices[len(prices)/2]
       variance = calculateVariance(prices, median)
       return
   }
   ```
4. **Outlier detection**：算完 median 后，标记任何偏离 >5% 的 operator → 写到 challenge 队列里

**新建**：`aggregator/median.go` 实现 median + variance + outlier detection

### 论文章节（~5h）
**§V Aggregator: BLS Signature & Median Consensus** （~1页）
段落骨架：
1. Aggregator 节点职责（150词）
2. BLS 签名聚合数学（~200词）：$\sigma_{\text{agg}} = \prod \sigma_i$, $\text{verify}(\sigma_{\text{agg}}, \prod pk_i, m)$
3. 中位数聚合 vs 算术平均（中位数对outlier鲁棒）（~200词）
4. Tolerance 阈值的选择（5%）的灵敏度分析（~200词）
5. 性能：聚合延迟 vs operator数量（~100词）

**输出**：1张BLS聚合流程图 + 1张tolerance参数sensitivity图

### 读这5篇 (~5h)
1. Boneh-Lynn-Shacham "Short signatures from the Weil pairing" 2004
2. Boneh "BLS Multi-Signatures with Public-Key Aggregation" 2018
3. EigenLayer BLS Aggregation 文档
4. Symbiotic Whitepaper
5. Karak Network technical doc

---

## 👤 M4 — Challenger + Tests + Documentation + Writing-heavy

### 改造目标
- 改 `challenger/challenger.go` 让它独立验证aggregator的价格响应
- 写完整的 anvil 端到端测试
- 写 Holesky testnet 部署脚本（可选）
- **写论文最多的章节**（4个其他人各写1节，M4 写 4 节但都较短）

### 具体改动（~3h，代码相对最少）

**文件1**: `challenger/challenger.go`
- 监听 `TaskRespondedEvent`
- 独立从一个第四个CEX（如 Bitfinex）拉价格作为参考
- 如果 aggregator 报的 median 与参考偏离 >5%，调用 `raiseAndResolveDeviationChallenge`

**文件2**: `tests/integration/e2e_test.sh`
- bash 脚本：启动 anvil → deploy contracts → 启 aggregator → 启4个 operator → 跑10分钟 → 收集log → assert至少有N次成功task响应

**文件3**: `Makefile`
- 加 `make e2e-test`、`make deploy-holesky`

### 论文章节（~8h，写作主力）

**§I Introduction** （~0.5页）
- 问题：DeFi 预言机被中心化操控的历史问题
- 我们的方案：基于 EigenLayer restaking 的去中心化预言机
- 三条 contributions

**§II EigenLayer Restaking Architecture** （~0.5页）
- staking → restaking 的演进
- ServiceManager / Operator / AVS / Slashing 四角色
- 一张EigenLayer架构图

**§VI End-to-End Evaluation & Comparison** （~0.8页）
- 实验环境：Anvil本地链 + 4个operator + 1 aggregator + 1 challenger
- 指标：
  - 单个 task 端到端延迟（task creation → on-chain response）
  - BLS verification gas cost
  - Operator 报价方差（4家CEX之间的天然分歧）
  - vs Chainlink ETH/USD price feed 的对比表
- 至少3张图

**§VII Discussion** （~0.4页）
- Liveness 风险
- Slashing 经济性分析
- vs Chainlink/Pyth/UMA 的差异
- Future work: 接入真实Holesky testnet

**§VIII Conclusion + Member Contributions** （~0.3页）
- 4人具体贡献paragraph

### 读这5篇 (~4h)
1. Chainlink Whitepaper 2.0
2. Pyth Network Whitepaper
3. UMA Optimistic Oracle paper
4. Buterin "Ethereum Whitepaper"
5. Gencer "Decentralization in Bitcoin and Ethereum" 2018

### 额外职责
- 维护 `references.bib`（≥18条）
- 论文 final proofread

---

## 共享工具

- **GitHub repo**（M1 fork 出来的）：所有代码改动走 PR，互相 review
- **Overleaf 共享 LaTeX 工程**：4人同时编辑
- **Zotero 共享库**（M4 管理）：≥18 条 references
- **微信/Discord 群**：每天晚上 10 分钟同步

---

## 工作流时序（避免互相阻塞）

```
Day 1 (4/28): 全员搭环境，跑通原版demo                      [并行]
Day 2 (4/29): M1改contracts定义 → push一版让M2/M3知道接口   [M1先跑]
              M2/M3/M4 同时各自模块开始改                    [并行]
Day 3 (4/30): M1完成contracts，M2/M3完成代码，M4开始整合     [并行]
Day 4 (5/1): M4跑端到端测试，4人开始写各自section            [并行]
Day 5 (5/2): 各章节initial draft完成                         [并行]
Day 6 (5/3): M4整合LaTeX，全员交叉review                     [汇聚]
Day 7-9 (5/4-5/6): 第二稿 + 控页数 + 查重                    [汇聚]
Day 10 (5/7): 提交                                          [M1]
```

---

## 下一步（你回我）

**A**：写 `setup_dev.sh`（一键搭好Foundry+Go+Anvil，跑通原版demo）
**B**：起草 IEEE LaTeX 模板骨架（4 sections占位 + .bib初版）
**C**：给 M1/M2/M3/M4 每人写一份"如何改造你的模块"详细 briefing（直接告诉他们改哪个文件第几行）
**D**：A+B+C 全做（推荐，把所有人起跑线一次铺好）

回 D 我立刻动手做这3件。
