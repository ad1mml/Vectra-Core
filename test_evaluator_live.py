#!/usr/bin/env python3
"""
Live self-test for evaluate_predictions.py -- no AI involved.

It downloads recent EUR/USD 15-minute candles from Twelve Data, then builds
fake predictions whose outcome is KNOWN from those candles (a Buy that must
win, a Buy that must lose, a Sell that must win, a Sell that must lose) and
checks that the evaluator agrees. It also checks the candle timezone.

Run from ~/Vectra-Core with the Python that has `requests`:
    python3.10 test_evaluator_live.py

Uses one Twelve Data request. Writes nothing to data/.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import evaluate_predictions as ev

SYMBOL, TIMEFRAME = "EUR/USD", "15min"


def fmt(x: float) -> str:
    return f"{x:.5f}"


def make_record(ts, direction, entry, sl, tp):
    sign = "Buy" if direction == "buy" else "Sell"
    prediction = {
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "direction": sign,
        # Deliberately a combined string, like the real VIP output.
        "decision": f"{sign} (Entry at price {fmt(entry)}, TP at price {fmt(tp)}, SL at price {fmt(sl)})",
        "entry": fmt(entry),
        "stop_loss": fmt(sl),
        "take_profit_1": fmt(tp),
    }
    return {"timestamp": ts.isoformat(), "plan": "selftest", "prediction": prediction}, prediction


def run(candles, now=None):
    """Return a list of (name, passed, detail). Pure logic, testable offline."""
    results = []
    if len(candles) < 80:
        return [("enough candles", False, f"only {len(candles)} candles returned (need >= 80)")]

    i = len(candles) - 60
    pred_candle = candles[i]
    ts = pred_candle["time"]  # evaluator only looks at candles strictly AFTER this
    post = candles[i + 1:]
    p0 = pred_candle["close"]
    hi = max(c["high"] for c in post)
    lo = min(c["low"] for c in post)
    rng = hi - lo
    up, down = hi - p0, p0 - lo
    unreachable_low = min(lo, p0) - 0.5 * rng
    unreachable_high = max(hi, p0) + 0.5 * rng

    cases = []
    if up > 0:
        cases.append(("Buy that must WIN", "buy", p0, unreachable_low, p0 + 0.5 * up, "win"))
        cases.append(("Sell that must LOSE", "sell", p0, p0 + 0.5 * up, unreachable_low, "loss"))
    if down > 0:
        cases.append(("Buy that must LOSE", "buy", p0, p0 - 0.5 * down, unreachable_high, "loss"))
        cases.append(("Sell that must WIN", "sell", p0, unreachable_high, p0 - 0.5 * down, "win"))

    for name, direction, entry, sl, tp, expected in cases:
        record, prediction = make_record(ts, direction, entry, sl, tp)
        got = ev.evaluate_one(record, prediction, candles, ts)
        ok = got.get("outcome") == expected
        detail = f"expected {expected}, got {got.get('outcome')}"
        if ok and expected == "win":
            risk = abs(entry - sl)
            want_r = abs(tp - entry) / risk
            ok = abs(got.get("r_multiple", -99) - want_r) < 0.01
            detail += f", R={got.get('r_multiple')} (want {want_r:.3f})"
        results.append((name, ok, detail))

    # Wait and missing-decision handling.
    wait_rec = {"timestamp": ts.isoformat(), "plan": "selftest", "prediction": {"decision": "Wait", "direction": "Wait"}}
    got = ev.evaluate_one(wait_rec, wait_rec["prediction"], candles, ts)
    results.append(("Wait counts as no_trade", got.get("outcome") == "no_trade", str(got.get("outcome"))))

    miss_rec = {"timestamp": ts.isoformat(), "plan": "selftest", "prediction": {"symbol": SYMBOL, "reasoning": "x"}}
    got = ev.evaluate_one(miss_rec, miss_rec["prediction"], candles, ts)
    results.append(("Missing decision is not_evaluable", got.get("outcome") == "not_evaluable", str(got.get("outcome"))))

    # Symbol mapping.
    for raw, want in [("EURUSD", "EUR/USD"), ("SILVER", "XAG/USD"), ("XAUUSD", "XAU/USD"),
                      ("BTCUSDT", "BTC/USDT"), ("Not identifiable", None)]:
        got = ev.normalize_symbol(raw)
        results.append((f"symbol {raw!r} -> {want}", got == want, f"got {got}"))
    return results


def timezone_check(candles, now):
    last = candles[-1]["time"]
    lag_hours = (now - last).total_seconds() / 3600
    print(f"Latest candle: {last:%Y-%m-%d %H:%M} UTC | now: {now:%Y-%m-%d %H:%M} UTC | lag: {lag_hours:.2f} h")
    weekend = now.weekday() >= 5 or (now.weekday() == 4 and now.hour >= 21) or (now.weekday() == 6 and now.hour < 22)
    if weekend:
        print("Forex is closed (weekend), so a large lag is expected. Re-run on a weekday for a timezone check.")
        return True
    if -0.1 <= lag_hours <= 1.5:
        print("TIMEZONE OK: the newest candle is within ~1.5 h of now, so candle times are UTC.")
        return True
    print("TIMEZONE PROBLEM: the newest candle is far from now. Candle times may not be UTC.")
    return False


def main():
    ev.load_dotenv()
    key = (os.environ.get("TWELVE_DATA") or os.environ.get("TWELVE_DATA_KEY") or "").strip()
    if not key:
        print("ERROR: no Twelve Data key found in the environment or .env", file=sys.stderr)
        return 1
    now = datetime.now(timezone.utc)
    try:
        candles = ev.fetch_candles(SYMBOL, TIMEFRAME, key, now - timedelta(days=3))
    except Exception as exc:  # never print the key
        print("ERROR fetching candles:", str(exc).replace(key, "[REDACTED]")[:300], file=sys.stderr)
        return 1
    print(f"Fetched {len(candles)} {TIMEFRAME} candles for {SYMBOL}.")
    tz_ok = timezone_check(candles, now)

    failed = 0
    for name, ok, detail in run(candles, now):
        print(("PASS  " if ok else "FAIL  ") + f"{name}  [{detail}]")
        failed += 0 if ok else 1
    print()
    print("ALL CHECKS PASSED" if not failed and tz_ok else f"{failed} check(s) failed" + ("" if tz_ok else " + timezone problem"))
    return 0 if not failed and tz_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
