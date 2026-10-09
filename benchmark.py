"""Lightweight JSONL logger for VectraCore prediction benchmarking.

Place this file in the same directory as app.py. It records one compact JSON
object per prediction in data/predictions.jsonl. Logging failures are handled
by the caller in app.py and should not interrupt a prediction.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "data"
LOG_FILE = LOG_DIR / "predictions.jsonl"


def _safe_value(value: Any) -> Any:
    """Convert values to JSON-safe, bounded values without storing huge payloads."""
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, str) and len(value) > 2000:
            return value[:2000]
        return value
    if isinstance(value, Mapping):
        return {
            str(k): _safe_value(v)
            for k, v in list(value.items())[:80]
            if not str(k).lower() in {
                "messages", "chat_history", "conversation", "conversation_history",
                "raw_prompt", "prompt", "api_key", "secret", "password",
            }
        }
    if isinstance(value, (list, tuple)):
        return [_safe_value(v) for v in value[:30]]
    return str(value)[:500]


def log_prediction(user_email: str, plan: str, result: Mapping[str, Any]) -> None:
    """Append a compact prediction record; never intentionally log chat history."""
    if not isinstance(result, Mapping):
        raise TypeError("result must be a mapping")

    # Keep the model's prediction fields useful for later evaluation while
    # excluding session identifiers and conversational history.
    prediction_fields = (
        "symbol", "pair", "asset", "market", "timeframe", "direction",
        "signal", "action", "entry", "entry_price", "stop_loss", "take_profit",
        "target", "confidence", "buy_probability", "sell_probability",
        "risk_reward", "rr", "status", "analysis", "reasoning",
    )
    prediction = {
    key: _safe_value(result[key])
    for key in prediction_fields
    if key in result
    }

    # Normalize the timeframe when it is present.
    timeframe = prediction.get("timeframe")

    if isinstance(timeframe, str):
        timeframe = timeframe.strip().lower()

        aliases = {
            "1m": "1min",
            "5m": "5min",
            "15": "15min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1h",
            "4h": "4h",
            "1d": "1day",
        }

    prediction["timeframe"] = aliases.get(
        timeframe, timeframe
    )

    # If the result uses a different schema, keep a small safe subset so the
    # record is still useful without copying the entire response/session.
    if not prediction:
        prediction = _safe_value(result)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "plan": str(plan)[:40],
        "user_email": str(user_email)[:254],
        "prediction": prediction,
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
