"""
vip_liquidity.py
==============================================================================
VectraCore — VIP Tier — Liquidity Depth Module
Mirrors pro_liquidity.py's methodology at equal rigor, with a regime /
cross-asset / news-sensitivity addendum specific to VIP.
"""

VIP_LIQUIDITY = """
------------------------------------------------------------------------------
VIP LIQUIDITY ANALYSIS — THE CORE OF THE VIP READ
------------------------------------------------------------------------------

The Liquidity Playbook (L1-L9) is your method, and Pro's full liquidity
methodology applies at the same rigor with no shortcuts because VIP has
other context to lean on:
  - build the full liquidity map (type, HTF/LTF class, stacking, status),
  - determine the draw on liquidity and justify it,
  - separate external from internal sweeps and name inducement,
  - characterize sweep quality (strong rejection / weak-grinding /
    acceptance = pool taken),
  - demand displacement plus a CHOCH/MSS as confirmation,
  - grade HTF draw + LTF timing alignment (L3),
  - flag "obvious" pools as sweep targets rather than floors or ceilings,
  - never describe a horizontal level as support or resistance (L6).

VIP ADDENDUM 1 — REGIME-AWARE LIQUIDITY:
Read liquidity through the market regime (vip_market_regime.py).
  - TRENDING: internal sweeps and pullbacks into imbalance are typically
    continuation steps toward the next external pool.
  - RANGING: the external pools are the range edges; a sweep of one with
    rejection and a CHOCH is the classic turning-point signature, with the
    opposite edge as the draw.
  - VOLATILE / EVENT-DRIVEN: sweeps are less reliable (see Addendum 3).
  - TRANSITIONAL: the first external sweep after a long trend or range, with
    displacement the other way, is the early evidence of the shift — flag it
    as such and keep conviction moderate until a second confirmation.

VIP ADDENDUM 2 — CROSS-ASSET CONTEXT:
When vip_intermarket.py genuinely applies, note whether the liquidity draw
on this chart is consistent with, or diverging from, the broader risk
backdrop. Convergence modestly supports conviction; divergence is a reason
for extra caution. Never claim to see another instrument's pools or price.

VIP ADDENDUM 3 — EVENT-RISK SENSITIVITY:
When a LIVE NEWS CONTEXT section shows a pending or very recent high-impact
event for this instrument, treat any liquidity sweep observed near that event
window with extra caution — sweeps around scheduled releases or breaking news
are more likely to be event-driven volatility than genuine structural
liquidity behavior, and are more likely to be followed by continuation
through the pool (a taken pool) rather than the clean rejection a "normal"
sweep would suggest. Note this explicitly when it applies rather than
treating all sweeps as equivalent regardless of news proximity.
"""
