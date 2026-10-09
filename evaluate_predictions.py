#!/usr/bin/env python3
"""
VectraCore prediction evaluator.

Evaluates logged Buy/Sell predictions against subsequent Twelve Data candles.
This is a historical measurement tool, not a profitability guarantee.

Usage:
    python3 evaluate_predictions.py
    python3 evaluate_predictions.py --days 30
    python3 evaluate_predictions.py --days 30 --exclude-lines 1,2
    python3 evaluate_predictions.py --log-file path/to/other.jsonl

Environment:
    TWELVE_DATA or TWELVE_DATA_KEY, or a TWELVE_DATA entry in .env

Important limitations:
- Intrabar order is unknowable from OHLC candles when SL and TP are both hit.
- This evaluator excludes the candle whose start timestamp is at/before the
  prediction timestamp to avoid counting price movement that may predate it.
- Twelve Data's outputsize limits history. Insufficient candle coverage is
  reported separately and never silently counted as a pending trade.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "predictions.jsonl"
REPORT_FILE = DATA_DIR / "benchmark_report.json"
API_URL = "https://api.twelvedata.com/time_series"
DEFAULT_DAYS = 30
MAX_DAYS = 365
OUTPUTSIZE = 5000
REQUEST_TIMEOUT = 30
REQUEST_PAUSE_SECONDS = 0.15

TIMEFRAME_MAP = {
    "1": "1min", "1m": "1min", "1min": "1min",
    "5": "5min", "5m": "5min", "5min": "5min",
    "15": "15min", "15m": "15min", "15min": "15min",
    "30": "30min", "30m": "30min", "30min": "30min",
    "45": "45min", "45m": "45min", "45min": "45min",
    "60": "1h", "60m": "1h", "1h": "1h", "1hr": "1h",
    "120": "2h", "120m": "2h", "2h": "2h",
    "240": "4h", "240m": "4h", "4h": "4h",
    "D": "1day", "1d": "1day", "1day": "1day",
    "W": "1week", "1w": "1week", "1week": "1week",
}
MISSING = {
    "", "n/a", "na", "none", "null", "unknown", "-", "not available for this chart",
    "not visible on this chart", "not available", "not provided",
}
VALID_OUTCOMES = {
    "win", "loss", "pending", "ambiguous", "not_evaluable",
    "no_trade", "insufficient_data", "error",
}


def load_dotenv() -> None:
    """Load simple KEY=value entries without overriding environment variables."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError as exc:
        print(f"WARNING: Could not read .env ({exc}).", file=sys.stderr)


def parse_number(value: Any):
    """Parse a numeric level without guessing prices from arbitrary prose."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = str(value).strip()
    if text.lower() in MISSING:
        return None
    text = re.sub(r"^[\s$€£]+", "", text).replace(",", "")
    if not re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", text):
        return None
    try:
        number = float(text)
        return number if math.isfinite(number) else None
    except ValueError:
        return None


def parse_timestamp(value: Any):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            # benchmark.py writes ISO UTC timestamps; naive legacy values use UTC.
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def get_field(record: dict, prediction: dict, *names):
    """Read prediction fields first, then legacy top-level fields."""
    for source in (prediction, record):
        if not isinstance(source, dict):
            continue
        for name in names:
            value = source.get(name)
            if value is not None and str(value).strip():
                return value
    return None


SYMBOL_ALIASES = {
    "GOLD": "XAU/USD", "XAUUSD": "XAU/USD",
    "SILVER": "XAG/USD", "XAGUSD": "XAG/USD",
}
CRYPTO_BASES = ("BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "LTC", "BNB", "DOT", "LINK")


def to_provider_symbol(symbol):
    """Map common chart tickers to Twelve Data's format (EURUSD -> EUR/USD)."""
    if not symbol or "/" in symbol:
        return symbol
    if symbol in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[symbol]
    crypto = re.fullmatch(r"(" + "|".join(CRYPTO_BASES) + r")(USDT|USD)", symbol)
    if crypto:
        return f"{crypto.group(1)}/{crypto.group(2)}"
    if re.fullmatch(r"[A-Z]{6}", symbol):
        return f"{symbol[:3]}/{symbol[3:]}"
    return symbol


def normalize_symbol(value):
    if value is None:
        return None
    symbol = str(value).strip().upper()
    lowered = symbol.lower()
    if lowered in MISSING or "identifiable" in lowered or "not visible" in lowered:
        return None
    # Remove whitespace, then map to the provider's format.
    symbol = re.sub(r"\s+", "", symbol)
    return to_provider_symbol(symbol) or None


def normalize_decision(record: dict, prediction: dict) -> str:
    """Return buy/sell/wait/unknown, preferring explicit normalized fields."""
    for field in ("direction", "signal", "action", "decision", "final_decision"):
        value = get_field(record, prediction, field)
        if value is None:
            continue
        text = str(value).strip().lower()
        if re.match(r"^(buy|long)\b", text):
            return "buy"
        if re.match(r"^(sell|short)\b", text):
            return "sell"
        if re.match(r"^(hold|wait|no[- ]trade|no trade|skip)\b", text):
            return "wait"
    return "unknown"


def extract_labeled_price(text: str, labels: tuple[str, ...]):
    """Extract only a number immediately following a recognized level label."""
    for label in labels:
        pattern = (
            r"(?i)(?:\b" + label + r"\b)\s*(?:is|at|:|=)?\s*"
            r"(?:price\s*)?[$€£]?\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))"
        )
        match = re.search(pattern, text)
        if match:
            value = parse_number(match.group(1))
            if value is not None:
                return value
    return None


def resolve_level(record: dict, prediction: dict, fields: tuple[str, ...],
                  decision_text: str, labels: tuple[str, ...]):
    value = parse_number(get_field(record, prediction, *fields))
    if value is not None:
        return value
    return extract_labeled_price(decision_text, labels)


def load_records(log_file=LOG_FILE):
    if not log_file.exists():
        raise FileNotFoundError(
            f"Prediction log not found: {log_file}. Ensure benchmark.py has logged predictions."
        )
    records = []
    malformed = 0
    with log_file.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    records.append((line_number, row))
                else:
                    malformed += 1
                    print(f"WARNING: ignoring non-object JSON on line {line_number}")
            except json.JSONDecodeError:
                malformed += 1
                print(f"WARNING: skipping malformed JSON on line {line_number}")
    return records, malformed


def parse_candle_datetime(value: Any):
    """Twelve Data requests below explicitly ask for UTC timestamps."""
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return parse_timestamp(text)


def fetch_candles(symbol, interval, api_key, start_date=None):
    """Fetch the latest bounded candle set; filtering is per prediction later."""
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "Python package 'requests' is missing in this environment."
        ) from exc

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": OUTPUTSIZE,
        "apikey": api_key,
        "format": "JSON",
        "timezone": "UTC",
        "order": "ASC",
    }
    if start_date is not None:
        # With order=ASC, Twelve Data returns the first OUTPUTSIZE candles at/after
        # start_date, so the window from the oldest prediction onward is covered.
        params["start_date"] = start_date.strftime("%Y-%m-%d %H:%M:%S")
    response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected Twelve Data response type.")
    if "values" not in payload:
        message = payload.get("message") or payload.get("code") or "No candle values returned"
        raise RuntimeError(str(message)[:300])

    candles = []
    for item in payload.get("values") or []:
        try:
            dt = parse_candle_datetime(item.get("datetime"))
            open_price = parse_number(item.get("open"))
            high = parse_number(item.get("high"))
            low = parse_number(item.get("low"))
            close = parse_number(item.get("close"))
            if dt is None or None in (open_price, high, low, close):
                continue
            if high < low or high < max(open_price, close) or low > min(open_price, close):
                continue
            candles.append({
                "time": dt, "open": open_price, "high": high,
                "low": low, "close": close,
            })
        except (AttributeError, TypeError, ValueError):
            continue

    # Deduplicate timestamps defensively, then sort oldest-first.
    by_time = {candle["time"]: candle for candle in candles}
    return sorted(by_time.values(), key=lambda candle: candle["time"])


def evaluate_one(record: dict, prediction: dict, candles: list, timestamp):
    decision = normalize_decision(record, prediction)
    if decision == "wait":
        return {"outcome": "no_trade", "reason": "explicit Hold/Wait/no-trade decision"}
    if decision == "unknown":
        return {"outcome": "not_evaluable", "reason": "missing or unrecognized Buy/Sell decision"}

    combined_text = " | ".join(
        str(get_field(record, prediction, field) or "")
        for field in ("decision", "final_decision", "analysis", "reasoning")
    )
    entry = resolve_level(
        record, prediction, ("entry", "entry_price"), combined_text,
        ("entry", "entry price"),
    )
    sl = resolve_level(
        record, prediction, ("stop_loss", "sl"), combined_text,
        ("stop loss", "stop-loss", "stop", "sl"),
    )
    tp = resolve_level(
        record, prediction, ("take_profit", "take_profit_1", "target", "tp"),
        combined_text, ("take profit", "take-profit", "take_profit", "target", "tp"),
    )
    if entry is None or sl is None or tp is None:
        return {"outcome": "not_evaluable", "reason": "missing or non-numeric entry/SL/TP"}
    if min(entry, sl, tp) <= 0:
        return {"outcome": "not_evaluable", "reason": "price levels must be positive"}
    if decision == "buy" and not (sl < entry < tp):
        return {"outcome": "not_evaluable", "reason": "Buy levels must satisfy SL < entry < TP"}
    if decision == "sell" and not (tp < entry < sl):
        return {"outcome": "not_evaluable", "reason": "Sell levels must satisfy TP < entry < SL"}

    risk = abs(entry - sl)
    if not math.isfinite(risk) or risk <= 0:
        return {"outcome": "not_evaluable", "reason": "invalid or zero risk distance"}

    post_candles = [c for c in candles if timestamp < c["time"]]
    # If the provider returned its full requested limit and the prediction is
    # older than the oldest available candle, history may be truncated.
    # A short candle list is not sufficient evidence of truncation.
    if candles and len(candles) >= OUTPUTSIZE and timestamp < candles[0]["time"]:
        return {
            "outcome": "insufficient_data",
            "reason": "prediction predates earliest candle available from provider",
            "earliest_candle": candles[0]["time"].isoformat(),
        }

    if not post_candles:
        return {
            "outcome": "pending",
            "reason": "no complete candle starting after prediction timestamp is available",
        }

    for candle in post_candles:
        if decision == "buy":
            sl_hit = candle["low"] <= sl
            tp_hit = candle["high"] >= tp
        else:
            sl_hit = candle["high"] >= sl
            tp_hit = candle["low"] <= tp

        if sl_hit and tp_hit:
            return {
                "outcome": "ambiguous",
                "reason": "SL and TP touched in the same candle; intrabar order is unknown",
                "candle_time": candle["time"].isoformat(),
            }
        if sl_hit:
            return {
                "outcome": "loss", "r_multiple": -1.0,
                "candle_time": candle["time"].isoformat(),
            }
        if tp_hit:
            return {
                "outcome": "win", "r_multiple": round(abs(tp - entry) / risk, 8),
                "candle_time": candle["time"].isoformat(),
            }
    return {
        "outcome": "pending",
        "reason": "neither SL nor TP touched in available post-prediction candles",
        "post_prediction_candles": len(post_candles),
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Evaluate logged VectraCore predictions.")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help=f"lookback window in days (1-{MAX_DAYS}, default {DEFAULT_DAYS})")
    parser.add_argument("--exclude-lines", default="",
                        help="comma-separated log line numbers to ignore (e.g. test records): 1,2")
    parser.add_argument("--log-file", default=None, help="evaluate a different JSONL log")
    parser.add_argument("--report-file", default=None, help="write the report to this path")
    args = parser.parse_args(argv)
    args.log_file = Path(args.log_file) if args.log_file else LOG_FILE
    if args.report_file:
        args.report_file = Path(args.report_file)
    elif args.log_file != LOG_FILE:
        args.report_file = args.log_file.with_name(args.log_file.stem + "_report.json")
    else:
        args.report_file = REPORT_FILE
    args.days = max(1, min(MAX_DAYS, args.days))
    try:
        args.excluded = {int(x) for x in args.exclude_lines.split(",") if x.strip()}
    except ValueError:
        parser.error("--exclude-lines must be comma-separated integers")
    return args


def summarize(details):
    plans = {}
    for item in details:
        plan = item.get("plan", "unknown")
        group = plans.setdefault(plan, {
            "wins": 0, "losses": 0, "pending": 0, "ambiguous": 0,
            "not_evaluable": 0, "no_trade": 0, "insufficient_data": 0,
            "errors": 0, "gate_blocked": 0, "r_values": [],
        })
        outcome = item.get("outcome")
        if outcome in VALID_OUTCOMES:
            key = {"win": "wins", "loss": "losses", "error": "errors"}.get(outcome, outcome)
            group[key] += 1
        if item.get("gate_blocked"):
            group["gate_blocked"] += 1
        if outcome in {"win", "loss"}:
            group["r_values"].append(float(item["r_multiple"]))

    summary = {}
    for plan, group in plans.items():
        r_values = group.pop("r_values")
        completed = group["wins"] + group["losses"]
        summary[plan] = {
            **group,
            "completed_trades": completed,
            "win_rate_percent": round(100 * group["wins"] / completed, 2) if completed else None,
            "average_r": round(mean(r_values), 3) if r_values else None,
            "expectancy_r_per_completed_trade": round(sum(r_values) / completed, 3) if completed else None,
            "evaluable_trade_records": completed + group["pending"] + group["ambiguous"],
        }
    return summary


def main():
    args = parse_args(sys.argv[1:])
    days = args.days

    load_dotenv()
    api_key = (os.environ.get("TWELVE_DATA") or os.environ.get("TWELVE_DATA_KEY") or "").strip()
    if not api_key:
        print("ERROR: Twelve Data key not found in environment or .env. Key was not printed.", file=sys.stderr)
        return 1

    try:
        rows, malformed = load_records(args.log_file)
    except (OSError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    oldest_allowed = now.timestamp() - days * 86400
    details = []
    candle_cache = {}
    request_count = 0

    # Ask the provider for candles starting a day before the lookback window so
    # short timeframes still cover every prediction we evaluate.
    candle_start = now - timedelta(days=days + 1)

    for line_number, record in rows:
        if line_number in args.excluded:
            continue
        prediction = record.get("prediction", {})
        if not isinstance(prediction, dict):
            prediction = {}
        timestamp = parse_timestamp(record.get("timestamp"))
        symbol = normalize_symbol(get_field(record, prediction, "symbol", "pair", "asset", "market"))
        raw_timeframe = get_field(record, prediction, "timeframe", "interval")
        timeframe_key = str(raw_timeframe).strip().lower() if raw_timeframe is not None else ""
        timeframe = TIMEFRAME_MAP.get(timeframe_key) or TIMEFRAME_MAP.get(str(raw_timeframe).strip()) if raw_timeframe is not None else None
        plan = str(record.get("plan") or "unknown").strip().lower()

        base = {
            "line": line_number,
            "timestamp": timestamp.isoformat() if timestamp else record.get("timestamp"),
            "plan": plan,
            "symbol": symbol,
            "timeframe": timeframe or str(raw_timeframe or "unknown"),
        }

        if not timestamp:
            details.append({**base, "outcome": "not_evaluable", "reason": "missing or invalid prediction timestamp"})
            continue
        if timestamp.timestamp() < oldest_allowed:
            details.append({**base, "outcome": "not_evaluable", "reason": f"prediction older than requested {days}-day lookback"})
            continue
        if timestamp > now:
            details.append({**base, "outcome": "not_evaluable", "reason": "prediction timestamp is in the future"})
            continue
        # A Wait/no-trade needs no candles, so it must not be reported as
        # "not evaluable" just because the symbol or timeframe was unreadable.
        if normalize_decision(record, prediction) == "wait":
            entry = {**base, "outcome": "no_trade",
                     "reason": "explicit Hold/Wait/no-trade decision"}
            meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
            pre = meta.get("pre_gate") if isinstance(meta.get("pre_gate"), dict) else {}
            if re.match(r"^(buy|sell|long|short)\b", str(pre.get("decision") or "").strip().lower()):
                entry["gate_blocked"] = True
                entry["reason"] = f"AI proposed {pre.get('decision')}; blocked by a safety gate"
                entry["proposed"] = {k: pre.get(k) for k in ("entry", "stop_loss", "take_profit", "take_profit_1")}
            details.append(entry)
            continue
        if not symbol or not timeframe:
            details.append({**base, "outcome": "not_evaluable", "reason": "missing symbol or unsupported timeframe"})
            continue

        cache_key = (symbol, timeframe)
        try:
            if cache_key not in candle_cache:
                candle_cache[cache_key] = fetch_candles(symbol, timeframe, api_key, candle_start)
                request_count += 1
                if request_count:
                    time.sleep(REQUEST_PAUSE_SECONDS)
            result = evaluate_one(record, prediction, candle_cache[cache_key], timestamp)
        except Exception as exc:
            # Do not print API keys or request URLs in errors.
            message = str(exc).replace(api_key, "[REDACTED]")[:300]
            result = {"outcome": "error", "reason": message}
        details.append({**base, **result})

    summary = summarize(details)
    report = {
        "generated_at": now.isoformat(),
        "lookback_days": days,
        "source_log": str(args.log_file),
        "records_read": len(rows),
        "malformed_lines": malformed,
        "provider": "Twelve Data",
        "candle_timezone_requested": "UTC",
        "candle_limit_per_symbol_timeframe": OUTPUTSIZE,
        "excluded_log_lines": sorted(args.excluded),
        "summary_by_plan": summary,
        "predictions": details,
        "methodology": [
            "Only Buy/Sell predictions with numeric, directionally valid entry/SL/TP are trade-evaluable.",
            "Hold/Wait/no-trade decisions are reported as no_trade and excluded from trade win-rate denominators.",
            "gate_blocked counts no_trade records where the AI proposed Buy/Sell but a code safety gate (e.g. the 1:1 reward-to-risk floor) changed it to Wait.",
            "Only candles with start timestamps strictly later than the prediction timestamp are evaluated.",
            "If SL and TP touch in the same candle, outcome is ambiguous and excluded from wins/losses.",
            "Pending means candles were available after the prediction but neither level was touched.",
            "insufficient_data means provider history does not cover the prediction timestamp.",
            "This OHLC-based evaluation cannot model spreads, commissions, slippage, entry fill, or intra-candle price path.",
        ],
        "note": "Historical candle-based estimate only; not proof of future profitability. Verify provider timezone and coverage before relying on the report.",
    }
    try:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: Could not write report: {exc}", file=sys.stderr)
        return 1

    print(f"Evaluated {len(details)} logged records ({malformed} malformed lines skipped).")
    print(f"Report saved to: {args.report_file}")
    print()
    if not summary:
        print("No prediction records were available.")
    for plan, values in summary.items():
        print(
            f"[{plan.upper()}] wins={values['wins']} losses={values['losses']} "
            f"win_rate={values['win_rate_percent']}% avg_R={values['average_r']} "
            f"expectancy_R={values['expectancy_r_per_completed_trade']} "
            f"pending={values['pending']} ambiguous={values['ambiguous']} "
            f"no_trade={values['no_trade']} gate_blocked={values['gate_blocked']} insufficient_data={values['insufficient_data']} "
            f"not_evaluable={values['not_evaluable']} errors={values['errors']}"
        )
    print("\nReminder: no-trade, pending, ambiguous, missing-level, and insufficient-data records are not wins/losses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
