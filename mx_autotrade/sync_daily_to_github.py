#!/usr/bin/env python3
import json
import re
import datetime
import subprocess
from pathlib import Path

WORK = Path('/home/a/.openclaw/workspace')
REPO = WORK / 'A-Share-Claw'
REVIEWS = WORK / 'mx_autotrade' / 'reviews'
README_EN = REPO / 'README.md'
README_CN = REPO / 'README-CN.md'


def load_review(day: str):
    p = REVIEWS / f'review-{day}.json'
    if not p.exists():
        raise SystemExit(f'missing review file: {p}')
    return json.loads(p.read_text(encoding='utf-8'))


def latest_balance_before(day: str):
    files = sorted(REVIEWS.glob('review-*.json'))
    prev = None
    for f in files:
        d = f.stem.replace('review-', '')
        if d < day:
            prev = f
    if not prev:
        return None
    data = json.loads(prev.read_text(encoding='utf-8'))
    return (data.get('todayResult') or {}).get('balanceYuan')


def next_day_index(text: str):
    nums = [int(x) for x in re.findall(r'\|\s*Day(\d+)\s*\|', text)]
    return (max(nums) + 1) if nums else 1


def row_exists_for_balance(text: str, balance: float):
    b = f"{balance:,.2f}"
    return b in text


def append_row(text: str, row: str):
    lines = text.splitlines()
    # insert after last table row starting with | Day
    idx = -1
    for i, ln in enumerate(lines):
        if re.match(r'^\|\s*Day\d+\s*\|', ln):
            idx = i
    if idx == -1:
        raise ValueError('Day table not found in README')
    lines.insert(idx + 1, row)
    return '\n'.join(lines) + ('\n' if not text.endswith('\n') else '')


def git(*args):
    return subprocess.run(['git', *args], cwd=str(REPO), check=True, text=True, capture_output=True)


def main():
    day = datetime.date.today().isoformat()
    r = load_review(day)
    bal = float((r.get('todayResult') or {}).get('balanceYuan') or 0)
    prev_bal = latest_balance_before(day)
    if prev_bal and prev_bal != 0:
        dr = (bal - float(prev_bal)) / float(prev_bal)
    else:
        dr = 0.0

    en = README_EN.read_text(encoding='utf-8')
    cn = README_CN.read_text(encoding='utf-8')

    if row_exists_for_balance(en, bal) and row_exists_for_balance(cn, bal):
        print('already_synced')
        return

    day_idx = max(next_day_index(en), next_day_index(cn))
    row = f"| Day{day_idx} | {bal:,.2f} | {dr:+.2%} |"

    README_EN.write_text(append_row(en, row), encoding='utf-8')
    README_CN.write_text(append_row(cn, row), encoding='utf-8')

    git('add', 'README.md', 'README-CN.md')
    # commit only when staged diff exists
    diff = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=str(REPO))
    if diff.returncode == 0:
        print('no_changes')
        return

    git('commit', '-m', f'docs: add Day{day_idx} daily trading status ({day})')
    git('push', 'origin', 'main')
    head = git('rev-parse', '--short', 'HEAD').stdout.strip()
    print(f'pushed {head}')


if __name__ == '__main__':
    main()
