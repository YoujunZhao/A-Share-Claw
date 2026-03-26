# A-Share Claw

<p>
  <a href="./README.en.md"><img alt="English" src="https://img.shields.io/badge/Language-English-blue"></a>
  <a href="./README.zh-CN.md"><img alt="中文" src="https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E4%B8%AD%E6%96%87-red"></a>
</p>

An OpenClaw-based **A-share paper trading automation flow** with:
- auction + intraday scheduled execution
- risk controls (single-position cap, total exposure cap, stale-order cancellation)
- daily review generation

> For simulation/paper trading only. Not financial advice.

## One-click install (OpenClaw)

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

## Quick start (3 steps)

1. Create and bind a tradable paper-trading portfolio in MX.
2. Run installer and configure `MX_APIKEY`.
3. Let it run on trading days (09:24 / 10:30 / 14:30), with review at 15:10.

## Detailed flow

### 1) Trade execution
- 09:24: pre-open scan and order attempt
- 10:30: intraday second scan
- 14:30: close-to-end execution + risk cleanup

### 2) Risk controls
- Single symbol cap: `maxPositionPerStock`
- Total exposure cap: `maxTotalPosition`
- Daily max trade count: `maxTradesPerDay`
- Auto cancel stale pending orders (>20 mins)

### 3) Review pipeline
- 15:10 fetches balance/positions/orders
- writes JSON review into `mx_autotrade/reviews/`
- can be forwarded to Telegram by your own notification job

## Config

- template: `mx_autotrade/config.example.json`
- active: `~/.openclaw/workspace/mx_autotrade/config.json`
