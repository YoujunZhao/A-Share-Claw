<div align="center">

<img src="./assets/logo.jpg" alt="A股龙虾 Logo" width="350" />

# A股龙虾

| Day | 余额 | 当日收益率 |
|---|---:|---:|
| Day1 | 200,000.00 | 0.00% |
| Day2 | 198,867.21 | -0.57% |
| Day3 | 198,711.30 | -0.08% |
| Day4 | 198,791.28 | +0.04% |
| Day5 | 196,340.25 | -1.23% |
| Day6 | 197,616.03 | +0.65% |
| Day7 | 196,516.19 | -0.56% |
| Day8 | 195,901.15 | -0.31% |
| Day9 | 197,862.20 | +1.00% |

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
请在我的机器上一键安装并配置 A-Share Claw（A股龙虾）：先执行 `git clone https://github.com/YoujunZhao/A-Share-Claw.git`，再执行 `installer/install.sh`，检查 `~/.openclaw/mx.env` 是否有 `MX_APIKEY`（没有就提醒我补），安装后验证 crontab 里有 `mx_autotrade` 的 4 条定时任务，并回报结果。
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
安装脚本会写入 4 条交易日定时任务：
- 09:24 竞价前扫描并尝试下单
- 10:30 盘中第二轮扫描
- 14:30 尾盘执行 + 风控清理
- 15:10 生成每日复盘

### 2）交易执行逻辑
- 从选股接口拉取候选标的。
- 下单前检查仓位限制与可用资金。
- 按控制后的手数提交买单。
- 每笔委托和返回结果都写入日志。

### 3）风控逻辑
- 单票仓位硬限制：`maxPositionPerStock`。
- 总仓位硬限制：`maxTotalPosition`。
- 每日交易次数限制：`maxTradesPerDay`。
- 挂单超时自动撤单（>20 分钟未成交）。
- 现金不足或触发仓位限制时自动跳过开仓。

### 4）每日复盘流程
- 15:10 自动读取资金、持仓、委托。
- 生成结构化 JSON 复盘报告。
- 用于审计、策略优化和 Telegram 推送。

### 5）日志与产物
- 策略日志：`~/.openclaw/workspace/mx_autotrade/logs/YYYY-MM-DD.jsonl`
- 总日志：`~/.openclaw/workspace/mx_autotrade/cron.log`
- 每日复盘：`~/.openclaw/workspace/mx_autotrade/reviews/review-YYYY-MM-DD.json`

### 6）参数调优
生效配置文件：
- `~/.openclaw/workspace/mx_autotrade/config.json`

常用参数：
- `maxTradesPerDay`（默认 6）
- `maxPositionPerStock`（默认 0.15）
- `maxTotalPosition`（默认 0.60）
- `runTimes`（默认 `09:24/10:30/14:30`）