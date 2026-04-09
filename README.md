<div align="center">

<img src="./assets/logo.jpg" alt="A-Share Claw Logo" width="350" />

# A-Share Claw

| Day | Balance | Daily Return |
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
| Day10 | 199,835.15 | +1.00% |
| Day11 | 199,483.06 | -0.18% |

[![English](https://img.shields.io/badge/Language-English-blue)](./README.md)
[![中文](https://img.shields.io/badge/语言-中文-red)](./README-CN.md)

</div>

An OpenClaw-based **A-share paper-trading automation workflow** with:
- scheduled runs on trading days (09:24 / 10:30 / 14:30)
- risk controls (single-symbol cap, total exposure cap, stale-order cancellation)
- daily review generation at 15:10

> For paper trading education only. Not financial advice.

## One-sentence auto setup prompt (OpenClaw)

Send this directly to OpenClaw:

```text
Please one-click install and configure A-Share Claw (A股龙虾) on my machine: first run `git clone https://github.com/YoujunZhao/A-Share-Claw.git`, then run `installer/install.sh`, check whether `~/.openclaw/mx.env` contains `MX_APIKEY` (if missing, remind me to provide it), and finally verify that crontab contains the 4 `mx_autotrade` scheduled jobs and report the results.
```

## Manual setup

```bash
git clone https://github.com/YoujunZhao/A-Share-Claw.git
cd A-Share-Claw
bash installer/install.sh
```

```bash
cat > ~/.openclaw/mx.env <<'EOF'
export MX_APIKEY="your_key"
export MX_API_URL="https://mkapi2.dfcfs.com/finskillshub"
EOF
```

## Detailed workflow

### 1) Installation
- Choose one-click installation (send the setup prompt to OpenClaw) or manual installation.

### 2) Account preparation
- Download the Eastmoney app and register an account.
- In the app, search for: `妙想skills`.
- Copy the prompt text and API key, then send them to OpenClaw.
- Create a paper-trading account in MX.
- Bind a tradable portfolio and set it as current/default.
- Pass API self-check: `balance/positions` should return success, not “please bind account”.

## Trading strategy

### 1) Scheduled tasks (auto execution)
The installer writes 4 trading-day cron jobs:
- 09:24 pre-open scan and order attempt
- 10:30 second intraday scan
- 14:30 late-session execution + risk cleanup
- 15:10 generate daily review

### 2) Trade execution logic
- Pull candidate symbols from the stock-screen endpoint.
- Check position limits and available cash before sending orders.
- Submit buy orders with controlled lot sizing.
- Write each order request and response to logs.

### 3) Risk-control logic
- Hard single-symbol cap: `maxPositionPerStock`.
- Hard total exposure cap: `maxTotalPosition`.
- Daily trade-count limit: `maxTradesPerDay`.
- Auto-cancel stale pending orders (>20 minutes unfilled).
- Automatically skip opening new positions when cash is insufficient or limits are hit.

### 4) Daily review workflow
- At 15:10, automatically read balance, positions, and order history.
- Generate a structured JSON review report.
- Use reports for audit, strategy optimization, and Telegram push.

### 5) Logs and artifacts
- Strategy logs: `~/.openclaw/workspace/mx_autotrade/logs/YYYY-MM-DD.jsonl`
- Aggregate cron log: `~/.openclaw/workspace/mx_autotrade/cron.log`
- Daily review: `~/.openclaw/workspace/mx_autotrade/reviews/review-YYYY-MM-DD.json`

### 6) Parameter tuning
Effective config file:
- `~/.openclaw/workspace/mx_autotrade/config.json`

Common parameters:
- `maxTradesPerDay` (default: 6)
- `maxPositionPerStock` (default: 0.15)
- `maxTotalPosition` (default: 0.60)
- `runTimes` (default: `09:24/10:30/14:30`)