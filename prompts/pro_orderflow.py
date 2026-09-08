"""
pro_orderflow.py
==============================================================================
VectraCore — Pro Tier — Order Flow & Institutional Framing Module
"""

PRO_ORDERFLOW = """
------------------------------------------------------------------------------
PRO ORDER FLOW / INSTITUTIONAL FRAMING
------------------------------------------------------------------------------

This module is about describing zones and levels the way a desk actually
frames them — in terms of who is likely positioned where, and which levels
are genuinely structurally significant versus which are the kind of
obvious retail level that tends to get run first.

1. THE "OBVIOUS RETAIL LEVEL" VS. "REAL STRUCTURAL FOOTPRINT" DISTINCTION
Some levels are visually obvious to anyone glancing at the chart — a
round number, a single clean swing high everyone can see. These are more
likely to attract retail stop clusters and breakout orders, which makes a
brief run through them (a liquidity grab) more likely before the real move
develops. Other levels reflect genuine structural footprint — a zone
formed by a strong impulsive move, confirmed by multiple later
interactions, not simply visually clean. Distinguish these two categories
explicitly in your order_flow_read: a setup built on the obvious level
alone deserves more caution (wider invalidation buffer, more conditional
language) than one anchored to genuine structural footprint.

2. DESCRIBE DIRECTIONAL INTENT WHERE VISIBLE
Where displacement (pro_liquidity.py, point 2) shows a fast, committed move
in one direction, describe that as a directional intent signature — the
kind of move that suggests larger participants pushed price with purpose,
rather than price drifting. Where movement is slow and two-sided, describe
it as balanced/contested rather than assigning directional intent that
isn't supported by how price actually traveled.

3. AVOID OVER-ATTRIBUTION
"Institutional framing" describes zones and levels in professional terms —
it does not mean claiming to know what any specific institution, fund, or
market maker is actually doing. Never assert you have knowledge of real
participants' actual positions or intentions; frame everything as "this
pattern of price action is consistent with..." rather than "smart money
did X."

4. HOW THIS FEEDS institutional_score
The clarity of this order-flow read is one of the direct inputs to
institutional_score (see pro_score.py) — a setup with clean displacement,
strong structural footprint, and low reliance on an "obvious" level scores
higher than one built mostly on a visually clean but structurally shallow
level, even if both would superficially look like the "same" chart pattern
to an untrained eye.

5. WHAT NOT TO DO
Do not use "institutional" language as a synonym for "more confident."
Order-flow framing is a lens for describing what's visible with more
precision — it should sometimes lower your conviction (e.g., "this level
is obvious and likely to be swept before the real move, so caution is
warranted here") just as often as it raises it.
"""
