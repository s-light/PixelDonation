#!/usr/bin/env python3
"""Analyse a SerialPlot CSV from PixelDonation firmware.

Usage:
    python tools/analyse_plot.py temp/plot.csv [--window 20 40]

Columns expected: raw,filtered,baseline,delta,event,above_count,state
(above_count and state are optional — present only in firmware >= debug build)
"""

import argparse
import csv
import sys
from pathlib import Path


def load(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    # strip SerialPlot leading zeros (buffering before board starts)
    nonzero = [r for r in rows if any(v not in ("0", "") for v in r.values())]
    return rows, nonzero


def summarise(nonzero, cols):
    print(f"Non-zero rows: {len(nonzero)}")
    for col in cols:
        vals = [float(r[col]) for r in nonzero if r.get(col, "") not in ("", None)]
        if vals:
            print(f"  {col:>12}: min={min(vals):>8.0f}  max={max(vals):>8.0f}  mean={sum(vals)/len(vals):>8.1f}")


def find_events(nonzero):
    return [(i, r) for i, r in enumerate(nonzero) if r.get("event", "0") == "1"]


def find_raw_dips(nonzero, threshold=20000):
    return [(i, r) for i, r in enumerate(nonzero) if int(r["raw"]) < threshold]


def find_state_transitions(nonzero):
    transitions = []
    prev = nonzero[0].get("state", "0")
    for i, r in enumerate(nonzero[1:], 1):
        cur = r.get("state", "0")
        if cur != prev:
            transitions.append((i, prev, cur, r))
            prev = cur
    return transitions


def show_window(nonzero, center, before=20, after=40, label=""):
    has_cnt = "above_count" in nonzero[0]
    has_st = "state" in nonzero[0]
    header = f"{'idx':>5} {'raw':>6} {'filt':>6} {'base':>6} {'delta':>7} {'ev':>2}"
    if has_cnt:
        header += f" {'cnt':>4}"
    if has_st:
        header += f" {'st':>2}"
    if label:
        print(f"\n=== {label} ===")
    print(header)
    start, end = max(0, center - before), min(len(nonzero), center + after)
    for i in range(start, end):
        r = nonzero[i]
        mark = " <--" if r.get("event", "0") == "1" else ""
        line = f"{i:>5} {r['raw']:>6} {r['filtered']:>6} {r['baseline']:>6} {r['delta']:>7} {r.get('event','?'):>2}"
        if has_cnt:
            line += f" {r.get('above_count','?'):>4}"
        if has_st:
            line += f" {r.get('state','?'):>2}"
        print(line + mark)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="Path to SerialPlot CSV")
    ap.add_argument("--dip", type=int, default=20000, help="Raw threshold for coin dip detection (default 20000)")
    ap.add_argument("--window", type=int, nargs=2, default=[20, 40], metavar=("BEFORE", "AFTER"))
    args = ap.parse_args()

    path = Path(args.csv)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    rows, nonzero = load(path)
    if not nonzero:
        print("No non-zero data found.")
        sys.exit(0)

    cols = list(nonzero[0].keys())
    print(f"File: {path}  ({len(rows)} total rows, {len(rows)-len(nonzero)} leading zeros stripped)")
    print(f"Columns: {cols}\n")

    summarise(nonzero, cols)

    events = find_events(nonzero)
    print(f"\nEvents (event=1): {len(events)}")
    for i, r in events:
        print(f"  row {i:4d}: delta={r['delta']:>7}  state={r.get('state','?')}  cnt={r.get('above_count','?')}")

    dips = find_raw_dips(nonzero, args.dip)
    print(f"\nRaw dips below {args.dip}: {len(dips)}")
    for i, r in dips:
        print(f"  row {i:4d}: raw={r['raw']:>6}  delta={r['delta']:>7}  state={r.get('state','?')}")

    transitions = find_state_transitions(nonzero)
    if transitions:
        print(f"\nState transitions: {len(transitions)}")
        for i, frm, to, r in transitions:
            print(f"  row {i:4d}: {frm} -> {to}  delta={r['delta']:>7}  cnt={r.get('above_count','?')}")

    before, after = args.window
    for i, r in events:
        show_window(nonzero, i, before, after, label=f"EVENT at row {i} (delta={r['delta']})")

    for i, r in dips:
        # only show dip window if not already covered by an event window
        if not any(abs(i - ei) <= before + after for ei, _ in events):
            show_window(nonzero, i, before, after, label=f"RAW DIP at row {i} (raw={r['raw']})")


if __name__ == "__main__":
    main()
