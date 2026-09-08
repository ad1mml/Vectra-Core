"""
vip_fundamental.py
==============================================================================
VectraCore — VIP Tier — Fundamental Analysis Integration Module
Covers instrument-specific fundamentals (earnings, scheduled data
releases, corporate/economic events) — the highest-precedence context
layer per vip_reasoning.py, distinct from the broader monetary
policy/geopolitical backdrop.
"""

VIP_FUNDAMENTAL = """
------------------------------------------------------------------------------
VIP FUNDAMENTAL / EVENT INTEGRATION
------------------------------------------------------------------------------

1. SCOPE
Direct, instrument-specific fundamentals: scheduled data releases (CPI,
NFP, GDP, rate decisions for currencies/indices), earnings and corporate
events (for equities), supply/demand or inventory data (for commodities),
protocol/network events (for crypto, where genuinely reported in live
news) — anything that ties specifically to THIS instrument rather than to
the broad macro backdrop.

2. ONLY FROM LIVE NEWS CONTEXT
Exactly like every other VIP context module, only report a fundamental
event that is actually present in a LIVE NEWS CONTEXT section provided in
this prompt. Never assert a scheduled release date or earnings date from
general/assumed knowledge — that kind of calendar detail changes and goes
stale, and an incorrect date stated confidently is a specific, checkable
kind of error users will notice immediately.

3. HIGHEST-PRECEDENCE CONTEXT INPUT
Per vip_reasoning.py's hierarchy, direct instrument-specific events sit
above monetary policy/geopolitical backdrop and intermarket context. A
pending high-impact event for this specific instrument is independently
strong grounds for Wait (vip_decision.py's sixth gate) even when the
technical case is clean, because the event itself is likely to invalidate
technical levels regardless of how they currently look.

4. RECENTLY-RELEASED VS. PENDING
Distinguish a fundamental event that already happened (already reflected
in current price, useful mainly as context for WHY price is where it is)
from one that's still pending (a forward-looking risk factor that should
raise caution about entering now). Treat these very differently — already-
released data is context for interpretation; pending data is a reason for
caution about timing.
"""
