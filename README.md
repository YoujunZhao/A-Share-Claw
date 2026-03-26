# A-Share Claw

<p>
  <a href="./README.md"><img alt="US" src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8-Docs-blue"></a>
  <a href="./README-CN.md"><img alt="CN" src="https://img.shields.io/badge/%F0%9F%87%A8%F0%9F%87%B3-%E6%96%87%E6%A1%A3-red"></a>
</p>

An OpenClaw-based **A-share paper-trading automation workflow** with:
- scheduled runs on trading days (09:24 / 10:30 / 14:30)
- risk controls (single-symbol cap, total exposure cap, stale-order cancellation)
- daily review generation at 15:10

> For paper trading education only. Not financial advice.

## One-sentence auto setup prompt

Send this directly to OpenClaw:

```text
Please one-click install and configure A-Share Claw on this machine: clone https://github.com/YoujunZhao/A-Share-Claw.git, run installer/install.sh, check whether ~/.openclaw/mx.env contains MX_APIKEY (if missing, ask me to provide), then verify cron has the 4 mx_autotrade jobs and report status.
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

## Quick flow
1. Create and bind a tradable paper-trading portfolio in MX
2. Run one-click setup
3. Let scheduled jobs run and generate daily review

## Schedule
- 09:24 pre-open scan + order attempt
- 10:30 intraday second scan
- 14:30 close-to-end run + cleanup
- 15:10 daily review generation

## Risk controls
- `maxPositionPerStock` hard cap
- `maxTotalPosition` hard cap
- `maxTradesPerDay` daily cap
- auto-cancel stale pending orders (>20 mins)

## Logs and outputs
- strategy logs: `~/.openclaw/workspace/mx_autotrade/logs/YYYY-MM-DD.jsonl`
- global log: `~/.openclaw/workspace/mx_autotrade/cron.log`
- review output: `~/.openclaw/workspace/mx_autotrade/reviews/review-YYYY-MM-DD.json`
