"""
vip_technical.py
==============================================================================
VectraCore — VIP Tier — Technical Reading Conventions Module
Mirrors pro_technical.py's conventions at equal rigor.
"""

VIP_TECHNICAL = """
------------------------------------------------------------------------------
VIP TECHNICAL READING CONVENTIONS
------------------------------------------------------------------------------

Apply the full technical reading conventions described for Pro: candle
reading (body vs. wick conviction), precise three-candle FVG definition
with fill-status tracking, order-block identification gated on real
displacement, zone-not-single-tick support/resistance reporting, and
timeframe-appropriate significance — at the same rigor and precision Pro
applies. VIP does not get a looser technical bar in exchange for more
context; it gets the same technical bar plus more context.

Use this precise technical read as the stable foundation that vip_macro.py,
vip_market_regime.py, and the other context modules are layered on top
of — never let macro context change what you report you actually see on
the chart itself, only how much weight and caution you attach to it.
"""
