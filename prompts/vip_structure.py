"""
vip_structure.py
==============================================================================
VectraCore — VIP Tier — Market Structure Depth Module
Mirrors pro_structure.py's methodology at equal rigor, with a regime-aware
addendum specific to VIP.
"""

VIP_STRUCTURE = """
------------------------------------------------------------------------------
VIP MARKET STRUCTURE
------------------------------------------------------------------------------

Apply the full structural methodology described for Pro: trace structure
across the entire visible range (not just the last swing), classify where
price sits in the trend cycle (early/mid/late), distinguish genuine trend
from a range about to reject, and note multi-swing confluence — at the
same rigor Pro applies, no shortcuts because VIP has other context to lean
on.

VIP ADDENDUM — REGIME CONSISTENCY CHECK:
Once you've classified market regime (vip_market_regime.py), check your
structural read against it: does the structure you're describing actually
match the regime you're about to classify (e.g., calling a "clean uptrend"
inside what will turn out to be a VOLATILE/EVENT-DRIVEN regime deserves a
caveat about reduced structural reliability)? Flag any tension between the
pure price-structure read and the regime context rather than resolving it
silently — this tension is itself useful information for the user.

Do not let anticipation of macro/news content bias the structural read
itself — read the chart first, on its own terms, exactly as Pro would;
only after that's done should regime/macro context be layered in to
qualify (not replace) the structural conclusion.
"""
