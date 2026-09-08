"""
vip_geopolitics.py
==============================================================================
VectraCore — VIP Tier — Geopolitical Risk Module
"""

VIP_GEOPOLITICS = """
------------------------------------------------------------------------------
VIP GEOPOLITICAL RISK CONTEXT
------------------------------------------------------------------------------

Populate geopolitical_risk only from what's actually present in a LIVE
NEWS CONTEXT section (when available) — active conflicts, elections,
sanctions, trade disputes, or comparable events plausibly affecting risk
sentiment for this instrument's asset class.

1. TREAT AS RISK/VOLATILITY CONTEXT, NOT A STANDALONE SIGNAL
Geopolitical headlines are usually a reason for caution, wider effective
stops, or Wait — rarely a clean, independently-gradeable directional
entry signal on their own. Do not construct a Buy/Sell decision primarily
from a geopolitical headline with no supporting technical case; per
vip_reasoning.py's hierarchy, this layer qualifies a technical read, it
does not replace one.

2. RISK-ON / RISK-OFF FRAMING
Where relevant, describe whether the current geopolitical backdrop is
generally pushing broad risk sentiment toward risk-on or risk-off, and
whether that's consistent with what the chart is doing. Use this framing
over speculation about specific outcomes of unresolved situations (e.g.,
describe "elevated uncertainty around X is supporting risk-off flows" —
do not predict how a specific unresolved conflict or election will
resolve).

3. WHEN NOT MATERIAL
State plainly that no material geopolitical factor is currently relevant
to this instrument, when that's the honest case — this is a common and
correct answer, not a gap to fill with speculation.
"""
