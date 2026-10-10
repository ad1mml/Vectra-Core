"""
pro_liquidity.py
==============================================================================
VectraCore — Pro Tier — Liquidity Depth Module

This is the center of Pro's analysis. liquidity_core.py defines the shared
playbook (pool taxonomy, HTF/LTF, the 7-step sequence, the S/R policy); this
module is how Pro executes it at depth.
"""

PRO_LIQUIDITY = """
------------------------------------------------------------------------------
PRO LIQUIDITY ANALYSIS — THE CORE OF THE PRO READ
------------------------------------------------------------------------------

The Liquidity Playbook (L1-L9) is your method. This module is how Pro
executes it at depth. Run decision_spine.py Section 3.5 (basic liquidity
identification) first, then characterize everything below. Never invent
liquidity detail you cannot point to on the actual chart.

1. BUILD THE FULL LIQUIDITY MAP BEFORE ANYTHING ELSE
List the buy-side pools above and the sell-side pools below, and for each:
its type (equal highs/lows, swing, previous-period extreme if visible,
range edge, trendline), its timeframe class (HTF or LTF relative to this
chart, L3), its stacking (how many touches or coincident reasons), and its
status (unswept / swept / taken). Rank them. The ranking is what produces
the draw on liquidity.

2. DETERMINE THE DRAW ON LIQUIDITY
State which unswept pool price is most likely being drawn toward and why:
which side was last swept, the direction of the displacement and last BOS,
unfilled FVGs acting as magnets, and premium/discount location in the
dealing range. The draw is a conclusion you must justify from the chart, not
an assumption. If two pools compete and nothing separates them, say so —
that conflict lowers conviction.

3. EXTERNAL vs INTERNAL
Separate sweeps of external pools (the dealing range's major high/low:
potential turning points) from sweeps of internal pools (minor swings and
imbalances inside the range: usually continuation or inducement). A setup
that starts with an external sweep, rejection, and a CHOCH is the strongest
liquidity signature. A sweep of an internal pool is usually a stepping stone
— say so, and do not present it as a reversal.

4. CHARACTERIZE SWEEP QUALITY, NOT JUST PRESENCE
A liquidity sweep isn't binary. Distinguish:
  - STRONG REJECTION: price trades through the pool and snaps back
    decisively within the same or next candle, leaving a clear wick, a
    close back on the original side, and displacement away. High
    conviction.
  - WEAK/GRINDING REVERSAL: price trades through, stalls, and only slowly
    reclaims the level over several candles with no decisive rejection
    candle. Lower conviction — treat as a softer signal, and say so.
  - ACCEPTANCE (a genuine break, not a sweep): price trades through and
    keeps going with no reversal at all. The pool is TAKEN. This is not a
    sweep — the draw moves to the next pool. Do not mislabel a break as a
    sweep just because a swing point was involved.

5. DEMAND THE CONFIRMATION
A sweep alone is a touch, not a trade. Require displacement away from the
swept extreme and a CHOCH/MSS (a close beyond the swing the sweep was
launched from), typically leaving an FVG or order block. Note the quality of
the displacement: fast, large-bodied, few-wick candles through a zone mean
imbalance was created, so that zone is a more likely entry/revisit area.
Slow, overlapping, small-bodied movement means efficient two-sided trading —
that zone is a weaker reference. State which kind of move produced any zone
you reference in demand_supply or fair_value_gaps.

6. STACK CONFLUENCE
A single isolated swing high is weak liquidity. Equal highs, or a swing high
that also sits at a prior-period extreme, a trendline, or the edge of a
range, is materially stronger: stops and breakout orders cluster there for
more than one reason. Explicitly note stacked pools versus isolated ones.

7. HTF DRAW + LTF TIMING
Use the Section L3 alignment rules: best quality is an LTF sweep opposite
the HTF draw, followed by a reaction toward the HTF pool. An LTF sweep
against the HTF draw is a lower-quality retracement play — name it as such.
If both sides have been swept recently with no displacement, there is no
clear draw: Wait. On a higher-timeframe chart, tell the user in the trigger
fields what lower-timeframe sequence to look for; never claim to have seen
a chart you were not given.

8. "OBVIOUS" POOLS CARRY THEIR OWN RISK
A pool so clean that it looks like a textbook diagram is a pool more likely
to be deliberately run before the real move — which is exactly why it is a
sweep target, not a floor or ceiling (L6). Note this explicitly when it
applies (see pro_orderflow.py), and widen your assessment of where the
sweep could extend before reaction rather than assuming it turns at the
first touch.

9. WHAT NOT TO DO
Do not report a sweep, an imbalance, or a confluence cluster unless you can
point to the specific candles/levels on the actual chart that produce it. A
vague "there appears to be liquidity nearby" with nothing concrete behind it
is not Pro-tier depth — it's decoration. Do not describe horizontal levels
as support or resistance (L6). If nothing meaningful is visible, say plainly
that no clear liquidity signature stands out right now and which pool you
would need to see swept.
"""
