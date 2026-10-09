"""
market_facts.py - turns raw candles into a short "verified facts" text block
for the AI prompt. No AI, no network: pure maths on candle data.

Accepts candles oldest-first in EITHER format:
    Twelve Data: {"open": "1.10", "high": "1.12", "low": "1.09", "close": "1.11", ...}
    Short form : {"o": 1.10, "h": 1.12, "l": 1.09, "c": 1.11}
"""


def normalize(candles):
    """Convert any supported candle format to {"o","h","l","c"} floats.
    Bad/incomplete candles are skipped instead of crashing."""
    out = []
    for c in candles or []:
        try:
            out.append({
                "o": float(c.get("o", c.get("open"))),
                "h": float(c.get("h", c.get("high"))),
                "l": float(c.get("l", c.get("low"))),
                "c": float(c.get("c", c.get("close"))),
            })
        except (TypeError, ValueError):
            continue
    return out


def atr(candles, period=14):
    """Average True Range = typical candle size. Used to judge SL distance."""
    if len(candles) < 2:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["h"], candles[i]["l"], candles[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    trs = trs[-period:]
    return sum(trs) / len(trs)


def swings(candles, left=3, right=3):
    """Swing highs/lows: a candle higher (or lower) than `left` candles
    before it and `right` candles after it."""
    highs, lows = [], []
    for i in range(left, len(candles) - right):
        h, l = candles[i]["h"], candles[i]["l"]
        if all(h > candles[j]["h"] for j in range(i - left, i)) and \
           all(h >= candles[j]["h"] for j in range(i + 1, i + right + 1)):
            highs.append((i, h))
        if all(l < candles[j]["l"] for j in range(i - left, i)) and \
           all(l <= candles[j]["l"] for j in range(i + 1, i + right + 1)):
            lows.append((i, l))
    return highs, lows


def trend(highs, lows):
    """Bullish = higher highs + higher lows. Bearish = lower both."""
    if len(highs) < 2 or len(lows) < 2:
        return "unclear"
    hh = highs[-1][1] > highs[-2][1]
    hl = lows[-1][1] > lows[-2][1]
    if hh and hl:
        return "bullish (higher highs, higher lows)"
    if not hh and not hl:
        return "bearish (lower highs, lower lows)"
    return "ranging/mixed"


def analyze(candles, timeframe):
    """Facts for ONE timeframe."""
    candles = normalize(candles)
    if len(candles) < 20:
        return None
    highs, lows = swings(candles)
    price = candles[-1]["c"]
    range_hi = max(c["h"] for c in candles[-100:])
    range_lo = min(c["l"] for c in candles[-100:])
    span = (range_hi - range_lo) or 1e-9
    pos = (price - range_lo) / span  # 0 = bottom of range, 1 = top
    zone = "premium (upper half)" if pos > 0.55 else \
           "discount (lower half)" if pos < 0.45 else "equilibrium (middle)"
    return {
        "tf": timeframe,
        "price": price,
        "atr": atr(candles),
        "trend": trend(highs, lows),
        "last_swing_high": highs[-1][1] if highs else None,
        "last_swing_low": lows[-1][1] if lows else None,
        "range_high": range_hi,
        "range_low": range_lo,
        "zone": zone,
    }


def facts_block(per_tf, symbol=""):
    """per_tf = {"1h": candles, "4h": candles, "1day": candles}
    Returns text to paste into the AI prompt, or "" if no data."""
    lines = [f"VERIFIED MARKET FACTS {symbol} (computed from real candles, "
             "not estimated from the image):"]
    found = False
    for tf, candles in per_tf.items():
        f = analyze(candles, tf)
        if not f:
            continue
        found = True
        lines.append(
            f"[{tf}] price={f['price']:.5g} | trend: {f['trend']} | "
            f"ATR={f['atr']:.5g} | swing high={f['last_swing_high']} | "
            f"swing low={f['last_swing_low']} | range {f['range_low']:.5g}-"
            f"{f['range_high']:.5g} | price is in {f['zone']}"
        )
    if not found:
        return ""
    lines.append(
        "How to use these facts: swing highs/lows, ATR, trend and zone are "
        "computed from real candles, so prefer them for levels and context. "
        "If the uploaded chart's current price clearly differs, trust the "
        "chart image for current price and mention the difference. "
        "Keep SL at least 1x ATR (of the chart's timeframe) from entry. "
        "If the higher-timeframe trend opposes the trade, say so explicitly "
        "and lower your confidence accordingly.")
    return "\n".join(lines)


if __name__ == "__main__":
    import math
    fake = []
    for i in range(150):
        mid = 1.10 + 0.0005 * i + 0.004 * math.sin(i / 5)
        fake.append({"o": mid, "h": mid + 0.0015, "l": mid - 0.0015, "c": mid + 0.0003})
    print(facts_block({"1h": fake}, "EUR/USD"))
    td = [{"datetime": "x", "open": str(c["o"]), "high": str(c["h"]), "low": str(c["l"]), "close": str(c["c"])} for c in fake]
    print(facts_block({"4h": td, "1day": td[:5]}, "TD-format test"))
