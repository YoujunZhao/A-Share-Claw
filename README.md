# A-Share Claw / A股龙虾

<p>
  <a href="./README.en.md"><img alt="English" src="https://img.shields.io/badge/Language-English-blue"></a>
  <a href="./README.zh-CN.md"><img alt="中文" src="https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E4%B8%AD%E6%96%87-red"></a>
</p>

A practical OpenClaw automation flow for China A-share **paper trading**, including:
- scheduled strategy runs (auction + intraday)
- risk limits (position caps, stale-order cancel)
- daily review output

> This project is for simulation/paper trading education only, not financial advice.

## One-click install (OpenClaw)

```bash
git clone https://github.com/YoujunZhao/A-Share-Claw.git
cd A-Share-Claw
bash installer/install.sh
```

Then set env:

```bash
cat > ~/.openclaw/mx.env <<'EOF'
export MX_APIKEY="your_key"
export MX_API_URL="https://mkapi2.dfcfs.com/finskillshub"
EOF
```

- English docs: [README.en.md](./README.en.md)
- 中文文档: [README.zh-CN.md](./README.zh-CN.md)
