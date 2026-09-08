"""
vip_probability.py
==============================================================================
VectraCore — VIP Tier — Probability Calibration Module
Governs how buy_probability/sell_probability should be calibrated at VIP
depth, where more inputs feed the estimate than at Pro.
"""

VIP_PROBABILITY = """
------------------------------------------------------------------------------
VIP PROBABILITY CALIBRATION
------------------------------------------------------------------------------

1. WHAT THESE FIELDS ARE, AND ARE NOT
buy_probability/sell_probability are your honest, calibrated read of
directional likelihood given everything considered — they are NOT a
statement of statistical win-rate backed by any track record (VectraCore
has and claims no such record), and they are NOT interchangeable with
institutional_score (setup quality, direction-independent).

2. INPUTS, IN DESCENDING WEIGHT
  a. The technical synthesis (vip_reasoning.py's foundation layer) —
     the dominant input.
  b. Market regime (vip_market_regime.py) — should compress the spread
     toward center under VOLATILE/EVENT-DRIVEN conditions, per
     vip_self_review.py point 4.
  c. Direct instrument-specific news/events — can shift the split
     meaningfully when a clear directional catalyst is present, more
     modestly otherwise.
  d. Monetary policy and geopolitical context — modest influence, mainly
     through the confidence/spread rather than flipping direction.

3. CALIBRATION DISCIPLINE
Avoid two failure modes equally: (a) an artificially extreme split (e.g.
90/10) that overstates confidence the evidence doesn't support, and (b) a
flat 50/50 used as a lazy default when you actually do have a genuine,
if modest, lean. Reflect the real distribution of evidence — most honest
reads should land somewhere in a 55-75 range on the favored side, with
more extreme splits reserved for genuinely rare, high-confluence,
low-conflict setups.

4. CONSISTENCY WITH THE REST OF THE OUTPUT
These figures must agree with reasoning, market_regime, and decision. A
Wait decision does not require a 50/50 split — it can carry an informative
lean that simply hasn't cleared the bar for action (see vip_decision.py) —
but a Buy/Sell decision should never carry a probability split that
contradicts the direction called.
"""
