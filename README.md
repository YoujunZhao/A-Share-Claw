<div align="center">

<img src="./assets/logo.jpg" alt="A-Share Claw Logo" width="350" />

# A-Share Claw

| Day | Balance | Daily Return |
|---|---:|---:|
| Day1 | 200,000.00 | 0.00% |
| Day2 | 198,867.21 | -0.57% |
| Day3 | 198,711.30 | -0.08% |

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

### 1) Account preparation
- Create a paper-trading account in MX.
- Bind a tradable portfolio and set it as current/default.
- Pass API self-check: `balance/positions` should return success, not “please bind account”.

### 2) Environment installation
- Clone and run installer:
  - `git clone https://github.com/YoujunZhao/A-Share-Claw.git`
  - `cd A-Share-Claw && bash installer/install.sh`
- Configure `~/.openclaw/mx.env`:
  - `MX_APIKEY`
  - `MX_API_URL` (default: `https://mkapi2.dfcfs.com/finskillshub`)

### 3) Scheduled tasks (auto execution)
The installer writes 4 trading-day cron jobs:
- 09:24 pre-open scan and order attempt
- 10:30 second intraday scan
- 14:30 late-session execution + risk cleanup
- 15:10 generate daily review

### 4) Trading strategy
- Pull candidate symbols from the stock-screen endpoint.
- Check position limits and available cash before sending orders.
- Submit buy orders with controlled lot sizing.
- Write each order request and response to logs.

### 5) Risk-control strategy
- Hard single-symbol cap: `maxPositionPerStock`.
- Hard total exposure cap: `maxTotalPosition`.
- Daily trade-count limit: `maxTradesPerDay`.
- Auto-cancel stale pending orders (>20 minutes unfilled).
- Automatically skip opening new positions when cash is insufficient or limits are hit.

### 6) Daily review process
- At 15:10, automatically read balance, positions, and order history.
- Generate a structured JSON review report.
- Use reports for audit, strategy optimization, and Telegram push.

### 7) Logs and outputs
- Strategy logs: `~/.openclaw/workspace/mx_autotrade/logs/YYYY-MM-DD.jsonl`
- Aggregate cron log: `~/.openclaw/workspace/mx_autotrade/cron.log`
- Daily review: `~/.openclaw/workspace/mx_autotrade/reviews/review-YYYY-MM-DD.json`

### 8) Parameter tuning
Effective config file:
- `~/.openclaw/workspace/mx_autotrade/config.json`

Common parameters:
- `maxTradesPerDay` (default: 6)
- `maxPositionPerStock` (default: 0.15)
- `maxTotalPosition` (default: 0.60)
- `runTimes` (default: `09:24/10:30/14:30`)
