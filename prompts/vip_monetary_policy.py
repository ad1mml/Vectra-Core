"""
vip_monetary_policy.py
==============================================================================
VectraCore — VIP Tier — Monetary Policy Context Module
"""

VIP_MONETARY_POLICY = """
------------------------------------------------------------------------------
VIP MONETARY POLICY CONTEXT
------------------------------------------------------------------------------

Populate monetary_policy_context only from what's actually present in a
LIVE NEWS CONTEXT section (when available) — never from general/assumed
knowledge of "current" central bank stances, since that knowledge may be
stale relative to the actual present moment.

1. WHAT TO ASSESS
The broad policy direction (easing/tightening/holding) of the central
bank(s) most relevant to this instrument's underlying currency or asset
class, based on the live news provided, and whether current price action
on the chart appears consistent with or fighting that backdrop.

2. HOW TO USE IT
Per vip_reasoning.py's precedence hierarchy, this is context that modestly
shifts caution/conviction — a technical setup running WITH the prevailing
policy backdrop deserves a small conviction bump; one fighting it deserves
a small caution increase. State this explicitly rather than silently
folding it into the probability figures with no explanation.

3. WHEN UNAVAILABLE OR NOT CLEARLY RELEVANT
State plainly that monetary policy context isn't available (no live news
this request) or isn't clearly relevant to this specific instrument right
now (e.g., a commodity or equity chart where no central bank event is a
close driver) — either is an honest, complete answer. Do not force a
central-bank narrative onto an instrument where it doesn't meaningfully
apply.
"""
