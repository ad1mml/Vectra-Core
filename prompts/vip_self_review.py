"""
vip_self_review.py
==============================================================================
VectraCore — VIP Tier — Mandatory Adversarial Self-Review Module
The heavier, mandatory counterpart to pro_self_review.py's lightweight
mechanical check. This is a genuine second pass on the CONCLUSION, not
just a formatting check.
"""

VIP_SELF_REVIEW = """
------------------------------------------------------------------------------
VIP MANDATORY SELF-REVIEW PASS
------------------------------------------------------------------------------

Before producing final JSON, run this adversarial pass on your own draft
conclusion. This is mandatory for every chart-mode VIP response, not an
optional step for when something feels uncertain.

1. STEELMAN THE OPPOSITE CASE
What is the strongest argument AGAINST the decision you're about to make?
Would a skeptical senior colleague reviewing this exact chart and this
exact reasoning push back, and on what specific point? If you cannot
construct a genuine counter-argument at all, that itself is worth a
moment's suspicion — most real setups have at least one legitimate
weakness worth naming.

2. CHECK FOR FORCED DECISIVENESS
Are you calling a direction because the evidence genuinely supports one,
or because a tier that's "supposed" to be sophisticated felt like it
needed a confident-sounding answer? If the honest answer leans toward the
latter, correct toward Wait.

3. RE-VERIFY THE PRICE-GROUNDING PROTOCOL, EXPLICITLY, AGAIN
This is the single most important check in this pass. After all the
additional macro/regime/geopolitical reasoning performed in vip_reasoning.py,
re-confirm: does current_price still reflect what you actually read off
the chart, and does entry still sit close to it for a market call? Extra
reasoning steps are exactly the condition under which a price can quietly
drift from its anchor — check this explicitly rather than assuming earlier
work was still intact by the time you reached this point.

4. CHECK REGIME/PROBABILITY CONSISTENCY
Does market_regime (vip_market_regime.py) logically support the confidence
level implied by buy_probability/sell_probability and institutional_score?
A VOLATILE/EVENT-DRIVEN regime classification sitting next to a very high,
unhedged probability figure is an internal contradiction — resolve it by
adjusting the probability down or the regime language, whichever is
actually true, not by leaving the mismatch in place.

5. CHECK THAT CONTEXT LAYERS WERE ACTUALLY WEIGHED, NOT JUST MENTIONED
Skim your own draft monetary_policy_context and geopolitical_risk fields:
do they actually inform the decision/reasoning, or are they present but
disconnected filler? If disconnected, either genuinely integrate them or
honestly state they're currently neutral/non-material for this call —
don't leave decorative context that does no analytical work.

RECORD THE OUTCOME:
Write a brief, honest summary of what this pass surfaced into
vip_self_review (the schema field) — even when the answer is "reviewed,
no material change." A pass that always concludes "everything checks out"
with identical phrasing every time is a sign this step is being performed
mechanically rather than genuinely — vary your language naturally based on
what was actually found each time.
"""
