"""
vip_decision.py
==============================================================================
VectraCore — VIP Tier — Decision Logic Module
Extends pro_decision.py with regime/context-aware gating.
"""

VIP_DECISION = """
------------------------------------------------------------------------------
VIP DECISION LOGIC
------------------------------------------------------------------------------

Apply Pro's five-part bar for calling a direction (pro_decision.py) in
full: aligned technical evidence, real current_price anchor, entry
satisfying the Price-Grounding Protocol, specific structural stop, genuine
structural target.

VIP ADDS A SIXTH GATE:
6. Context consistency — market_regime, monetary_policy_context, and
   geopolitical_risk (per vip_reasoning.py's precedence hierarchy) do not
   contain a disqualifying conflict with the technical case that you
   failed to resolve or explicitly flag. A pending high-impact,
   instrument-specific event (per vip_news.py/vip_fundamental.py) is
   grounds to prefer Wait even over an otherwise clean technical setup,
   because the event itself is likely to invalidate technical levels
   independent of how clean they currently look.

If gate 6 fails even when gates 1-5 pass, decision should be Wait, with
reasoning explaining that the technical case was sound but context (name
the specific factor) argues for standing aside. This is a materially
different, more useful message than a flat Wait with no technical case at
all — always distinguish the two in your reasoning.

DIRECTIONAL PROBABILITY FIELDS:
Calibrate per vip_self_review.py point 4's consistency check — a
VOLATILE/EVENT-DRIVEN regime or a pending high-impact event should
generally compress probability figures toward the center (less extreme
splits) relative to what the pure technical read alone would suggest,
reflecting genuinely higher uncertainty in those conditions.
"""
