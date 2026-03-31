#!/usr/bin/env python3
import json
import datetime
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent
REVIEWS = ROOT / "reviews"


def pct(v):
    if v is None:
        return "N/A"
    try:
        return f"{v*100:.2f}%"
    except Exception:
        return "N/A"


def main():
    day = datetime.date.today().isoformat()
    p = REVIEWS / f"review-{day}.json"
    if not p.exists():
        raise SystemExit(f"review file not found: {p}")

    d = json.loads(p.read_text(encoding="utf-8"))
    t = d.get("todayResult") or {}
    trades = d.get("perTradeLogic") or []
    disc = d.get("disciplineCheck") or {}
    auto = d.get("autoTune") or {}

    msg_lines = [
        f"📘 自动交易日报 {day}",
        f"余额：¥{(t.get('balanceYuan') or 0):,.2f}",
        f"今日交易：{len(trades)} 笔",
        f"单票仓位：{(disc.get('singlePositionLimit') or {}).get('status', 'N/A')} | 总仓位：{(disc.get('totalPositionLimit') or {}).get('status', 'N/A')}",
        f"14:30 风控：{(disc.get('riskFirstAt1430') or {}).get('status', 'N/A')}",
    ]

    if auto.get("applied"):
        changes = auto.get("changes") or {}
        c = []
        for k, v in changes.items():
            c.append(f"{k}: {v.get('from')}→{v.get('to')}")
        if c:
            msg_lines.append("自动调参：" + "；".join(c))

    msg = "\n".join(msg_lines)

    cmd = [
        "openclaw", "message", "send",
        "--channel", "telegram",
        "--account", "newbot",
        "--target", "7016708132",
        "--message", msg,
    ]

    last_err = None
    for i in range(3):
        try:
            subprocess.run(cmd, check=True)
            return
        except subprocess.CalledProcessError as e:
            last_err = e
            time.sleep(2 * (i + 1))
    raise last_err


if __name__ == "__main__":
    main()
