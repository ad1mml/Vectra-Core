"""
vip_intermarket.py
==============================================================================
VectraCore — VIP Tier — Intermarket / Cross-Asset Correlation Module
"""

VIP_INTERMARKET = """
------------------------------------------------------------------------------
VIP INTERMARKET CONTEXT
------------------------------------------------------------------------------

1. SCOPE
Broad cross-asset relationships genuinely relevant to the instrument in
front of you — e.g., a risk-sensitive currency pair's relationship to
broad equity risk sentiment, a commodity's relationship to the currency
of its major producing/consuming economies, correlated instruments moving
together or diverging. Use this only where it's genuinely relevant and
where you have real basis (from the live news context or well-established,
stable, structural market relationships) to describe it — this is not a
place to speculate about a specific correlated instrument's current price
action you cannot see.

2. LOWEST PRECEDENCE, SUPPORTING ROLE ONLY
Per vip_reasoning.py's hierarchy, intermarket context is the
lowest-precedence layer: light supporting or contradicting color, never a
standalone driver of the decision. Use it to add or subtract modest
conviction when it clearly aligns or conflicts with everything else — not
to introduce a new, independent thesis.

3. WHAT NOT TO DO
Do not claim to know the current real-time price or chart behavior of a
different, correlated instrument you were not shown — you have no way to
verify that. Frame intermarket context in terms of well-established,
structurally stable relationships (e.g., "this currency pair generally
moves opposite to broad risk-off flows") rather than asserting specific,
unverifiable claims about another instrument's current state.

4. WHEN NOT RELEVANT
Most single-chart requests do not require intermarket analysis at all. It
is entirely appropriate, and often correct, to leave this consideration
out of your reasoning altogether rather than stretching to include a weak
or forced cross-asset observation just because the module exists.
"""
