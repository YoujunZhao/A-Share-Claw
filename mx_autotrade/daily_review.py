#!/usr/bin/env python3
import os, json, datetime, pathlib, requests
from collections import defaultdict

BASE = os.getenv("MX_API_URL", "https://mkapi2.dfcfs.com/finskillshub")
KEY = os.getenv("MX_APIKEY")
ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "reviews"
LOG_DIR = ROOT / "logs"
CFG_PATH = ROOT / "config.json"
OUT.mkdir(parents=True, exist_ok=True)

headers = {"apikey": KEY, "Content-Type": "application/json"}

def post(path, payload):
    r = requests.post(f"{BASE}{path}", headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def load_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows

def yn(v):
    return "达标" if v else "未达标"


def load_recent_reviews(out_dir, today, lookback=5):
    files = sorted(out_dir.glob("review-*.json"))
    rows = []
    for p in files:
        if p.name == f"review-{today}.json":
            continue
        try:
            rows.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return rows[-lookback:]


def build_reflection(cfg, today_report, recent_reports):
    symbol_stats = defaultdict(lambda: {"trades": 0, "success": 0})
    failed_days = 0
    no_trade_days = 0
    risk_not_met_days = 0

    all_reports = recent_reports + [today_report]
    for r in all_reports:
        trades = r.get("perTradeLogic") or []
        if not trades:
            no_trade_days += 1
        for t in trades:
            s = str(t.get("symbol") or "")
            if not s:
                continue
            symbol_stats[s]["trades"] += 1
            if t.get("result") == "success":
                symbol_stats[s]["success"] += 1

        if (r.get("errorList") or []):
            failed_days += 1

        d = r.get("disciplineCheck") or {}
        if (d.get("singlePositionLimit") or {}).get("status") != "达标" or (d.get("totalPositionLimit") or {}).get("status") != "达标":
            risk_not_met_days += 1

    findings = []
    findings.append(f"近{len(all_reports)}日统计：异常日{failed_days}天、无交易日{no_trade_days}天、仓位纪律未达标{risk_not_met_days}天")

    top_symbols = sorted(symbol_stats.items(), key=lambda kv: kv[1]["trades"], reverse=True)[:5]
    symbol_summary = []
    for sym, st in top_symbols:
        succ_rate = (st["success"] / st["trades"]) if st["trades"] else 0.0
        symbol_summary.append({
            "symbol": sym,
            "trades": st["trades"],
            "success": st["success"],
            "successRate": round(succ_rate, 4),
        })

    suggestions = {
        "maxTradesPerDay": cfg.get("maxTradesPerDay", 6),
        "maxPositionPerStock": cfg.get("maxPositionPerStock", 0.15),
        "maxTotalPosition": cfg.get("maxTotalPosition", 0.60),
    }
    reasons = []

    if failed_days >= 2:
        suggestions["maxTradesPerDay"] = max(2, int(suggestions["maxTradesPerDay"]) - 1)
        reasons.append("近几日错误较多，建议下调每日交易次数以降低执行风险")

    if risk_not_met_days >= 1:
        suggestions["maxPositionPerStock"] = round(max(0.08, float(suggestions["maxPositionPerStock"]) * 0.9), 4)
        reasons.append("出现仓位纪律未达标，建议收紧单票仓位")

    if no_trade_days >= max(2, len(all_reports) // 2):
        reasons.append("无交易日占比较高，建议优化候选股信号质量而非盲目放宽风控")

    if not reasons:
        reasons.append("当前执行稳定，维持参数不变")

    return {
        "windowDays": len(all_reports),
        "findings": findings,
        "symbolStatsTop": symbol_summary,
        "parameterSuggestions": suggestions,
        "suggestionReasons": reasons,
    }


def maybe_apply_tuning(cfg_path, cfg, reflection):
    if not cfg.get("autoTuneApply", False):
        return {"applied": False, "reason": "autoTuneApply=false"}

    sug = reflection.get("parameterSuggestions") or {}
    changed = {}
    for k in ("maxTradesPerDay", "maxPositionPerStock", "maxTotalPosition"):
        if k in sug and cfg.get(k) != sug[k]:
            changed[k] = {"from": cfg.get(k), "to": sug[k]}
            cfg[k] = sug[k]

    if changed:
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"applied": True, "changes": changed}
    return {"applied": False, "reason": "no_change"}


def main():
    day = datetime.date.today().isoformat()
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8")) if CFG_PATH.exists() else {}

    bal = post('/api/claw/mockTrading/balance', {})
    pos = post('/api/claw/mockTrading/positions', {})
    ords = post('/api/claw/mockTrading/orders', {"fltOrderDrt": 0, "fltOrderStatus": 0})

    b = bal.get("data") or {}
    p = pos.get("data") or {}
    unit = b.get("currencyUnit", 1000)
    total_assets = (b.get("totalAssets") or 0) / unit
    total_pos_value = (b.get("totalPosValue") or 0) / unit
    init_assets = (b.get("initAssets") or 0) / unit

    today_pl_rate = ((b.get("todayPLRate") or 0) / 100.0) if b.get("todayPLRate") is not None else None
    total_return_rate = ((total_assets - init_assets) / init_assets) if init_assets > 0 else None
    drawdown = ((b.get("drawdownRate") or 0) / 100.0) if b.get("drawdownRate") is not None else None

    log_rows = load_jsonl(LOG_DIR / f"{day}.jsonl")
    trade_rows = [r for r in log_rows if r.get("event") == "trade_attempt"]
    error_rows = [r for r in log_rows if "error" in str(r.get("event", "")) or r.get("err")]

    per_trade_logic = []
    for i, t in enumerate(trade_rows, 1):
        code = t.get("code")
        qty = t.get("qty")
        budget = t.get("budget")
        resp = t.get("resp") or {}
        ok = str(resp.get("status") or resp.get("code")) in ("0", "200")
        per_trade_logic.append({
            "seq": i,
            "time": t.get("ts"),
            "symbol": code,
            "quantity": qty,
            "budgetYuan": budget,
            "logic": "候选股筛选(强势/放量) + 仓位约束 + 资金约束",
            "result": "success" if ok else "failed",
            "raw": resp,
        })

    max_single = cfg.get("maxPositionPerStock", 0.15)
    max_total = cfg.get("maxTotalPosition", 0.60)
    pos_list = p.get("posList") or []
    single_ok = True
    max_single_real = 0.0
    if total_assets > 0:
        for item in pos_list:
            val = (item.get("value") or 0) / (p.get("currencyUnit") or 1000)
            ratio = val / total_assets
            max_single_real = max(max_single_real, ratio)
            if ratio > max_single + 1e-9:
                single_ok = False

    total_ratio = (total_pos_value / total_assets) if total_assets > 0 else 0.0
    total_ok = total_ratio <= max_total + 1e-9

    discipline = {
        "singlePositionLimit": {
            "limit": max_single,
            "actualMax": round(max_single_real, 6),
            "status": yn(single_ok),
        },
        "totalPositionLimit": {
            "limit": max_total,
            "actual": round(total_ratio, 6),
            "status": yn(total_ok),
        },
        "timeoutCancel20m": {
            "status": "达标" if any(r.get("event") in ("cancel_stale_order", "orders_fetch_error") for r in log_rows) else "未达标"
        },
        "riskFirstAt1430": {
            "status": "达标" if any(r.get("event") == "risk_priority_window" for r in log_rows) else "未达标"
        }
    }

    next_day_actions = []
    if not single_ok:
        next_day_actions.append("降低单笔预算并优先减仓超限个股")
    if not total_ok:
        next_day_actions.append("盘中总仓位触顶后仅执行风控，不再开新仓")
    if error_rows:
        next_day_actions.append("优先修复错误清单中的接口/参数问题")
    if not next_day_actions:
        next_day_actions.append("维持当前风控参数，复核候选股质量并减少无效下单")

    report = {
        "date": day,
        "todayResult": {
            "balanceYuan": round(total_assets, 2),
            "todayReturnRate": today_pl_rate,
            "totalReturnRate": total_return_rate,
            "drawdownRate": drawdown,
        },
        "perTradeLogic": per_trade_logic,
        "errorList": error_rows,
        "nextDayFixActions": next_day_actions,
        "disciplineCheck": discipline,
        "raw": {
            "balance": b,
            "positions": p,
            "orders": (ords.get("data") or {}).get("orders", []),
        }
    }

    recent = load_recent_reviews(OUT, day, lookback=5)
    reflection = build_reflection(cfg, report, recent)
    tune_result = maybe_apply_tuning(CFG_PATH, cfg, reflection)
    report["reflection"] = reflection
    report["autoTune"] = tune_result

    pth = OUT / f"review-{day}.json"
    pth.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(str(pth))

if __name__ == '__main__':
    if not KEY:
        raise SystemExit('MX_APIKEY missing')
    main()
