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


def safe_post(path, payload):
    try:
        return post(path, payload), None
    except Exception as e:
        return None, str(e)


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


def append_log(logf, payload):
    with logf.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def try_optional(paths_and_payloads):
    """Try optional endpoints; return first successful response."""
    for path, payload in paths_and_payloads:
        rsp, err = safe_post(path, payload)
        if rsp is not None:
            return path, rsp, None
    return None, None, "all_failed"


def layer1_news_keywords(logf, now):
    """Layer1: 妙想资讯搜索 skill（优先）+ 回退检索接口。"""
    base_keywords = ["A股 今日强势 放量 趋势", "A股 短线 资金流入", "A股 低位放量 反转"]
    path, rsp, err = try_optional([
        ("/api/claw/mx-search/news", {"keyword": "A股 今日热点 资金 风口"}),
        ("/api/claw/mx-search/query", {"keyword": "A股 今日热点 资金 风口"}),
        ("/api/claw/news-search", {"keyword": "A股 今日热点 资金 风口"}),
        ("/api/claw/stock-news", {"keyword": "A股 今日热点 资金 风口"}),
        ("/api/claw/search", {"keyword": "A股 今日热点 资金 风口"}),
    ])

    if rsp is None:
        append_log(logf, {"ts": now.isoformat(), "event": "layer1_news_skip", "reason": err})
        return base_keywords

    txt = json.dumps(rsp, ensure_ascii=False)
    extras = []
    for k in ["涨停", "放量", "业绩", "资金流入", "突破", "回踩", "高景气", "电力", "算力", "光伏"]:
        if k in txt:
            extras.append(k)
    extras = list(dict.fromkeys(extras))[:3]
    kws = base_keywords + [f"A股 {x} 短线" for x in extras]
    append_log(logf, {"ts": now.isoformat(), "event": "layer1_news_ok", "path": path, "extraKeywords": extras})
    return kws


def layer2_financial_ok(code, logf, now):
    """Layer2: 妙想金融数据 skill（优先）；默认 fail-open，可切 strict。"""
    endpoint_candidates = [
        ("/api/claw/mx-data/financial", {"stockCode": code}),
        ("/api/claw/mx-data/quote", {"stockCode": code}),
        ("/api/claw/financial-data", {"stockCode": code}),
        ("/api/claw/stock-financial", {"stockCode": code}),
        ("/api/claw/quote", {"stockCode": code}),
    ]
    path, rsp, _ = try_optional(endpoint_candidates)
    if rsp is None:
        if CFG.get("strictFinancialSkill", False):
            return False, {"mode": "strict", "reason": "financial_endpoint_unavailable"}
        return True, {"mode": "fail_open", "reason": "financial_endpoint_unavailable"}

    text = json.dumps(rsp, ensure_ascii=False)
    # Very light guardrails from any parsable fields in payload
    pe = re.search(r'"(?:pe|peTtm|peRatio)"\s*:\s*(-?\d+\.?\d*)', text)
    roe = re.search(r'"(?:roe|roeWeighted)"\s*:\s*(-?\d+\.?\d*)', text)
    growth = re.search(r'"(?:netProfitGrowth|profitYoY|yoy)"\s*:\s*(-?\d+\.?\d*)', text)

    pe_v = float(pe.group(1)) if pe else None
    roe_v = float(roe.group(1)) if roe else None
    growth_v = float(growth.group(1)) if growth else None

    if pe_v is not None and pe_v > 120:
        return False, {"path": path, "reason": "pe_too_high", "pe": pe_v}
    if roe_v is not None and roe_v < 0:
        return False, {"path": path, "reason": "roe_negative", "roe": roe_v}
    if growth_v is not None and growth_v < -20:
        return False, {"path": path, "reason": "profit_growth_too_low", "growth": growth_v}
    return True, {"path": path, "reason": "pass", "pe": pe_v, "roe": roe_v, "growth": growth_v}


def layer3_sync_watchlist(codes, logf, now):
    """Layer3: 妙想自选股管理 skill（优先）；默认弱依赖，可切 strict。"""
    payload = {"codes": codes[:20]}
    path, rsp, err = try_optional([
        ("/api/claw/mx-selfselect/sync", payload),
        ("/api/claw/mx-selfselect/update", payload),
        ("/api/claw/selfselect/sync", payload),
        ("/api/claw/selfselect/update", payload),
        ("/api/claw/selfselect/add", payload),
    ])
    if rsp is None:
        append_log(logf, {"ts": now.isoformat(), "event": "layer3_watchlist_skip", "reason": err})
        return not CFG.get("strictWatchlistSkill", False)
    append_log(logf, {"ts": now.isoformat(), "event": "layer3_watchlist_ok", "path": path, "count": len(codes[:20])})
    return True


def pick_candidates_with_layers(logf, now):
    """Layer1+Layer2+Layer3 around stock screening.

    Layer4 execution remains in main() via mockTrading endpoints.
    """
    # Layer1: info search -> dynamic keywords
    queries = layer1_news_keywords(logf, now)

    raw = []
    for q in queries:
        rsp, err = safe_post("/api/claw/stock-screen", {"keyword": q})
        if rsp is None:
            append_log(logf, {"ts": now.isoformat(), "event": "stock_screen_error", "q": q, "err": err})
            continue
        raw.extend(extract_codes(rsp))

    candidates = list(dict.fromkeys(raw))[:30]
    if not candidates:
        return []

    # Layer2: optional financial filter
    passed = []
    for c in candidates:
        ok, detail = layer2_financial_ok(c, logf, now)
        append_log(logf, {"ts": now.isoformat(), "event": "layer2_financial_check", "code": c, "ok": ok, "detail": detail})
        if ok:
            passed.append(c)
        if len(passed) >= 20:
            break

    # Layer3: optional selfselect sync
    layer3_ok = layer3_sync_watchlist(passed, logf, now)
    if not layer3_ok:
        append_log(logf, {"ts": now.isoformat(), "event": "layer3_blocked", "reason": "strict_watchlist_enabled"})
        return []

    append_log(logf, {"ts": now.isoformat(), "event": "four_layer_pipeline", "layer1": True, "layer2": True, "layer3": bool(layer3_ok), "layer4": True, "candidateCount": len(passed)})
    return passed


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

    risk_window = (hhmm == "14:30")
    allow_buy_1430 = bool(CFG.get("allowBuyAt1430", False))

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

    pos = post("/api/claw/mockTrading/positions", {})
    plist = (pos.get("data") or {}).get("posList") or []
    pos_unit = (pos.get("data") or {}).get("currencyUnit", 1000)
    held_value = {}
    for p in plist:
        code = p.get("secCode")
        if code:
            held_value[code] = to_yuan(p.get("value"), pos_unit)

    single_cap = total_assets * CFG["maxPositionPerStock"]
    over_single = []
    for p in plist:
        code = p.get("secCode")
        value = to_yuan(p.get("value"), pos_unit)
        ratio = (value / total_assets) if total_assets > 0 else 0
        if code and ratio > CFG["maxPositionPerStock"] + 1e-9:
            over_single.append((p, value, ratio))

    # 14:30 先做风控；可配置是否允许继续开新仓
    if risk_window:
        sold_any = False
        for p, value, ratio in over_single:
            code = p.get("secCode")
            count = int(p.get("availCount") or p.get("count") or 0)
            if count < 100:
                continue
            px = (value / count) if count > 0 else 0
            if px <= 0:
                continue
            target_count = int((single_cap / px) // 100 * 100)
            sell_qty = max(0, count - target_count)
            sell_qty = int((sell_qty // 100) * 100)
            if sell_qty < 100:
                continue
            try:
                rsp = post("/api/claw/mockTrading/trade", {
                    "type": "sell",
                    "stockCode": code,
                    "quantity": sell_qty,
                    "useMarketPrice": True,
                })
                sold_any = True
                append_log(logf, {
                    "ts": now.isoformat(), "event": "risk_reduce_single_position",
                    "stockCode": code, "sellQty": sell_qty, "ratio": round(ratio, 4), "resp": rsp
                })
            except Exception as e:
                append_log(logf, {
                    "ts": now.isoformat(), "event": "risk_reduce_single_position_error",
                    "stockCode": code, "err": str(e)
                })

        append_log(logf, {
            "ts": now.isoformat(),
            "event": "risk_priority_window",
            "note": "14:30 risk-first: allow new buy orders" if allow_buy_1430 else "14:30 risk-first: no new buy orders",
            "allowBuyAt1430": allow_buy_1430,
            "overSingleCount": len(over_single),
            "soldAny": sold_any
        })
        if not allow_buy_1430:
            save_state(state)
            return

    if over_single:
        append_log(logf, {
            "ts": now.isoformat(),
            "event": "skip_buy_due_single_position_limit",
            "violations": [{"stockCode": x[0].get("secCode"), "ratio": round(x[2], 4)} for x in over_single]
        })
        save_state(state)
        return

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

    # Four-layer pipeline candidates
    candidates = pick_candidates_with_layers(logf, now)
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
