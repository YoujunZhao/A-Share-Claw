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
        s = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    else:
        s = {"date": None, "trades": 0}
    s.setdefault("holdMeta", {})
    s.setdefault("slotHistory", [])
    return s


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


def normalize_slots(slots):
    return slots[-20:]


def register_slot(state, hhmm):
    hist = normalize_slots(state.get("slotHistory") or [])
    if not hist or hist[-1] != hhmm:
        hist.append(hhmm)
    state["slotHistory"] = normalize_slots(hist)


def current_slot_index(state):
    hist = state.get("slotHistory") or []
    return len(hist) - 1 if hist else 0


def ensure_hold_meta_for_positions(state, plist):
    meta = state.setdefault("holdMeta", {})
    live_codes = set()
    for p in plist:
        code = p.get("secCode")
        count = int(p.get("count") or 0)
        if not code or count <= 0:
            continue
        live_codes.add(code)
        item = meta.setdefault(code, {})
        item.setdefault("firstSeenDate", state.get("date"))
        item.setdefault("firstSlot", current_slot_index(state))
        item.setdefault("buyCount", 0)
        item["lastSeenDate"] = state.get("date")
        item["lastSeenSlot"] = current_slot_index(state)
        item["lastKnownCount"] = count
    for code in list(meta.keys()):
        if code not in live_codes:
            meta.pop(code, None)


def mark_buy_in_state(state, code, qty, hhmm):
    meta = state.setdefault("holdMeta", {})
    item = meta.setdefault(code, {})
    item.setdefault("firstSeenDate", state.get("date"))
    item.setdefault("firstSlot", current_slot_index(state))
    item["lastBuyDate"] = state.get("date")
    item["lastBuyTime"] = hhmm
    item["lastBuySlot"] = current_slot_index(state)
    item["buyCount"] = int(item.get("buyCount") or 0) + 1
    item["lastBuyQty"] = qty


def mark_sell_in_state(state, code, sell_qty, remaining_count):
    meta = state.setdefault("holdMeta", {})
    item = meta.setdefault(code, {})
    item["lastSellDate"] = state.get("date")
    item["lastSellSlot"] = current_slot_index(state)
    item["lastSellQty"] = sell_qty
    item["lastKnownCount"] = max(0, remaining_count)
    if remaining_count <= 0:
        meta.pop(code, None)


def get_position_signals(p):
    day_pct = float((p.get("dayProfitPct") or 0) or 0)
    total_pct = float((p.get("profitPct") or 0) or 0)
    return day_pct, total_pct


def lots_available(p):
    count = int(p.get("availCount") or p.get("count") or 0)
    return int((count // 100) * 100)


def should_sell_stale_position(p, state, code):
    meta = (state.get("holdMeta") or {}).get(code) or {}
    last_buy_slot = meta.get("lastBuySlot")
    if last_buy_slot is None:
        return False, {"reason": "no_buy_slot"}
    held_slots = current_slot_index(state) - int(last_buy_slot)
    day_pct, total_pct = get_position_signals(p)
    if held_slots < 3:
        return False, {"reason": "hold_slots_lt_3", "heldSlots": held_slots}
    if day_pct > 0.8 or total_pct > 1.5:
        return False, {"reason": "still_strong", "heldSlots": held_slots, "dayPct": day_pct, "totalPct": total_pct}
    if lots_available(p) < 100:
        return False, {"reason": "not_enough_lots", "heldSlots": held_slots}
    return True, {"reason": "stale_underperform", "heldSlots": held_slots, "dayPct": day_pct, "totalPct": total_pct}


def should_sell_tail_weak(p, candidates, state, code):
    if code in set(candidates):
        return False, {"reason": "still_in_candidates"}
    lots = lots_available(p)
    if lots < 100:
        return False, {"reason": "not_enough_lots"}
    day_pct, total_pct = get_position_signals(p)
    pos_pct = float((p.get("posPct") or 0) or 0)
    meta = (state.get("holdMeta") or {}).get(code) or {}
    held_slots = current_slot_index(state) - int(meta.get("lastBuySlot", current_slot_index(state)))
    weak = day_pct <= 0.5 and total_pct <= 1.0
    old_enough = held_slots >= 1
    if not (weak and old_enough):
        return False, {"reason": "not_weak_enough", "heldSlots": held_slots, "dayPct": day_pct, "totalPct": total_pct, "posPct": pos_pct}
    return True, {"reason": "tail_rebalance_weak", "heldSlots": held_slots, "dayPct": day_pct, "totalPct": total_pct, "posPct": pos_pct}


def execute_sell(logf, now, state, p, qty, event, reason_detail):
    code = p.get("secCode")
    if qty < 100:
        return False
    try:
        rsp = post("/api/claw/mockTrading/trade", {
            "type": "sell",
            "stockCode": code,
            "quantity": qty,
            "useMarketPrice": True,
        })
        remaining = max(0, int(p.get("count") or 0) - qty)
        mark_sell_in_state(state, code, qty, remaining)
        append_log(logf, {
            "ts": now.isoformat(), "event": event,
            "stockCode": code, "sellQty": qty,
            "detail": reason_detail,
            "resp": rsp,
        })
        return True
    except Exception as e:
        append_log(logf, {
            "ts": now.isoformat(), "event": f"{event}_error",
            "stockCode": code, "sellQty": qty,
            "detail": reason_detail,
            "err": str(e)
        })
        return False


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

    passed = []
    for c in candidates:
        ok, detail = layer2_financial_ok(c, logf, now)
        append_log(logf, {"ts": now.isoformat(), "event": "layer2_financial_check", "code": c, "ok": ok, "detail": detail})
        if ok:
            passed.append(c)
        if len(passed) >= 20:
            break

    layer3_ok = layer3_sync_watchlist(passed, logf, now)
    if not layer3_ok:
        append_log(logf, {"ts": now.isoformat(), "event": "layer3_blocked", "reason": "strict_watchlist_enabled"})
        return []

    append_log(logf, {"ts": now.isoformat(), "event": "four_layer_pipeline", "layer1": True, "layer2": True, "layer3": bool(layer3_ok), "layer4": True, "candidateCount": len(passed)})
    return passed


def cleanup_pending_orders(now, logf):
    try:
        od = post("/api/claw/mockTrading/orders", {"fltOrderDrt": 0, "fltOrderStatus": 0})
    except Exception as e:
        append_log(logf, {"ts": now.isoformat(), "event": "orders_fetch_error", "err": str(e)})
        return

    orders = (od.get("data") or {}).get("orders") or []
    for o in orders:
        st = o.get("status")
        if st not in (2, 6):
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
        state = {"date": day, "trades": 0, "holdMeta": state.get("holdMeta", {}), "slotHistory": []}

    if hhmm not in set(CFG["runTimes"]):
        return

    register_slot(state, hhmm)
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
    pos_by_code = {}
    for p in plist:
        code = p.get("secCode")
        if code:
            held_value[code] = to_yuan(p.get("value"), pos_unit)
            pos_by_code[code] = p

    ensure_hold_meta_for_positions(state, plist)

    single_cap = total_assets * CFG["maxPositionPerStock"]
    over_single = []
    for p in plist:
        code = p.get("secCode")
        value = to_yuan(p.get("value"), pos_unit)
        ratio = (value / total_assets) if total_assets > 0 else 0
        if code and ratio > CFG["maxPositionPerStock"] + 1e-9:
            over_single.append((p, value, ratio))

    sold_any = False
    sold_codes = set()
    for p, value, ratio in over_single:
        code = p.get("secCode")
        count = lots_available(p)
        if count < 100:
            continue
        px = (value / int(p.get("count") or 0)) if int(p.get("count") or 0) > 0 else 0
        if px <= 0:
            continue
        target_count = int((single_cap / px) // 100 * 100)
        sell_qty = max(0, count - target_count)
        sell_qty = int((sell_qty // 100) * 100)
        if sell_qty < 100:
            continue
        ok = execute_sell(logf, now, state, p, sell_qty, "risk_reduce_single_position", {
            "ratio": round(ratio, 4),
            "targetCount": target_count,
            "reason": "single_position_limit"
        })
        sold_any = sold_any or ok
        if ok:
            sold_codes.add(code)

    candidates = pick_candidates_with_layers(logf, now)

    for p in plist:
        code = p.get("secCode")
        if not code or code in sold_codes:
            continue
        ok, detail = should_sell_stale_position(p, state, code)
        if not ok:
            continue
        sell_qty = lots_available(p)
        ok2 = execute_sell(logf, now, state, p, sell_qty, "sell_stale_position", detail)
        sold_any = sold_any or ok2
        if ok2:
            sold_codes.add(code)

    if risk_window:
        for p in plist:
            code = p.get("secCode")
            if not code or code in sold_codes:
                continue
            ok, detail = should_sell_tail_weak(p, candidates, state, code)
            if not ok:
                continue
            sell_qty = lots_available(p)
            ok2 = execute_sell(logf, now, state, p, sell_qty, "tail_rebalance_sell", detail)
            sold_any = sold_any or ok2
            if ok2:
                sold_codes.add(code)

        append_log(logf, {
            "ts": now.isoformat(),
            "event": "risk_priority_window",
            "note": "14:30 risk-first: allow new buy orders" if allow_buy_1430 else "14:30 risk-first: no new buy orders",
            "allowBuyAt1430": allow_buy_1430,
            "overSingleCount": len(over_single),
            "soldAny": sold_any,
            "candidateCount": len(candidates),
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

    if not candidates:
        append_log(logf, {"ts": now.isoformat(), "event": "no_candidates"})
        save_state(state)
        return

    selected = None
    single_cap = total_assets * CFG["maxPositionPerStock"]
    for c in candidates:
        if c in sold_codes:
            continue
        if held_value.get(c, 0) < single_cap * 0.9:
            selected = c
            break

    if not selected:
        append_log(logf, {"ts": now.isoformat(), "event": "skip_no_symbol_under_cap", "caps": {"singleCap": single_cap}})
        save_state(state)
        return

    budget_by_single = max(0, single_cap - held_value.get(selected, 0))
    budget_by_total = max(0, total_assets * CFG["maxTotalPosition"] - total_pos_value)
    per_stock_budget = min(budget_by_single, budget_by_total, avail, total_assets * 0.08)

    if per_stock_budget < 10000:
        append_log(logf, {"ts": now.isoformat(), "event": "skip_small_budget", "budget": per_stock_budget})
        save_state(state)
        return

    qty = int((per_stock_budget / 100) // 100 * 100)
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
        mark_buy_in_state(state, selected, qty, hhmm)
    save_state(state)


if __name__ == "__main__":
    main()
