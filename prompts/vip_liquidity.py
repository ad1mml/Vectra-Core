"""
vip_liquidity.py
==============================================================================
VectraCore — VIP Tier — Liquidity Depth Module
Mirrors pro_liquidity.py's methodology at equal rigor, with a
news-sensitivity addendum specific to VIP.
"""

VIP_LIQUIDITY = """
------------------------------------------------------------------------------
VIP LIQUIDITY ANALYSIS
------------------------------------------------------------------------------

Apply the full liquidity methodology described for Pro: characterize sweep
quality (strong rejection vs. weak/grinding vs. no rejection), read
imbalance/displacement, stack confluence, and flag "obvious" levels — at
the same rigor Pro applies.

VIP ADDENDUM — EVENT-RISK SENSITIVITY:
When a LIVE NEWS CONTEXT section shows a pending or very recent
high-impact event for this instrument, treat any liquidity sweep observed
near that event window with extra caution — sweeps around scheduled
releases or breaking news are more likely to be event-driven volatility
than genuine structural liquidity behavior, and are more likely to be
followed by continuation through the level rather than the clean rejection
a "normal" sweep would suggest. Note this explicitly when it applies
rather than treating all sweeps as equivalent regardless of news
proximity.
"""
