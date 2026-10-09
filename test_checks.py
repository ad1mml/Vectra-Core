from app import _sanity_check_levels

facts = {"1day": {"price": 1.1194, "atr": 0.0057,
                  "trend": "bearish (lower highs, lower lows)"}}

cases = {
    "good buy (expect Buy + daily-trend warning)":
        {"decision": "Buy", "entry": "1.1190", "stop_loss": "1.1150", "take_profit": "1.1290"},
    "wrong sides (expect Wait)":
        {"decision": "Buy", "entry": "1.1190", "stop_loss": "1.1250", "take_profit": "1.1290"},
    "far from live price (expect Wait)":
        {"decision": "Sell", "entry": "1.1914", "stop_loss": "1.1950", "take_profit": "1.1800"},
}

for name, trade in cases.items():
    out = _sanity_check_levels(dict(trade), facts)
    print(name, "->", out["decision"], "|", out.get("context_warning", ""))
