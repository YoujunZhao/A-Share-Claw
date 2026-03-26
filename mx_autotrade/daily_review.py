#!/usr/bin/env python3
import os, json, datetime, pathlib, requests

BASE = os.getenv("MX_API_URL", "https://mkapi2.dfcfs.com/finskillshub")
KEY = os.getenv("MX_APIKEY")
ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "reviews"
OUT.mkdir(parents=True, exist_ok=True)

headers = {"apikey": KEY, "Content-Type": "application/json"}

def post(path, payload):
    r = requests.post(f"{BASE}{path}", headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def main():
    day = datetime.date.today().isoformat()
    bal = post('/api/claw/mockTrading/balance', {})
    pos = post('/api/claw/mockTrading/positions', {})
    ords = post('/api/claw/mockTrading/orders', {"fltOrderDrt": 0, "fltOrderStatus": 0})

    report = {
        "date": day,
        "balance": bal.get("data"),
        "positions": pos.get("data"),
        "orders": (ords.get("data") or {}).get("orders", []),
        "reflection": [
            "是否出现追涨杀跌？",
            "止损是否严格执行？",
            "仓位是否超过计划？",
            "明日是否需要降低频率或仓位？"
        ]
    }
    p = OUT / f"review-{day}.json"
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(str(p))

if __name__ == '__main__':
    if not KEY:
        raise SystemExit('MX_APIKEY missing')
    main()
