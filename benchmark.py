"""Privacy-conscious JSONL logger for VectraCore prediction benchmarking.

Place this file beside app.py. Each call appends one JSON object to
data/predictions.jsonl. It stores prediction fields only (not chat history),
normalizes common schemas/placeholders, and never stores a raw email address.

This module logs predictions; it does not determine whether a trade wins or loses.
That must be done later by the evaluator using subsequent market data.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "data"
LOG_FILE = LOG_DIR / "predictions.jsonl"

# Keep this list intentionally narrow: do not log sessions, prompts, or chat data.
PREDICTION_FIELDS = (
    "symbol", "pair", "asset", "market",
    "timeframe", "chart_timeframe",
    "direction", "signal", "action", "decision", "final_decision",
    "entry", "entry_price", "stop_loss", "sl",
    "take_profit", "take_profit_1", "take_profit_2", "take_profit_3", "tp", "target",
    "current_price", "institutional_score", "market_regime", "context_warning",
    "confidence", "probability", "buy_probability", "sell_probability",
    "risk_reward", "rr", "status",
    "analysis", "reasoning",
    "chart_type", "demand_supply", "support_resistance",
    "liquidity_sweep", "market_structure", "fair_value_gaps",
    "change_of_character",
)

_BLOCKED_KEYS = {
    "messages", "chat_history", "conversation", "conversation_history",
    "raw_prompt", "prompt", "api_key", "secret", "password",
    "authorization", "cookie", "token", "email", "user_email",
}


def _safe_value(value: Any, *, depth: int = 0) -> Any:
    """Convert a value to bounded JSON-safe data and filter sensitive keys."""
    if depth > 5:
        return "[max depth]"
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return value[:2000]
    if isinstance(value, Mapping):
        safe = {}
        for key, item in list(value.items())[:80]:
            key_text = str(key)
            if key_text.lower() in _BLOCKED_KEYS:
                continue
            safe[key_text[:100]] = _safe_value(item, depth=depth + 1)
        return safe
    if isinstance(value, (list, tuple)):
        return [_safe_value(item, depth=depth + 1) for item in value[:30]]
    return str(value)[:500]


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return normalized in {
        "", "n/a", "na", "none", "null", "unknown", "not visible",
        "not available", "not available for this chart",
        "not visible on this chart", "not applicable",
    }


def _normalize_timeframe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    timeframe = value.strip().lower()
    aliases = {
        "1m": "1min",
        "1 minute": "1min",
        "5m": "5min",
        "5 minutes": "5min",
        "15": "15min",
        "15m": "15min",
        "15 minute": "15min",
        "15 minutes": "15min",
        "30m": "30min",
        "30 minutes": "30min",
        "1h": "1h",
        "1hr": "1h",
        "1 hour": "1h",
        "2h": "2h",
        "4h": "4h",
        "4hr": "4h",
        "4 hours": "4h",
        "1d": "1day",
        "1day": "1day",
        "daily": "1day",
        "1w": "1week",
        "weekly": "1week",
    }
    return aliases.get(timeframe, timeframe or None)


def _decision_text(prediction: Mapping[str, Any]) -> str:
    for key in ("decision", "final_decision", "direction", "signal", "action"):
        value = prediction.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _normalize_direction(prediction: dict[str, Any]) -> None:
    """Infer direction only from an explicit, recognizable decision."""
    decision = _decision_text(prediction)
    normalized = decision.strip().lower()

    if re.match(r"^(buy|long)\b", normalized):
        prediction["direction"] = "Buy"
    elif re.match(r"^(sell|short)\b", normalized):
        prediction["direction"] = "Sell"
    elif re.match(r"^(hold|wait|no trade|no-trade|stand aside)\b", normalized):
        prediction["direction"] = "Wait"
    # If no recognized decision is present, preserve any existing direction.


def _extract_price(text: str, labels: tuple[str, ...]) -> float | None:
    """Extract a price only when it follows an explicit label in the decision text."""
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = rf"\b(?:{label_pattern})\b\s*(?:at\s*)?(?:price\s*)?(?:[:=@]\s*)?([+-]?(?:\d+(?:,\d{{3}})*(?:\.\d+)?|\.\d+))"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        number = float(match.group(1).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _parse_probability(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value if math.isfinite(float(value)) else None
    if isinstance(value, str):
        match = re.search(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%", value.strip())
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return value


def _normalize_prediction(result: Mapping[str, Any]) -> dict[str, Any]:
    prediction = {
        key: _safe_value(result[key])
        for key in PREDICTION_FIELDS
        if key in result
    }

    # Remove placeholder text from fields expected to contain numeric values.
    numeric_fields = (
        "entry", "entry_price", "stop_loss", "sl", "take_profit",
        "take_profit_1", "tp", "target", "probability", "confidence",
        "buy_probability", "sell_probability", "risk_reward", "rr",
    )
    for key in numeric_fields:
        if _is_placeholder(prediction.get(key)):
            prediction[key] = None

    # Keep a canonical timeframe field for the evaluator.
    timeframe = prediction.get("timeframe", prediction.get("chart_timeframe"))
    normalized_timeframe = _normalize_timeframe(timeframe)
    if normalized_timeframe is not None:
        prediction["timeframe"] = normalized_timeframe

    # Interpret a percent string as a numeric percentage when possible.
    for key in ("probability", "confidence", "buy_probability", "sell_probability"):
        if key in prediction:
            prediction[key] = _parse_probability(prediction[key])

    # A combined decision string may contain explicit levels. Extract them only
    # when a labelled value is present; never guess a price from unrelated text.
    decision_parts = [
        prediction.get("decision"),
        prediction.get("final_decision"),
        prediction.get("action"),
        prediction.get("signal"),
    ]
    decision_text = " | ".join(
        item for item in decision_parts if isinstance(item, str) and item.strip()
    )
    if decision_text:
        if prediction.get("entry") is None and prediction.get("entry_price") is None:
            entry = _extract_price(decision_text, ("entry", "entry price"))
            if entry is not None:
                prediction["entry"] = entry
        if prediction.get("stop_loss") is None and prediction.get("sl") is None:
            stop = _extract_price(decision_text, ("stop loss", "stop-loss", "stop", "sl"))
            if stop is not None:
                prediction["stop_loss"] = stop
        if prediction.get("take_profit") is None and prediction.get("tp") is None:
            target = _extract_price(
                decision_text, ("take profit", "take-profit", "take_profit", "target", "tp")
            )
            if target is not None:
                prediction["take_profit"] = target

    _normalize_direction(prediction)

    # Make a missing decision explicit instead of leaving the evaluator to guess.
    if prediction and not _decision_text(prediction):
        prediction["logging_status"] = "decision_missing"

    # A few app responses use alternate field names. Preserve originals while
    # filling canonical aliases only when the canonical field is absent.
    if prediction.get("symbol") is None:
        for key in ("pair", "asset", "market"):
            if prediction.get(key):
                prediction["symbol"] = prediction[key]
                break
    if prediction.get("entry") is None and prediction.get("entry_price") is not None:
        prediction["entry"] = prediction["entry_price"]
    if prediction.get("stop_loss") is None and prediction.get("sl") is not None:
        prediction["stop_loss"] = prediction["sl"]
    if prediction.get("take_profit") is None:
        for key in ("take_profit_1", "tp", "target"):
            if prediction.get(key) is not None:
                prediction["take_profit"] = prediction[key]
                break

    return prediction


def _user_hash(user_email: str) -> str | None:
    """Return a stable pseudonymous identifier without logging the email itself."""
    email = str(user_email or "").strip().lower()
    if not email:
        return None
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:16]


def log_prediction(
    user_email: str,
    plan: str,
    result: Mapping[str, Any],
    meta: Mapping[str, Any] | None = None,
) -> None:
    """Append one prediction record; callers should catch logging errors."""
    if not isinstance(result, Mapping):
        raise TypeError("result must be a mapping")

    prediction = _normalize_prediction(result)

    # Avoid dumping the entire result if its keys do not match our schema.
    # An explicit minimal marker is safer than accidentally logging session data.
    if not prediction:
        prediction = {"logging_status": "no_supported_prediction_fields"}

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "plan": str(plan or "unknown")[:40].lower(),
        "user_id_hash": _user_hash(user_email),
        "prediction": prediction,
    }

    # Optional context from the app: what the AI proposed BEFORE any code gate
    # (pre_gate) and whether symbol/timeframe came from the user's caption.
    # Only a small whitelist is kept; nothing else from the caller is logged.
    if isinstance(meta, Mapping):
        safe_meta = {}
        pre_gate = meta.get("pre_gate")
        if isinstance(pre_gate, Mapping):
            safe_meta["pre_gate"] = {
                key: _safe_value(pre_gate.get(key))
                for key in ("decision", "entry", "stop_loss", "take_profit", "take_profit_1")
                if key in pre_gate
            }
        for key in ("symbol_source", "timeframe_source"):
            if meta.get(key) in ("caption",):
                safe_meta[key] = meta[key]
        if safe_meta:
            record["meta"] = safe_meta

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        record,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
