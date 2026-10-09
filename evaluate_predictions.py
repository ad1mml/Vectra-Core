#!/usr/bin/env python3
"""
VectraCore prediction evaluator (read-only).

Reads data/predictions.jsonl written by benchmark.py, fetches candles from
Twelve Data, and estimates whether TP or SL was hit first AFTER the logged
prediction timestamp.

Usage from the project directory:
    python3 evaluate_predictions.py

Requirements:
- benchmark.py has created data/predictions.jsonl
- TWELVE_DATA is set in the environment or in a .env file
- `requests` is installed (normally already used by the app)

This script does not modify app.py or predictions.jsonl. It writes a report
to data/benchmark_report.json. Predictions with missing/invalid levels,
unknown timeframe, or ambiguous same-candle TP/SL touches are not counted
as wins or losses.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "predictions.jsonl"
REPORT_FILE = DATA_DIR / "benchmark_report.json"
API_URL = "https://api.twelvedata.com/time_series"

# Twelve Data interval names in minutes. Extend if your app logs other formats.
TIMEFRAME_MAP = {
    "1": "1min", "1m": "1min", "1min": "1min",
    "5": "5min", "5m": "5min", "5min": "5min",
    "15": "15min", "15m": "15min", "15min": "15min",
    "30": "30min", "30m": "30min", "30min": "30min",
    "60": "1h", "1h": "1h", "1hr": "1h",
    "120": "2h", "2h": "2h",
    "240": "4h", "4h": "4h",
    "D": "1day", "1d": "1day", "1day": "1day",
    "W": "1week", "1w": "1week", "1week": "1week",
}
MISSING = {"", "n/a", "na", "none", "null", "unknown", "-", "not available for this chart"}

def load_dotenv():
    """Small .env reader; does not print or expose any secrets."""
    path = BASE_DIR / ".env"
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass

def parse_number(value: Any):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s.lower() in MISSING:
        return None
    # Avoid accidentally interpreting arbitrary text as a price.
    s = re.sub(r"^[\s$€£]+", "", s)
    s = s.replace(",", "")
    match = re.fullmatch(r"[-+]?\d*\.?\d+", s)
    if not match:
        return None
    try:
        return float(s)
    except ValueError:
        return None

def parse_timestamp(value: Any):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            # benchmark.py writes UTC ISO timestamps. Treat naive values as UTC.
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None

def get_field(record, prediction, *names):
    for source in (prediction, record):
        if not isinstance(source, dict):
            continue
        for name in names:
            value = source.get(name)
            if value is not None and str(value).strip() != "":
                return value
    return None

def normalize_symbol(value):
    if value is None:
        return None
    symbol = str(value).strip().upper().replace(" ", "")
    if symbol.lower() in MISSING or not symbol:
        return None
    return symbol

def load_records():
    if not LOG_FILE.exists():
        print(f"ERROR: prediction log not found: {LOG_FILE}")
        print("First make sure benchmark.py has logged at least one prediction.")
        sys.exit(1)
    records = []
    with LOG_FILE.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    records.append((line_number, row))
            except json.JSONDecodeError:
                print(f"WARNING: skipping malformed JSON on line {line_number}")
    return records

def fetch_candles(symbol, interval, api_key, start_dt, end_dt):
    try:
        import requests
    except ImportError:
        print("ERROR: Python package 'requests' is missing. Install it in your PythonAnywhere virtualenv.")
        sys.exit(1)

    # Fetch a bounded number of candles and then filter strictly to timestamps
    # after the prediction. We intentionally don't count the candle containing
    # the prediction timestamp, as its high/low may have happened beforehand.
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 5000,
        "apikey": api_key,
        "format": "JSON",
    }
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or "values" not in payload:
        message = payload.get("message", "Unexpected Twelve Data response") if isinstance(payload, dict) else "Unexpected API response"
        raise RuntimeError(str(message)[:300])

    candles = []
    for item in payload.get("values", []):
        try:
            dt = datetime.strptime(item["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            candle = {
                "time": dt,
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
            }
            if start_dt < dt <= end_dt:
                candles.append(candle)
        except (KeyError, ValueError, TypeError):
            continue
    candles.sort(key=lambda c: c["time"])
    return candles

def evaluate_one(record, prediction, candles):
    decision = str(get_field(record, prediction, "decision", "direction", "signal", "action") or "").strip().lower()
    entry = parse_number(get_field(record, prediction, "entry", "entry_price"))
    sl = parse_number(get_field(record, prediction, "stop_loss", "sl"))
    tp = parse_number(get_field(record, prediction, "take_profit", "target", "tp"))
    if decision not in {"buy", "long", "sell", "short"}:
        return {"outcome": "not_evaluable", "reason": f"decision is {decision or 'missing/Wait'}"}
    if entry is None or sl is None or tp is None:
        return {"outcome": "not_evaluable", "reason": "missing or non-numeric entry/SL/TP"}
    side = "buy" if decision in {"buy", "long"} else "sell"
    if (side == "buy" and not (sl < entry < tp)) or (side == "sell" and not (tp < entry < sl)):
        return {"outcome": "not_evaluable", "reason": "levels do not match trade direction"}

    risk = abs(entry - sl)
    if risk <= 0:
        return {"outcome": "not_evaluable", "reason": "zero risk distance"}
    for candle in candles:
        if side == "buy":
            sl_hit = candle["low"] <= sl
            tp_hit = candle["high"] >= tp
        else:
            sl_hit = candle["high"] >= sl
            tp_hit = candle["low"] <= tp

        if sl_hit and tp_hit:
            return {
                "outcome": "ambiguous",
                "reason": "SL and TP both touched in the same candle; intrabar order unknown",
                "candle_time": candle["time"].isoformat(),
            }
        if sl_hit:
            return {"outcome": "loss", "r_multiple": -1.0, "candle_time": candle["time"].isoformat()}
        if tp_hit:
            reward = abs(tp - entry)
            return {"outcome": "win", "r_multiple": reward / risk, "candle_time": candle["time"].isoformat()}
    return {"outcome": "pending", "reason": "neither SL nor TP touched in available post-prediction candles"}

def main():
    load_dotenv()
    api_key = (os.environ.get("TWELVE_DATA") or os.environ.get("TWELVE_DATA_KEY") or "").strip()
    if not api_key:
        print("ERROR: TWELVE_DATA key not found in environment or .env. The key was not printed.")
        sys.exit(1)

    rows = load_records()
    # Optional --days N controls the maximum age of predictions to evaluate.
    days = 30
    if len(sys.argv) >= 3 and sys.argv[1] == "--days":
        try:
            days = max(1, min(365, int(sys.argv[2])))
        except ValueError:
            print("Usage: python3 evaluate_predictions.py [--days 30]")
            sys.exit(2)
    now = datetime.now(timezone.utc)
    oldest_allowed = now.timestamp() - days * 86400
    details = []
    cache = {}
    skipped = 0

    for line_number, record in rows:
        prediction = record.get("prediction", {})
        if not isinstance(prediction, dict):
            prediction = {}
        timestamp = parse_timestamp(record.get("timestamp"))
        symbol = normalize_symbol(get_field(record, prediction, "symbol", "pair", "asset", "market"))
        timeframe_raw = get_field(record, prediction, "timeframe", "interval")
        timeframe = TIMEFRAME_MAP.get(str(timeframe_raw).strip()) if timeframe_raw is not None else None
        plan = str(record.get("plan") or "unknown").lower()

        base = {
            "line": line_number,
            "timestamp": timestamp.isoformat() if timestamp else record.get("timestamp"),
            "plan": plan,
            "symbol": symbol,
            "timeframe": timeframe or str(timeframe_raw or "unknown"),
        }

        if not timestamp or timestamp.timestamp() < oldest_allowed:
            details.append({**base, "outcome": "not_evaluable", "reason": f"missing timestamp or older than {days} days"})
            skipped += 1
            continue
        if not symbol or not timeframe:
            details.append({**base, "outcome": "not_evaluable", "reason": "missing symbol or unsupported timeframe"})
            skipped += 1
            continue

        # Avoid look-ahead: fetch market data only up to now, then exclude the
        # candle whose timestamp is equal to/before the prediction timestamp.
        cache_key = (symbol, timeframe, timestamp.date().isoformat())
        try:
            if cache_key not in cache:
                cache[cache_key] = fetch_candles(symbol, timeframe, api_key, timestamp, now)
                time.sleep(0.15)  # modest pacing for provider limits
            result = evaluate_one(record, prediction, cache[cache_key])
        except Exception as exc:
            result = {"outcome": "error", "reason": str(exc)[:300]}
        details.append({**base, **result})

    groups = {}
    for item in details:
        key = item.get("plan", "unknown")
        group = groups.setdefault(key, {"wins": 0, "losses": 0, "pending": 0, "ambiguous": 0, "not_evaluable": 0, "errors": 0, "r_values": []})
        outcome = item.get("outcome")
        if outcome in {"win", "loss", "pending", "ambiguous", "not_evaluable", "error"}:
            group["wins" if outcome == "win" else "losses" if outcome == "loss" else outcome] += 1
        if outcome in {"win", "loss"}:
            group["r_values"].append(float(item["r_multiple"]))

    summary = {}
    for plan, group in groups.items():
        r_values = group.pop("r_values")
        completed = group["wins"] + group["losses"]
        summary[plan] = {
            **group,
            "completed_trades": completed,
            "win_rate_percent": round(100 * group["wins"] / completed, 2) if completed else None,
            "average_r": round(mean(r_values), 3) if r_values else None,
            "expectancy_r_per_completed_trade": round(sum(r_values) / completed, 3) if completed else None,
        }

    report = {
        "generated_at": now.isoformat(),
        "lookback_days": days,
        "source_log": str(LOG_FILE),
        "note": "Historical estimate only, not proof of future profitability. Candle-only data cannot determine order when SL and TP are both touched within one candle.",
        "summary_by_plan": summary,
        "predictions": details,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Evaluated {len(details)} logged records.")
    print(f"Report saved to: {REPORT_FILE}")
    print()
    if not summary:
        print("No prediction records were available.")
    for plan, values in summary.items():
        print(f"[{plan.upper()}] wins={values['wins']} losses={values['losses']} "
              f"win_rate={values['win_rate_percent']}% avg_R={values['average_r']} "
              f"expectancy_R={values['expectancy_r_per_completed_trade']} "
              f"pending={values['pending']} ambiguous={values['ambiguous']} "
              f"not_evaluable={values['not_evaluable']} errors={values['errors']}")
    print("\nReminder: entries with missing numeric levels (including WAIT predictions) are not counted as wins/losses.")

if __name__ == "__main__":
    main()
