<div align="center">

<img src="./assets/logo.jpg" alt="A-Share Claw Logo" width="350" />

# A-Share Claw

| Day | Balance | Daily Return |
|---|---:|---:|
| Day1 | 200,000.00 | 0.00% |
| Day2 | 198,867.21 | -0.57% |

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
Please one-click install and configure A-Share Claw on this machine: run `git clone https://github.com/YoujunZhao/A-Share-Claw.git`, then run `installer/install.sh`, check whether `~/.openclaw/mx.env` contains `MX_APIKEY` (if missing, ask me to provide), then verify cron has the 4 `mx_autotrade` jobs and report status.
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

### 1) Account readiness
- Create a paper-trading account in MX.
- Bind a tradable portfolio and set it as current/default.
- Verify API readiness: balance/positions endpoints should return success (not “please bind account”).

### 2) Environment setup
- Clone repository and run installer:
  - `git clone https://github.com/YoujunZhao/A-Share-Claw.git`
  - `cd A-Share-Claw && bash installer/install.sh`
- Configure `~/.openclaw/mx.env`:
  - `MX_APIKEY`
  - `MX_API_URL` (default `https://mkapi2.dfcfs.com/finskillshub`)

### 3) Scheduler setup (auto-run)
The installer writes 4 cron jobs (trading days):
- 09:24 pre-open scan + order attempt
- 10:30 intraday second scan
- 14:30 close-to-end run + risk cleanup
- 15:10 daily review generation

### 4) Trading execution logic
- Pull symbol candidates from stock-screen API.
- Check risk limits and available cash before placing orders.
- Submit buy orders in controlled lot sizes.
- Record every order attempt and response to log files.

### 5) Risk-control logic
- Single-symbol hard cap: `maxPositionPerStock`.
- Total exposure hard cap: `maxTotalPosition`.
- Daily trade-count cap: `maxTradesPerDay`.
- Auto-cancel stale pending orders after timeout (>20 mins).
- Skip new entries when cash is too low or risk caps are hit.

### 6) Daily review pipeline
- At 15:10, fetch account balance, positions, and order history.
- Generate a structured JSON review report.
- Save reports for audit, optimization, and optional Telegram push.

### 7) Logs and artifacts
- Strategy logs: `~/.openclaw/workspace/mx_autotrade/logs/YYYY-MM-DD.jsonl`
- Cron aggregate log: `~/.openclaw/workspace/mx_autotrade/cron.log`
- Review output: `~/.openclaw/workspace/mx_autotrade/reviews/review-YYYY-MM-DD.json`

### 8) Tuning parameters
Active config file:
- `~/.openclaw/workspace/mx_autotrade/config.json`

Common parameters:
- `maxTradesPerDay` (default 6)
- `maxPositionPerStock` (default 0.15)
- `maxTotalPosition` (default 0.60)
- `runTimes` (default `09:24/10:30/14:30`)
