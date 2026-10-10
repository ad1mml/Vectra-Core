"""
trade_validation.py
==============================================================================
VectraCore - deterministic trade-geometry helpers (no Flask, no network).

app.py imports this file. Everything here is plain Python so it can be unit
tested without the rest of the app.

WHAT IT DOES
  * parses prices
  * computes risk / reward / R:R in a direction-aware way (Buy vs Sell)
  * classifies an entry as "market" (near current price) or "pending"
  * labels R:R quality (below minimum / acceptable / preferred)
  * records every validation change with a structured reason code

WHAT IT NEVER DOES
  * it never moves a stop-loss or take-profit to improve R:R
  * it never invents a price

CONFIGURATION (all optional, set in .env; defaults shown)
  MIN_ACCEPTABLE_RR=1.0             hard floor. Below this a Buy/Sell becomes Wait.
  PREFERRED_RR=1.5                  soft target. Below this the trade is still
                                    allowed but labelled "acceptable", not "preferred".
  MAX_MARKET_ENTRY_DISTANCE_PCT=0.25  a Buy/Sell whose entry is further than this
                                    (percent of current_price) from current_price
                                    is treated as a PENDING setup, not a market call.
  RR_SUSPICIOUSLY_HIGH=6.0          R:R above this adds a warning ("check that the
                                    target is a real level"). Never blocks.

These defaults are starting hypotheses, not proven optimal values. Tune them
using the benchmark results, not by feel.
"""

import os
import re


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


MIN_ACCEPTABLE_RR = _env_float("MIN_ACCEPTABLE_RR", 1.0)
PREFERRED_RR = _env_float("PREFERRED_RR", 1.5)
MAX_MARKET_ENTRY_DISTANCE_PCT = _env_float("MAX_MARKET_ENTRY_DISTANCE_PCT", 0.25)
RR_SUSPICIOUSLY_HIGH = _env_float("RR_SUSPICIOUSLY_HIGH", 6.0)

# Structured reason codes (stable strings - safe to log, count and chart).
CODE_UNPARSEABLE = "LEVELS_UNPARSEABLE"
CODE_ZERO_RISK = "ZERO_RISK"
CODE_STOP_WRONG_SIDE = "STOP_WRONG_SIDE"
CODE_TARGET_WRONG_SIDE = "TARGET_WRONG_SIDE"
CODE_RR_BELOW_MIN = "RR_BELOW_MIN"
CODE_PRICE_FAR_FROM_LIVE = "PRICE_FAR_FROM_LIVE"
CODE_ENTRY_FAR_PENDING = "ENTRY_FAR_FROM_PRICE_PENDING"
CODE_CURRENT_PRICE_MISSING = "CURRENT_PRICE_MISSING"
CODE_RR_BELOW_PREFERRED = "RR_BELOW_PREFERRED"
CODE_RR_HIGH_CHECK_TARGET = "RR_UNUSUALLY_HIGH"

_PENDING_KEYS = ("order_type", "entry_type", "execution_type")
_PENDING_WORDS = ("pending", "limit", "stop order", "buy stop", "sell stop")


def parse_price(val):
    """Best-effort parse of '1.2450', '1,245.0', '$1.2450', 12, 1.2 -> float,
    or None if there is no usable number."""
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = re.sub(r"[^0-9.\-]", "", str(val).strip())
    if s in ("", "-", ".", "-."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def trade_geometry(decision, entry, stop_loss, take_profit):
    """Direction-aware geometry check.

    Buy : risk = entry - stop,  reward = take_profit - entry
    Sell: risk = stop - entry,  reward = entry - take_profit

    Returns a dict:
      ok      True only when risk > 0 and reward > 0
      code    None when ok, otherwise one of the CODE_* strings
      risk, reward, rr   floats (or None when not computable)
    """
    side = str(decision or "").strip().lower()
    e, sl, tp = parse_price(entry), parse_price(stop_loss), parse_price(take_profit)
    out = {"ok": False, "code": None, "risk": None, "reward": None, "rr": None}

    if side not in ("buy", "sell") or e is None or sl is None or tp is None:
        out["code"] = CODE_UNPARSEABLE
        return out

    risk = (e - sl) if side == "buy" else (sl - e)
    reward = (tp - e) if side == "buy" else (e - tp)
    out["risk"], out["reward"] = risk, reward

    # Tiny tolerance so float noise does not turn "equal" into "wrong side".
    eps = 1e-12 * max(1.0, abs(e))
    if abs(e - sl) <= eps:
        out["code"] = CODE_ZERO_RISK
        return out
    if risk <= 0:
        out["code"] = CODE_STOP_WRONG_SIDE
        return out
    if reward <= 0:
        out["code"] = CODE_TARGET_WRONG_SIDE
        return out

    out["ok"] = True
    out["rr"] = reward / risk
    return out


def entry_distance_pct(entry, current_price):
    """Distance between entry and current price as a percent of current price,
    or None if either is missing / current price is not positive."""
    e, cp = parse_price(entry), parse_price(current_price)
    if e is None or cp is None or cp <= 0:
        return None
    return abs(e - cp) / cp * 100.0


def declared_pending(result):
    """True if the model itself labelled the entry as a pending/limit order
    (only possible when a tier's schema has such a field)."""
    if not isinstance(result, dict):
        return False
    for key in _PENDING_KEYS:
        val = str(result.get(key, "") or "").strip().lower()
        if val and any(w in val for w in _PENDING_WORDS):
            return True
    return False


def classify_entry(result, max_pct=None):
    """'market' | 'pending' | 'unknown' for a Buy/Sell result dict."""
    if max_pct is None:
        max_pct = MAX_MARKET_ENTRY_DISTANCE_PCT
    if declared_pending(result):
        return "pending"
    dist = entry_distance_pct(result.get("entry"), result.get("current_price"))
    if dist is None:
        return "unknown"
    return "pending" if dist > max_pct else "market"


def rr_quality(rr, minimum=None, preferred=None):
    """'below_min' | 'acceptable' | 'preferred' (None if rr is None)."""
    if rr is None:
        return None
    minimum = MIN_ACCEPTABLE_RR if minimum is None else minimum
    preferred = PREFERRED_RR if preferred is None else preferred
    if rr < minimum - 1e-9:
        return "below_min"
    if rr < preferred - 1e-9:
        return "acceptable"
    return "preferred"


def record_validation(result, status, code=None, detail=None, original=None, warning=False):
    """Append a structured entry to result['validation'].

    Layout (only non-empty values are stored, because app.py later replaces
    empty strings with 'Not available' text):
      validation = {
        "status": "passed" | "changed",
        "changes":  [ {"code": ..., "detail": ...}, ... ],   # decision/price changes
        "warnings": [ {"code": ..., "detail": ...}, ... ],   # informational only
        "original": {"decision","entry","stop_loss","take_profit"}  # what the model said
      }
    """
    if not isinstance(result, dict):
        return result
    v = result.get("validation")
    if not isinstance(v, dict):
        v = {"status": "passed", "changes": [], "warnings": []}
        result["validation"] = v
    v.setdefault("changes", [])
    v.setdefault("warnings", [])
    if code:
        item = {"code": code}
        if detail:
            item["detail"] = str(detail)
        (v["warnings"] if warning else v["changes"]).append(item)
    if status == "changed":
        v["status"] = "changed"
    if original:
        clean = {k: str(val) for k, val in original.items() if val not in (None, "")}
        if clean and "original" not in v:
            v["original"] = clean
    return result
