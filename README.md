# A-Share Claw（A股龙虾）

<p>
  <a href="#english"><img alt="English" src="https://img.shields.io/badge/Language-English-blue"></a>
  <a href="#chinese"><img alt="中文" src="https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E4%B8%AD%E6%96%87-red"></a>
</p>

---

<a id="english"></a>
## English

### What this is
A-Share Claw is an OpenClaw-based **A-share paper-trading automation workflow** with:
- scheduled runs on trading days (09:24 / 10:30 / 14:30)
- risk controls (single-symbol cap, total exposure cap, stale-order cancellation)
- daily review generation at 15:10

> For paper trading education only. Not financial advice.

### “One sentence to OpenClaw” auto install
Send this prompt directly to OpenClaw:

```text
Please one-click install and configure A-Share Claw on this machine: clone https://github.com/YoujunZhao/A-Share-Claw.git, run installer/install.sh, check whether ~/.openclaw/mx.env contains MX_APIKEY (if missing, ask me to provide), then verify cron has the 4 mx_autotrade jobs and report status.
```

If you already want it to set env too:

```text
Please one-click install A-Share Claw, write MX_APIKEY into ~/.openclaw/mx.env, complete installation verification, and report final status. Repo: https://github.com/YoujunZhao/A-Share-Claw.git
```

### Manual install (fallback)
```bash
git clone https://github.com/YoujunZhao/A-Share-Claw.git
cd A-Share-Claw
bash installer/install.sh
```

Set env:
```bash
cat > ~/.openclaw/mx.env <<'EOF'
export MX_APIKEY="your_key"
export MX_API_URL="https://mkapi2.dfcfs.com/finskillshub"
EOF
```

### Quick flow (3 steps)
1. Create and bind a tradable paper-trading portfolio in MX
2. Ask OpenClaw to perform one-click install (or run installer manually)
3. Let scheduled jobs run on trading days and generate review at 15:10

### Detailed workflow
#### 1) Schedule
- 09:24 pre-open scan + order attempt
- 10:30 intraday second scan
- 14:30 close-to-end run + cleanup
- 15:10 daily review generation

#### 2) Trading logic
- fetch candidates from stock-screen API
- check capital + position limits
- place orders and log each attempt

#### 3) Risk control
- `maxPositionPerStock` hard cap
- `maxTotalPosition` hard cap
- `maxTradesPerDay` daily cap
- auto-cancel stale pending orders (>20 mins)

#### 4) Logs and outputs
- strategy logs: `~/.openclaw/workspace/mx_autotrade/logs/YYYY-MM-DD.jsonl`
- global cron log: `~/.openclaw/workspace/mx_autotrade/cron.log`
- review output: `~/.openclaw/workspace/mx_autotrade/reviews/review-YYYY-MM-DD.json`

#### 5) Tunable params
Config file: `~/.openclaw/workspace/mx_autotrade/config.json`

Common params:
- `maxTradesPerDay` (default 6)
- `maxPositionPerStock` (default 0.15)
- `maxTotalPosition` (default 0.60)
- `runTimes` (default `09:24/10:30/14:30`)

---

<a id="chinese"></a>
## 中文

### 这是什么
A股龙虾（A-Share Claw）是一个基于 OpenClaw 的 **A股模拟盘自动交易流程**，包含：
- 交易日自动执行（09:24 / 10:30 / 14:30）
- 风控（单票仓位上限、总仓位上限、超时挂单撤单）
- 每日复盘（15:10 自动输出）

> 仅用于模拟盘学习，不构成投资建议。

### 你要的“一句话给 OpenClaw 就自动安装配置”
把下面这句话直接发给你的 OpenClaw：

```text
请在我的机器上一键安装并配置 A-Share Claw（A股龙虾）：克隆 https://github.com/YoujunZhao/A-Share-Claw.git，执行 installer/install.sh，检查 ~/.openclaw/mx.env 是否有 MX_APIKEY（没有就提醒我补），安装后验证 crontab 里有 mx_autotrade 的 4 条定时任务，并回报结果。
```

如果你已经有 key，也可以用这个版本（让它直接配置）：

```text
请一键安装 A-Share Claw，并把 MX_APIKEY 配到 ~/.openclaw/mx.env，然后完成安装验证。仓库：https://github.com/YoujunZhao/A-Share-Claw.git
```

### 手动安装（备用）
```bash
git clone https://github.com/YoujunZhao/A-Share-Claw.git
cd A-Share-Claw
bash installer/install.sh
```

配置环境变量：
```bash
cat > ~/.openclaw/mx.env <<'EOF'
export MX_APIKEY="你的key"
export MX_API_URL="https://mkapi2.dfcfs.com/finskillshub"
EOF
```

### 简易流程（3步）
1. 在妙想页面创建并绑定“可交易模拟组合”
2. 让 OpenClaw 执行一键安装（或手动执行安装脚本）
3. 等待交易日自动执行，15:10 自动复盘

### 详细流程（完整）
#### 1) 自动执行时点
- 09:24：竞价前扫描并尝试下单
- 10:30：盘中第二轮扫描
- 14:30：尾盘执行 + 风控清理
- 15:10：生成每日复盘

#### 2) 交易逻辑
- 从选股接口获取候选
- 结合当前仓位与资金判断是否开仓
- 下单后记录日志（可追踪）

#### 3) 风控逻辑
- `maxPositionPerStock`：单票仓位上限
- `maxTotalPosition`：总仓位上限
- `maxTradesPerDay`：每日最多交易笔数
- 超过 20 分钟未成交挂单自动撤单

#### 4) 输出与日志
- 策略日志：`~/.openclaw/workspace/mx_autotrade/logs/YYYY-MM-DD.jsonl`
- 总日志：`~/.openclaw/workspace/mx_autotrade/cron.log`
- 每日复盘：`~/.openclaw/workspace/mx_autotrade/reviews/review-YYYY-MM-DD.json`

#### 5) 可调参数
配置文件：`~/.openclaw/workspace/mx_autotrade/config.json`

常用参数：
- `maxTradesPerDay`（默认 6）
- `maxPositionPerStock`（默认 0.15）
- `maxTotalPosition`（默认 0.60）
- `runTimes`（默认 `09:24/10:30/14:30`）
