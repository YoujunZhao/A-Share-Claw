<div align="center">

<img src="./assets/logo.jpg" alt="A-Share Claw Logo" width="350" />

# A-Share Claw

| Day | Balance | Daily Return | Day | Balance | Daily Return |
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
| Day24 | 199,318.87 | -0.44% |

[![English](https://img.shields.io/badge/Language-English-blue)](./README.md)
[![中文](https://img.shields.io/badge/语言-中文-red)](./README-CN.md)

</div>

An OpenClaw-based **A-share paper-trading automation workflow** with:
- scheduled runs on trading days (`09:24 / 10:30 / 11:30 / 13:30 / 14:30`)
- buy-side scanning plus sell-side rebalance / risk reduction
- daily review generation at `15:10`

> For paper trading education only. Not financial advice.

## One-sentence auto setup prompt (OpenClaw)

Send this directly to OpenClaw:

```text
Please one-click install and configure A-Share Claw (A股龙虾) on my machine: first run `git clone https://github.com/YoujunZhao/A-Share-Claw.git`, then run `installer/install.sh`, check whether `~/.openclaw/mx.env` contains `MX_APIKEY` (if missing, remind me to provide it), and finally verify that crontab contains the 6 `mx_autotrade` scheduled jobs (5 trading slots + 1 daily review) and report the results.
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
The current strategy runs on 5 trading-day slots:
- 09:24 pre-open scan and order attempt
- 10:30 intraday scan
- 11:30 intraday scan
- 13:30 intraday scan
- 14:30 late-session risk-first execution + optional rebalance buy
- 15:10 generate daily review

### 2) Candidate selection pipeline
The strategy uses a four-layer pipeline before placing orders:
- **Layer 1 – News / theme discovery:** build market-hotspot keywords and search for short-term A-share candidates.
- **Layer 2 – Financial filter:** apply lightweight checks such as PE / ROE / profit-growth when data is available.
- **Layer 3 – Watchlist sync:** sync shortlisted symbols to the self-select/watchlist layer.
- **Layer 4 – Trade execution:** place mock-trading orders only after cash, exposure, and lot-size checks pass.

By default, the financial and watchlist layers are fail-open unless strict mode is enabled.

### 3) Buy logic
- Pull a candidate list from the four-layer pipeline.
- Skip new buys when daily trade count, cash, single-symbol cap, or total exposure limits are hit.
- Prefer symbols still below the single-symbol cap.
- Submit buy orders with controlled lot sizing and market-price execution.
- Write each order request and response to logs.

### 4) Sell / rebalance logic
The strategy is no longer buy-only. It now includes sell-side decisions:
- **Immediate risk sell-down:** if a position breaches `maxPositionPerStock`, reduce it immediately.
- **Stale-position exit:** if a holding has aged across multiple run slots and remains weak, exit it.
- **14:30 weak-position cleanup:** at the tail-risk window, sell positions that are no longer in the candidate pool and remain weak.
- **14:30 stronger-candidate rebalance:** compare the strongest new candidate with the weakest existing holding; when the score gap is large enough, sell the weaker holding first and let the downstream buy flow rotate into the stronger symbol.

### 5) Risk-control logic
- Hard single-symbol cap: `maxPositionPerStock`.
- Hard total exposure cap: `maxTotalPosition`.
- Daily trade-count limit: `maxTradesPerDay`.
- Auto-cancel stale pending orders (>20 minutes unfilled).
- Auto-skip new buys when cash is insufficient or exposure limits are hit.
- 14:30 is handled as a **risk-first** window; optional buy continuation is controlled by `allowBuyAt1430`.

### 6) Daily review workflow
- At 15:10, automatically read balance, positions, and order history.
- Generate a structured JSON review report.
- Use reports for audit, strategy optimization, and Telegram push.

### 7) Logs and artifacts
- Strategy logs: `~/.openclaw/workspace/mx_autotrade/logs/YYYY-MM-DD.jsonl`
- Aggregate cron log: `~/.openclaw/workspace/mx_autotrade/cron.log`
- Daily review: `~/.openclaw/workspace/mx_autotrade/reviews/review-YYYY-MM-DD.json`
- Runtime state: `~/.openclaw/workspace/mx_autotrade/state.json`

### 8) Parameter tuning
Effective config file:
- `~/.openclaw/workspace/mx_autotrade/config.json`

Current defaults in this repo:
- `maxTradesPerDay`: `6`
- `maxPositionPerStock`: `0.08`
- `maxTotalPosition`: `0.60`
- `runTimes`: `09:24 / 10:30 / 11:30 / 13:30 / 14:30`
- `allowBuyAt1430`: `true`
- `autoTuneApply`: `true`true`
