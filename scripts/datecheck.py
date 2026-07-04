#!/usr/bin/env python3
"""
datecheck.py — Deterministic date/weekday/time-distance calculator.

LLMs generate weekday and time-distance claims via semantic association, not
real arithmetic. "Wednesday" feels right because it pattern-matches prior text,
not because the model computed it. This script replaces that unreliable
inference with Python's datetime module.

Usage:
  python3 datecheck.py 2026-07-15              # What weekday is that date?
  python3 datecheck.py --since 2026-06-26      # How long ago?
  python3 datecheck.py --next-weekday 3         # Next Wednesday (3=Wed)
  python3 datecheck.py --today                  # Today's info

Works with both Chinese and English weekday names.
"""
import sys, argparse
from datetime import datetime, date, timedelta

WD_CN = ["一", "二", "三", "四", "五", "六", "日"]
WD_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def weekday_cn(d):
    return "周" + WD_CN[d.weekday()]


def weekday_en(d):
    return WD_EN[d.weekday()]


def parse(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def human_delta(days):
    if days == 0:
        return "today"
    ago = days > 0
    days = abs(days)
    if days < 7:
        s = f"{days} day(s)"
    elif days < 30:
        s = f"{days} days (~{days//7} week(s))"
    elif days < 365:
        s = f"{days} days (~{days//30} month(s))"
    else:
        s = f"{days} days (~{days//365} year(s) {(days%365)//30} month(s))"
    return s + (" ago" if ago else " from now")


def main():
    ap = argparse.ArgumentParser(description="Deterministic date calculator")
    ap.add_argument("dateval", nargs="?", help="YYYY-MM-DD — what weekday is this?")
    ap.add_argument("--since", help="YYYY-MM-DD — how long ago was this?")
    ap.add_argument("--next-weekday", help="Next occurrence of weekday (1-7 or Mon/Tue/.../Sun or 一/二/.../日)")
    ap.add_argument("--today", action="store_true", help="Show today's info")
    ap.add_argument("--lang", default="cn", choices=["cn", "en"], help="Output language")
    args = ap.parse_args()

    today = date.today()
    wd_fn = weekday_cn if args.lang == "cn" else weekday_en

    if args.today or (not args.dateval and not args.since and not args.next_weekday):
        print(f"Today: {today.isoformat()} {wd_fn(today)}")
        return

    if args.dateval:
        d = parse(args.dateval)
        delta = (today - d).days
        print(f"{d.isoformat()} is {wd_fn(d)}, {human_delta(delta)}")

    if args.since:
        d = parse(args.since)
        delta = (today - d).days
        print(f"{d.isoformat()} ({wd_fn(d)}) was {human_delta(delta)}")

    if args.next_weekday:
        target = parse_weekday(args.next_weekday)
        for i in range(1, 8):
            cand = today + timedelta(days=i)
            if cand.weekday() == target:
                print(f"Next {WD_EN[target]}: {cand.isoformat()} ({(cand-today).days} days from now)")
                break


def parse_weekday(s):
    """Accept 1-7, Mon-Sun, or 一-日."""
    s = s.strip()
    if s.isdigit():
        return int(s) - 1  # 1=Mon → 0
    s_low = s.lower()[:3]
    en_map = {d[:3].lower(): i for i, d in enumerate(WD_EN)}
    if s_low in en_map:
        return en_map[s_low]
    if s in WD_CN:
        return WD_CN.index(s)
    raise ValueError(f"Cannot parse weekday: {s}")


if __name__ == "__main__":
    main()
