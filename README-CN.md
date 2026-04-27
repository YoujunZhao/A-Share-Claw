<div align="center">

<img src="./assets/logo.jpg" alt="A股龙虾 Logo" width="350" />

# A股龙虾

| Day | Balance | 当日收益率 | Day | Balance | 当日收益率 |
|---|---:|---:|---|---:|---:|
| Day1 | +0.00% | 0.00% | Day2 | -0.57% | -0.57% |
| Day3 | -0.64% | -0.08% | Day4 | -0.60% | +0.04% |
| Day5 | -1.83% | -1.23% | Day6 | -1.19% | +0.65% |
| Day7 | -1.74% | -0.56% | Day8 | -2.05% | -0.31% |
| Day9 | -1.07% | +1.00% | Day10 | -0.08% | +1.00% |
| Day11 | -0.26% | -0.18% | Day12 | -0.40% | -0.14% |
| Day13 | -0.08% | +0.32% | Day14 | -0.40% | -0.31% |
| Day15 | -0.46% | -0.07% | Day16 | -0.41% | +0.05% |
| Day17 | -0.09% | +0.33% | Day18 | +0.03% | +0.11% |
| Day19 | +0.60% | +0.57% | Day20 | +0.60% | +0.00% |
| Day21 | +0.44% | -0.16% | Day22 | +0.17% | -0.27% |
| Day23 | 200,197.22 | -0.08% |

[![English](https://img.shields.io/badge/Language-English-blue)](./README.md)
[![中文](https://img.shields.io/badge/语言-中文-red)](./README-CN.md)

</div>

这是一个基于 OpenClaw 的 **A股模拟盘自动交易流程**，包含：
- 交易日自动执行（09:24 / 10:30 / 14:30）
- 风控（单票仓位上限、总仓位上限、超时挂单撤单）
- 每日复盘（15:10 自动输出）

> 仅用于模拟盘学习，不构成投资建议。

## 一句话自动安装提示词 (OpenClaw)

把下面这句话直接发给 OpenClaw：

```text
请在我的机器上一键安装并配置 A-Share Claw（A股龙虾）：先执行 `git clone https://github.com/YoujunZhao/A-Share-Claw.git`，再执行 `installer/install.sh`，检查 `~/.openclaw/mx.env` 是否有 `MX_APIKEY`（没有就提醒我补），安装后验证 crontab 里有 `mx_autotrade` 的 6 条定时任务（5 个交易时点 + 1 个每日复盘），并回报结果。
```

## 手动安装

```bash
git clone https://github.com/YoujunZhao/A-Share-Claw.git
cd A-Share-Claw
bash installer/install.sh
```

```bash
cat > ~/.openclaw/mx.env <<'EOF'
export MX_APIKEY="你的key"
export MX_API_URL="https://mkapi2.dfcfs.com/finskillshub"
EOF
```

## 详细流程

### 1）安装
  - 选择一键安装 （发送安装提示词给OpenClaw）或者手动安装。

### 2）账户准备
- 下载东方财富APP，注册账号
- APP打开搜索：妙想skills。复制提示词 & Key，发给OpenClaw。
- 在妙想创建模拟交易账户。
- 绑定可交易组合，并设为当前/默认组合。
- 接口自检通过：`balance/positions` 返回成功，而不是“请先绑定账户”。


## 交易策略

### 1）定时任务（自动执行）
当前策略在 5 个交易时点执行：
- 09:24 竞价前扫描并尝试下单
- 10:30 盘中扫描
- 11:30 盘中扫描
- 13:30 盘中扫描
- 14:30 尾盘风险优先执行 + 可选继续买入
- 15:10 生成每日复盘

### 2）候选股筛选流程
当前采用四层流程后再决定是否下单：
- **Layer 1 – 资讯/题材发现：** 根据市场热点关键词搜索短线 A 股候选。
- **Layer 2 – 财务过滤：** 在数据可用时做轻量 PE / ROE / 利润增速过滤。
- **Layer 3 – 自选股同步：** 将通过筛选的标的同步到自选/候选池。
- **Layer 4 – 交易执行：** 只有在资金、仓位、手数约束全部通过后才发起模拟交易。

默认情况下，财务层和自选股层为 fail-open，只有在 strict 模式开启时才会严格拦截。

### 3）买入逻辑
- 通过四层流程拿到候选列表。
- 若触发每日次数、可用资金、单票仓位或总仓位限制，则跳过新买入。
- 优先选择仍低于单票仓位上限的候选标的。
- 按受控手数和市价方式提交买单。
- 每笔委托请求与返回结果都会写入日志。

### 4）卖出 / 调仓逻辑
当前策略已经不是“只买不卖”，而是包含以下卖出动作：
- **单票超限立即减仓：** 某只股票超过 `maxPositionPerStock` 时，立即卖出至限制以内。
- **持仓超时弱势退出：** 持仓跨越多个运行时点后仍偏弱，则卖出。
- **14:30 尾盘弱仓清理：** 对已不在候选池、且表现偏弱的持仓进行卖出。
- **14:30 更强候选主动换仓：** 比较最强新候选与最弱旧持仓，当分差足够大时，先卖旧仓，再由后续买入流程换入更强标的。

### 5）风控逻辑
- 单票仓位硬限制：`maxPositionPerStock`。
- 总仓位硬限制：`maxTotalPosition`。
- 每日交易次数限制：`maxTradesPerDay`。
- 挂单超时自动撤单（>20 分钟未成交）。
- 现金不足或触发仓位限制时自动跳过开仓。
- 14:30 采用**风险优先**窗口，是否允许风控后继续买入由 `allowBuyAt1430` 控制。

### 6）每日复盘流程
- 15:10 自动读取资金、持仓、委托。
- 生成结构化 JSON 复盘报告。
- 用于审计、策略优化和 Telegram 推送。

### 7）日志与产物
- 策略日志：`~/.openclaw/workspace/mx_autotrade/logs/YYYY-MM-DD.jsonl`
- 总日志：`~/.openclaw/workspace/mx_autotrade/cron.log`
- 每日复盘：`~/.openclaw/workspace/mx_autotrade/reviews/review-YYYY-MM-DD.json`
- 运行状态：`~/.openclaw/workspace/mx_autotrade/state.json`

### 8）参数调优
生效配置文件：
- `~/.openclaw/workspace/mx_autotrade/config.json`

当前仓库默认参数：
- `maxTradesPerDay`：`6`
- `maxPositionPerStock`：`0.08`
- `maxTotalPosition`：`0.60`
- `runTimes`：`09:24 / 10:30 / 11:30 / 13:30 / 14:30`
- `allowBuyAt1430`：`true`
- `autoTuneApply`：`true`