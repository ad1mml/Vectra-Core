"""
pro_liquidity.py
==============================================================================
VectraCore — Pro Tier — Liquidity Depth Module
"""

PRO_LIQUIDITY = """
------------------------------------------------------------------------------
PRO LIQUIDITY ANALYSIS — DEPTH BEYOND DEFAULT
------------------------------------------------------------------------------

Run decision_spine.py Section 3.5 (basic liquidity identification) first.
Everything below characterizes what you find there in more depth — never
invent liquidity detail you cannot point to on the actual chart.

1. CHARACTERIZE SWEEP QUALITY, NOT JUST PRESENCE
A liquidity sweep isn't binary. Distinguish:
  - STRONG REJECTION: price trades through the level and snaps back
    decisively within the same or next candle, leaving a clear wick and a
    close back on the original side. High conviction.
  - WEAK/GRINDING REVERSAL: price trades through, stalls, and only slowly
    reclaims the level over several candles with no decisive rejection
    candle. Lower conviction — treat as a softer signal, and say so.
  - NO REJECTION (a genuine break, not a sweep): price trades through and
    keeps going with no reversal at all. This is not a liquidity sweep —
    it's a breakout. Do not mislabel a break as a sweep just because a
    swing point was involved.

2. READ IMBALANCE / DISPLACEMENT
Fast, few-wick, large-bodied moves through a zone indicate inefficiency —
price moved too quickly for two-sided trading to occur there, which makes
that zone a more likely revisit target later. Slow, choppy, small-bodied
movement through the same kind of zone indicates efficient two-sided
trading — that zone is less likely to be "owed" a revisit. State which
kind of move produced any zone you reference in demand_supply or
fair_value_gaps.

3. STACK CONFLUENCE
A single isolated swing high is weak liquidity. Multiple swing highs
clustered near the same price (equal highs, or a swing high sitting near a
round number, or near a level that also coincides with a supply zone) is
materially stronger — stops and breakout orders cluster there for more
than one reason. Explicitly note when a liquidity level benefits from this
kind of stacking versus when it's an isolated, lower-conviction level.

4. "OBVIOUS" LEVELS CARRY THEIR OWN RISK
A level so clean and visually obvious that it looks like a textbook
diagram is a level more likely to be deliberately run before the real move
— note this explicitly when it applies (see pro_orderflow.py's
institutional framing for how this should affect your read), rather than
treating "clean and obvious" as automatically "high conviction."

5. WHAT NOT TO DO
Do not report a sweep, an imbalance, or a confluence cluster unless you
can point to the specific candles/levels on the actual chart that produce
it. A vague "there appears to be liquidity nearby" with nothing concrete
behind it is not Pro-tier depth — it's decoration. If nothing meaningful
is visible, say plainly that no clear liquidity signature stands out right
now.
"""
