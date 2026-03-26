<div align="center">

# A股龙虾

[![English](https://img.shields.io/badge/Language-English-blue)](./README.md)
[![中文](https://img.shields.io/badge/语言-中文-red)](./README-CN.md)

</div>

这是一个基于 OpenClaw 的 **A股模拟盘自动交易流程**，包含：
- 交易日自动执行（09:24 / 10:30 / 14:30）
- 风控（单票仓位上限、总仓位上限、超时挂单撤单）
- 每日复盘（15:10 自动输出）

> 仅用于模拟盘学习，不构成投资建议。

## 一句话自动安装提示词

把下面这句话直接发给 OpenClaw：

```text
请在我的机器上一键安装并配置 A-Share Claw（A股龙虾）：克隆 https://github.com/<你的用户名>/A-Share-Claw.git，执行 installer/install.sh，检查 ~/.openclaw/mx.env 是否有 MX_APIKEY（没有就提醒我补），安装后验证 crontab 里有 mx_autotrade 的 4 条定时任务，并回报结果。
```

## 手动安装

```bash
git clone https://github.com/<你的用户名>/A-Share-Claw.git
cd A-Share-Claw
bash installer/install.sh
```

```bash
cat > ~/.openclaw/mx.env <<'EOF'
export MX_APIKEY="你的key"
export MX_API_URL="https://mkapi2.dfcfs.com/finskillshub"
EOF
```

## 简易流程
1. 在妙想创建并绑定可交易模拟组合
2. 执行一键安装
3. 等待交易日自动运行并生成复盘

## 执行时点
- 09:24 竞价前扫描并尝试下单
- 10:30 盘中第二轮扫描
- 14:30 尾盘执行 + 风控清理
- 15:10 生成每日复盘

## 风控规则
- `maxPositionPerStock` 单票上限
- `maxTotalPosition` 总仓位上限
- `maxTradesPerDay` 每日交易上限
- 超过 20 分钟未成交挂单自动撤单

## 日志与产物
- 策略日志：`~/.openclaw/workspace/mx_autotrade/logs/YYYY-MM-DD.jsonl`
- 总日志：`~/.openclaw/workspace/mx_autotrade/cron.log`
- 每日复盘：`~/.openclaw/workspace/mx_autotrade/reviews/review-YYYY-MM-DD.json`
