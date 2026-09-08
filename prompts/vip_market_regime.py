"""
vip_market_regime.py
==============================================================================
VectraCore — VIP Tier — Market Regime Classification Module
"""

VIP_MARKET_REGIME = """
------------------------------------------------------------------------------
VIP MARKET REGIME CLASSIFICATION
------------------------------------------------------------------------------

Classify the current regime the instrument appears to be trading in, using
both the chart itself and any available live news context. This is the
one macro-layer module that can be meaningfully assessed from price action
alone (vip_macro.py point 2), even without a live news section present.

THE FOUR REGIMES:

1. TRENDING — clear directional structure, momentum broadly one-sided,
   pullbacks shallow and orderly relative to the trend leg.

2. RANGING / CONSOLIDATING — price oscillating between defined bounds, no
   sustained directional edge, repeated rejections at both range
   boundaries.

3. VOLATILE / EVENT-DRIVEN — choppy, wide-range action inconsistent with
   clean technical flow. Strong supporting signal: live news context shows
   a high-impact event recently released or imminent for this instrument.
   Technical levels are less reliable in this regime — treat this
   classification as a direct input to caution across vip_risk.py,
   vip_probability.py, and vip_score.py.

4. TRANSITIONAL — early evidence one regime is giving way to another (a
   long-standing range finally breaking with real displacement, or a
   clean trend losing momentum into visible chop).

CLASSIFICATION METHOD:
State which regime is active and the specific evidence for it (both
price-based and, when available, news-based) in one or two sentences. Do
not classify by vibe — point to what you're actually seeing: pullback
depth and orderliness for TRENDING, boundary-respect count for
RANGING, candle range/wick chaos and any coincident high-impact news for
VOLATILE/EVENT-DRIVEN, or the specific structural break/momentum shift for
TRANSITIONAL.

DOWNSTREAM EFFECT — MANDATORY, NOT OPTIONAL:
The regime classification must visibly influence at least one of:
stop-placement caution (vip_risk.py), probability spread compression
(vip_probability.py), or institutional_score (vip_score.py). A regime
field that's populated but doesn't change anything else in the output is
decoration, not analysis — vip_self_review.py point 4 checks specifically
for this.
"""
