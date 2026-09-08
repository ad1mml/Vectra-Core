"""
vip_score.py
==============================================================================
VectraCore — VIP Tier — Institutional Score Module
Extends pro_score.py's methodology with context-layer weighting.
"""

VIP_SCORE = """
------------------------------------------------------------------------------
VIP institutional_score METHODOLOGY
------------------------------------------------------------------------------

Apply Pro's institutional_score methodology as the technical foundation:
structural clarity, liquidity/order-flow quality, confluence across
evidence types, invalidation clarity, and reliance on obvious-vs-genuine
levels — weighed exactly as described in pro_score.py.

VIP ADDENDUM — CONTEXT ADJUSTMENT:
After establishing the technical-foundation score, adjust modestly (rarely
by more than 10-15 points in either direction) based on context alignment:
  - Convergence between the technical case and market regime/monetary
    policy/geopolitical context (vip_reasoning.py's layers agreeing)
    modestly supports the score.
  - A pending high-impact, instrument-specific event, or a
    VOLATILE/EVENT-DRIVEN regime classification, modestly caps the score
    even for an otherwise technically clean setup — reflecting genuinely
    higher execution risk in those conditions, not a judgment that the
    technical read itself was wrong.

The technical foundation remains the dominant input — context should
refine the score, not override it. A technically excellent setup with a
technically-neutral news backdrop should still score in the technical
foundation's own high range, not be dragged down for lack of a
context tailwind it never needed.
"""
