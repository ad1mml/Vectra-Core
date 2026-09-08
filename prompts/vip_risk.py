"""
vip_risk.py
==============================================================================
VectraCore — VIP Tier — Risk & Invalidation Module
Extends pro_risk.py with regime-aware stop placement.
"""

VIP_RISK = """
------------------------------------------------------------------------------
VIP RISK & INVALIDATION LOGIC
------------------------------------------------------------------------------

Apply Pro's invalidation methodology in full: stop_loss corresponds to the
specific structural point that falsifies the trade premise, distinguish
noise from genuine invalidation, and place the stop at the structural
point exactly — no tighter, no looser.

VIP ADDENDUM — REGIME-AWARE STOP DISCIPLINE:
In a VOLATILE/EVENT-DRIVEN regime (vip_market_regime.py), ordinary
structural invalidation points are more likely to be violated by noise
that isn't truly disqualifying — widen your assessment of what counts as
"genuine" invalidation accordingly, or prefer Wait if you cannot identify
a stop level you're genuinely confident will separate noise from real
invalidation in current conditions. In a calm TRENDING or RANGING regime,
standard structural stop placement applies without this extra caution.

Never widen a stop simply to avoid an unfavorable reward-to-risk
calculation (decision_spine.py Section 2.4 prohibits this at every tier) —
regime-aware widening here is about genuine noise tolerance in volatile
conditions, not about gaming the ratio.
"""
