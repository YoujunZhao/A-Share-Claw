# A股龙虾（A-Share Claw）

<p>
  <a href="./README.en.md"><img alt="English" src="https://img.shields.io/badge/Language-English-blue"></a>
  <a href="./README.zh-CN.md"><img alt="中文" src="https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E4%B8%AD%E6%96%87-red"></a>
</p>

这是一个基于 OpenClaw 的 **A股模拟交易自动化流程**，包含：
- 竞价/盘中定时执行
- 风控限制（单票/总仓位、超时挂单撤单）
- 每日复盘输出

> 仅用于模拟盘学习与流程演示，不构成投资建议。

## 一键安装（OpenClaw）

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

## 简易流程（3步）

1. 在妙想页面创建并绑定模拟账户（可交易组合）
2. 执行安装脚本并设置 `MX_APIKEY`
3. 等待交易日自动执行（09:24 / 10:30 / 14:30），15:10 生成复盘

## 详细流程

### 1) 交易执行逻辑
- 09:24：竞价前策略扫描并尝试下单
- 10:30：盘中第二轮扫描
- 14:30：尾盘执行（含风控清理）

### 2) 风控逻辑
- 单票仓位上限：`maxPositionPerStock`
- 总仓位上限：`maxTotalPosition`
- 每日最大交易笔数：`maxTradesPerDay`
- 挂单超时自动撤单（>20分钟）

### 3) 复盘逻辑
- 15:10 自动读取资金/持仓/委托
- 产出复盘 JSON 到 `mx_autotrade/reviews/`
- 用于后续 Telegram 推送或人工复盘

## 配置文件

- 示例配置：`mx_autotrade/config.example.json`
- 实际生效配置：`~/.openclaw/workspace/mx_autotrade/config.json`

## 项目结构

```text
installer/install.sh          # 一键安装+写入定时任务
mx_autotrade/run_autotrade.py # 自动交易执行
mx_autotrade/daily_review.py  # 每日复盘生成
mx_autotrade/config.example.json
```
