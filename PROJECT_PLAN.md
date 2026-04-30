# EE6883 Final Project — V4 计划（Restaking AVS方案）

**Title**: *PriceOracle-AVS: A Modified EigenLayer Actively Validated Service for Decentralized Price Feeds — Implementation, Analysis, and Security Considerations*

**Course**: EE6883 (Innovations in Blockchain Technology)
**Topic chosen**: #5 Ethereum ReStaking
**Team**: 4 人，每人 ~15h，公平分配
**Deadline**: 2026-05-07
**Format**: IEEE double-column, 4–6 页

---

## 1. 总思路

**Fork** [Layr-Labs/incredible-squaring-avs](https://github.com/Layr-Labs/incredible-squaring-avs)（EigenLabs官方"AVS Hello World"教学模板）→ **改造**为一个有实际意义的AVS：**链下ETH/USD价格预言机**——operators从不同CEX拉价格，通过BLS签名聚合达成共识，价格偏离会被slash。

**为什么选这个改造方向**：
- 比"求平方"有实际意义（DeFi预言机是真实需求）
- 充分体现 restaking 价值：ETH经济安全保护链下数据真实性
- 4个模块（合约/operator/aggregator/challenger）天然适配4人分工
- 可以在论文里和 Chainlink、Pyth、UMA 等中心化/半中心化预言机做对比

---

## 2. 论文结构（IEEE 4-6页）

| § | 标题 | 长度 | 负责 |
|---|------|------|------|
| I | Introduction & Background | 0.5 页 | M4 |
| II | EigenLayer Restaking Architecture | 0.5 页 | M4 |
| III | PriceOracle-AVS Smart Contract Design | 1.0 页 | **M1** |
| IV | Operator Implementation: Multi-CEX Price Aggregation | 1.0 页 | **M2** |
| V | Aggregator: BLS Signature & Median Consensus | 1.0 页 | **M3** |
| VI | End-to-End Evaluation & Comparison | 0.8 页 | M4 |
| VII | Discussion: Slashing, Liveness, Comparison with Chainlink | 0.4 页 | 合写 |
| VIII | Conclusion + Member Contributions | 0.3 页 | M4 |
| — | References (≥18条) | — | All |

总长 ~5.5 页，留弹性。

---

## 3. Repository 实际结构与4人分工映射

```
incredible-squaring-avs/
├── contracts/                      ← M1 负责
│   └── src/
│       ├── IncredibleSquaringServiceManager.sol  → PriceOracleServiceManager.sol
│       ├── IncredibleSquaringTaskManager.sol     → PriceOracleTaskManager.sol
│       └── ERC20Mock.sol
├── operator/                       ← M2 负责
│   └── operator.go                 → 改: 替换squaring → CEX API price fetch
├── aggregator/                     ← M3 负责
│   └── aggregator.go               → 改: 求和 → 中位数聚合 + tolerance check
├── challenger/                     ← M4 负责（部分）
│   └── challenger.go               → 改: 独立验证价格响应
├── tests/
│   └── anvil/                      ← M4 负责测试
└── README.md
```

每人改一个模块，互不踩脚，可以并行开发。

---

## 4. 4人详细分工（每人 ~15h，工作量均等）

> 详见 `REPO_AND_TASKS.md`

| 成员 | 模块 | 改造内容 | 章节 |
|------|------|----------|------|
| **M1 (Jon)** | `contracts/` Solidity合约 | 改ServiceManager + TaskManager，加价格偏离slashing | §III |
| **M2** | `operator/` Go客户端 | 把squaring换成CEX API price fetch (Binance/Coinbase/Kraken) | §IV |
| **M3** | `aggregator/` Go聚合器 | 求和聚合改成中位数聚合，加tolerance阈值 | §V |
| **M4** | `challenger/` + 测试 + 部署 | 改challenger，写anvil测试，写Holesky部署脚本 | §I/II/VI/VII/VIII（写作主力） |

工作量校准：
- **M1/M2/M3**：~5h写代码 + ~5h跑测试出图 + ~5h写论文章节 = 15h
- **M4**：~3h写代码（challenger较简单）+ ~4h端到端测试 + ~8h写多个章节（写作偏重） = 15h

---

## 5. 论文 Novelty —— Introduction 三条 Contributions

> **Contributions**:
> 1. We design and implement **PriceOracle-AVS**, a working modification of the EigenLayer Incredible Squaring AVS template that turns it into a decentralized ETH/USD price oracle, demonstrating how the AVS pattern generalizes from toy compute to economically meaningful services.
> 2. We propose a **slashing rule based on price deviation** that punishes operators whose individually reported prices deviate from the BLS-aggregated consensus by more than a configurable threshold (5% in our deployment), and analyze its game-theoretic incentive properties.
> 3. We provide **an end-to-end evaluation on a local Anvil testnet**, including BLS signature verification gas cost, end-to-end latency from task creation to on-chain response, and cost comparison against Chainlink Price Feeds, the dominant centralized-operator oracle solution.

这三点都不是综述性的——是基于你们的 fork 改造后的实测数据。

---

## 6. 引用清单（≥18条，≥5 peer-reviewed）

### Restaking 核心
1. EigenLabs. "EigenLayer: The Restaking Collective." Whitepaper, 2023.
2. Durvasula, N. and Roughgarden, T. "Robust Restaking Networks." 2024. ✅peer
3. Mohan, M. et al. "Cryptoeconomic Security for Data Availability Committees." 2024.
4. Symbiotic Whitepaper, 2024.
5. Karak Network technical doc, 2024.

### BLS & 多签
6. Boneh, D., Lynn, B., Shacham, H. "Short signatures from the Weil pairing." J. Cryptology 2004. ✅peer
7. Boneh, D. et al. "BLS Multi-Signatures with Public-Key Aggregation." 2018. ✅peer
8. EIP-2537 (BLS12-381 precompile)

### EigenLayer 工程
9. Layr-Labs/incredible-squaring-avs GitHub repo
10. EigenLayer "AVS Risk Framework"
11. Movement Labs AVS tutorial
12. AVS Book (eigenlabs.gitbook.io)

### 预言机对比
13. Chainlink Whitepaper 2.0. Breidenbach et al. 2021.
14. Pyth Network Whitepaper, 2023.
15. UMA Optimistic Oracle paper, 2020.
16. Adler, J. et al. "Astraea: A Decentralized Blockchain Oracle." 2018. ✅peer

### 经济模型 & 通用区块链
17. Buterin, V. "Ethereum Whitepaper." 2014.
18. Gencer, A.E. et al. "Decentralization in Bitcoin and Ethereum." 2018. ✅peer

总计 18 条，含 6 篇 peer-reviewed（满足 ≥5 要求）。

---

## 7. 时间表

| 日期 | M1 (Jon) | M2 | M3 | M4 |
|------|------|------|------|------|
| 4/28 | Fork repo, 装Foundry+Go+Anvil, 跑通原版 | 同左 (clone repo) | 同左 | 同左 + 读EigenLayer白皮书 |
| 4/29 | 重命名contracts，定义新Task struct | 写CEX API client (Binance) | 改aggregator task generation | 写§I §II 初稿 |
| 4/30 | 加 deviation slashing 函数 | 加 Coinbase + Kraken | 实现median聚合 + tolerance | 改challenger logic |
| 5/1 | Foundry测试 + §III初稿 | operator端到端调通 + §IV初稿 | aggregator端到端调通 + §V初稿 | anvil端到端跑通 + §VI |
| 5/2 | finalize §III + figs | finalize §IV + figs | finalize §V + figs | §VII + §VIII + .bib |
| 5/3 | merge LaTeX | review/proofread | review/proofread | 整合全文 |
| 5/4 | 控制页数 | proofread | proofread | proofread |
| 5/5 | 第二稿review | — | — | — |
| 5/6 | 缓冲日，查重 | — | — | — |
| **5/7** | 提交（M1是first author） | — | — | — |

---

## 8. 风险与对策

- **Go不熟**：M2/M3可考虑用 [zellular-xyz/incredible-squaring-avs-js](https://github.com/zellular-xyz/incredible-squaring-avs-js)（JS版） 或 [Layr-Labs/incredible-squaring-avs-rs](https://github.com/Layr-Labs/incredible-squaring-avs-rs)（Rust版）
- **CEX API限速/被墙**：用 CoinGecko 这类聚合API代替，或用历史CSV离线测试
- **Holesky部署失败**：保留anvil本地端到端作为backup（足够论文使用）
- **论文页数超限**：把代码片段压缩到关键3-5行，削减背景章节

---

## 9. Claude 全程协助

- ✅ 已写好的：项目计划、4人详细任务、引用清单
- 接下来可以做：
  - A. 写 `setup_dev.sh` 一键搭好Foundry+Go+Anvil
  - B. 起草 IEEE LaTeX 模板骨架（4 sections占位 + .bib初版）
  - C. 给 M1/M2/M3/M4 各写一份详细的"如何改造你的模块" briefing（包含具体哪个文件改哪几行）
  - D. 写好之后整合 LaTeX + 控页数 + proofread

---

## 10. 下一步

回我 "开始 D" 我就把 A+B+C 全做了（一次性铺好所有人的起跑线）。
回 "A"/"B"/"C" 单独某个我就只做那个。
