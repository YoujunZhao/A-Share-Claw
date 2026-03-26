#!/usr/bin/env python3
import os, re, json, datetime, pathlib, requests

BASE = os.getenv("MX_API_URL", "https://mkapi2.dfcfs.com/finskillshub")
KEY = os.getenv("MX_APIKEY")
ROOT = pathlib.Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
STATE_FILE = ROOT / "state.json"
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

if not KEY:
    raise SystemExit("MX_APIKEY missing")

headers = {"apikey": KEY, "Content-Type": "application/json"}


def post(path, payload):
    r = requests.post(f"{BASE}{path}", headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"date": None, "trades": 0}


def save_state(s):
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def to_yuan(v, unit=1000):
    return (v or 0) / unit


def extract_codes(resp):
    text = json.dumps(resp, ensure_ascii=False)
    return list(dict.fromkeys(re.findall(r"\b[036]\d{5}\b", text)))


def pick_candidates():
    queries = [
        "A股 今日强势 放量 上涨 趋势",
        "A股 近5日强势 短线",
    ]
    out = []
    for q in queries:
        try:
            res = post("/api/claw/stock-screen", {"keyword": q})
            out.extend(extract_codes(res))
        except Exception:
            pass
    return list(dict.fromkeys(out))[:20]


def append_log(logf, payload):
    with logf.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def cleanup_pending_orders(now, logf):
    """撤掉长时间未成交挂单，避免占用资金。"""
    try:
        od = post("/api/claw/mockTrading/orders", {"fltOrderDrt": 0, "fltOrderStatus": 0})
    except Exception as e:
        append_log(logf, {"ts": now.isoformat(), "event": "orders_fetch_error", "err": str(e)})
        return

    orders = (od.get("data") or {}).get("orders") or []
    for o in orders:
        st = o.get("status")
        if st not in (2, 6):  # 已报 / 已报待撤
            continue
        ts = o.get("time")
        if not isinstance(ts, (int, float)):
            continue
        age_min = (now.timestamp() - ts) / 60.0
        if age_min < 20:
            continue
        oid = o.get("id")
        code = o.get("secCode")
        if not oid or not code:
            continue
        try:
            rsp = post("/api/claw/mockTrading/cancel", {"type": "order", "orderId": oid, "stockCode": code})
            append_log(logf, {
                "ts": now.isoformat(), "event": "cancel_stale_order", "orderId": oid,
                "stockCode": code, "ageMin": round(age_min, 1), "resp": rsp
            })
        except Exception as e:
            append_log(logf, {
                "ts": now.isoformat(), "event": "cancel_stale_order_error", "orderId": oid,
                "stockCode": code, "ageMin": round(age_min, 1), "err": str(e)
            })


def main():
    now = datetime.datetime.now()
    day = now.strftime("%Y-%m-%d")
    hhmm = now.strftime("%H:%M")
    logf = LOG_DIR / f"{day}.jsonl"

    state = load_state()
    if state.get("date") != day:
        state = {"date": day, "trades": 0}

    if hhmm not in set(CFG["runTimes"]):
        return

    # 先清理超时挂单
    cleanup_pending_orders(now, logf)

    bal = post("/api/claw/mockTrading/balance", {})
    if (bal.get("status") or bal.get("code")) not in (0, "0", 200, "200"):
        append_log(logf, {"ts": now.isoformat(), "event": "balance_error", "resp": bal})
        return

    d = bal.get("data") or {}
    unit = d.get("currencyUnit", 1000)
    total_assets = to_yuan(d.get("totalAssets"), unit)
    avail = to_yuan(d.get("availBalance"), unit)
    total_pos_value = to_yuan(d.get("totalPosValue"), unit)
    pos_pct = (total_pos_value / total_assets) if total_assets > 0 else 0

    if state["trades"] >= CFG["maxTradesPerDay"]:
        append_log(logf, {"ts": now.isoformat(), "event": "skip_max_trades", "trades": state["trades"]})
        save_state(state)
        return

    if pos_pct >= CFG["maxTotalPosition"]:
        append_log(logf, {
            "ts": now.isoformat(), "event": "skip_total_pos_limit",
            "posPct": round(pos_pct, 4), "limit": CFG["maxTotalPosition"]
        })
        save_state(state)
        return

    if avail < 20000:
        append_log(logf, {"ts": now.isoformat(), "event": "skip_low_cash", "avail": avail})
        save_state(state)
        return

    pos = post("/api/claw/mockTrading/positions", {})
    plist = (pos.get("data") or {}).get("posList") or []
    held_value = {}
    for p in plist:
        code = p.get("secCode")
        if code:
            held_value[code] = to_yuan(p.get("value"), (pos.get("data") or {}).get("currencyUnit", 1000))

    candidates = pick_candidates()
    if not candidates:
        append_log(logf, {"ts": now.isoformat(), "event": "no_candidates"})
        save_state(state)
        return

    # 选择未超单票上限的标的
    selected = None
    single_cap = total_assets * CFG["maxPositionPerStock"]
    for c in candidates:
        if held_value.get(c, 0) < single_cap * 0.9:  # 留 10% 缓冲
            selected = c
            break

    if not selected:
        append_log(logf, {"ts": now.isoformat(), "event": "skip_no_symbol_under_cap", "caps": {"singleCap": single_cap}})
        save_state(state)
        return

    # 保守下单：按较高假设股价100元计算数量，防止仓位爆掉
    budget_by_single = max(0, single_cap - held_value.get(selected, 0))
    budget_by_total = max(0, total_assets * CFG["maxTotalPosition"] - total_pos_value)
    per_stock_budget = min(budget_by_single, budget_by_total, avail, total_assets * 0.08)  # 单次最多8%

    if per_stock_budget < 10000:
        append_log(logf, {"ts": now.isoformat(), "event": "skip_small_budget", "budget": per_stock_budget})
        save_state(state)
        return

    qty = int((per_stock_budget / 100) // 100 * 100)  # assume 100元/股
    qty = max(100, min(qty, 2000))

    trade = post("/api/claw/mockTrading/trade", {
        "type": "buy",
        "stockCode": selected,
        "quantity": qty,
        "useMarketPrice": True,
    })

    ok = str(trade.get("status") or trade.get("code")) in ("0", "200")
    append_log(logf, {
        "ts": now.isoformat(), "event": "trade_attempt", "code": selected, "qty": qty,
        "budget": round(per_stock_budget, 2), "resp": trade,
    })
    if ok:
        state["trades"] += 1
    save_state(state)


if __name__ == "__main__":
    main()
