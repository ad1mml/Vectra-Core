"""
pro_structure.py
==============================================================================
VectraCore — Pro Tier — Market Structure Depth Module
"""

PRO_STRUCTURE = """
------------------------------------------------------------------------------
PRO MARKET STRUCTURE — DEPTH BEYOND DEFAULT
------------------------------------------------------------------------------

Run decision_spine.py Section 3.3 (basic structure) and 3.4 (BOS/CHOCH)
first — everything below is additive, applied to the same single chart.

1. TRACE STRUCTURE ACROSS THE FULL VISIBLE RANGE, NOT JUST THE LAST SWING
Default looks at the most recent relevant swing. Pro looks at how the
current move fits inside everything visible on the chart: is this the
first leg of a new trend, a continuation deep into an established one, or
a move happening at the edge of a range that's held multiple times before?
Position within the visible range changes the read — a breakout attempt at
the edge of a range tested five times carries different weight than one at
the edge of a range tested for the first time.

2. IDENTIFY WHERE IN THE TREND CYCLE PRICE CURRENTLY SITS
Classify the current leg as early (fresh break of structure, room to
run), mid (established direction, structure still intact), or late
(extended move, structure showing early signs of exhaustion — slowing
momentum, shrinking impulse candles, first minor CHOCH against the move).
State this explicitly; it should visibly affect conviction — a late-stage
extended move deserves more caution than a fresh, early one even with
identical candle-pattern optics.

3. DISTINGUISH GENUINE TREND FROM A RANGE ABOUT TO REJECT
A series of higher highs/higher lows that are shrinking in size, with each
new high struggling to clear the last by much, is structurally different
from clean, expanding impulse legs — even though both technically qualify
as "bullish structure" under the basic definition. Call out this
distinction when it's visible; it materially changes setup quality.

4. MULTI-SWING CONFLUENCE
When two or more structural swing points cluster near the same price (a
prior high near a prior low from a different leg, for instance), treat
that cluster as a stronger structural level than either point alone would
be. Note this confluence explicitly in your structure read and let it
inform support_resistance and, if relevant, entry/stop placement — a stop
placed just beyond a confluence zone is more defensible than one placed at
an isolated single swing point.

5. WHAT NOT TO DO
Do not invent a longer-term trend narrative you cannot actually see on
this single image. "Broader context" here means everything genuinely
visible on the chart in front of you, read more thoroughly — not a claim
about weeks/months of price action you were never shown. If the chart only
shows a short window, your structural depth is bounded by that window;
say so rather than speculating about what's off-screen.
"""
