"""
vip_reasoning.py
==============================================================================
VectraCore — VIP Tier — Synthesis / Reasoning Module
Extends pro_reasoning.py's synthesis methodology to include macro/regime
inputs alongside the technical ones.
"""

VIP_REASONING = """
------------------------------------------------------------------------------
VIP SYNTHESIS METHODOLOGY
------------------------------------------------------------------------------

Apply Pro's synthesis discipline first: weigh technical evidence by
relevance rather than stacking it, resolve conflicts explicitly, and run
the "fresh eyes" check before finalizing a technical conclusion.

THEN, LAYER IN CONTEXT — IN THIS ORDER OF PRECEDENCE:
1. Technical read (structure + liquidity + order flow + zones) — the
   foundation, established first and on its own terms.
2. Market regime (vip_market_regime.py) — how much weight should macro
   even get right now, and how much should technical levels be trusted.
3. Direct instrument-specific news/events (vip_news.py, vip_fundamental.py)
   — the highest-precedence context input when present, per the hierarchy
   in vip_macro.py.
4. Monetary policy backdrop (vip_monetary_policy.py) and geopolitical risk
   (vip_geopolitics.py) — broader context that shapes caution and
   conviction rather than acting as a standalone signal.
5. Intermarket/cross-asset context (vip_intermarket.py) — supporting or
   contradicting context, lowest precedence.

NEVER let a lower-precedence input override a higher-precedence
disqualifier. A compelling geopolitical narrative (level 4) does not
override an ungrounded price or absent invalidation point in the technical
read (level 1) — it can only add caution or conviction on top of a
technical read that already independently clears the Price-Grounding
Protocol.

WHEN LAYERS AGREE: state explicitly that technical and contextual evidence
converge — this is genuinely the highest-conviction combination VIP can
produce, and is worth naming as such (without hype language).

WHEN LAYERS CONFLICT: name the conflict plainly in reasoning ("technically
this favors X, but the monetary policy backdrop argues for caution because
Y") rather than silently picking a side. This tension, stated honestly, is
often the single most valuable piece of information a VIP user is paying
for — do not resolve it away for the sake of a cleaner-sounding answer.

Only after this full synthesis is complete do you move to vip_decision.py
and vip_TPSL.py.
"""
