"""
vip_validator.py
==============================================================================
VectraCore — VIP Tier — Output Validation Module
Extends pro_validator.py's checklist for VIP's larger schema and ladder.
"""

VIP_VALIDATOR = """
------------------------------------------------------------------------------
VIP OUTPUT VALIDATION CHECKLIST
------------------------------------------------------------------------------

Run Pro's full checklist first (structure, types, internal consistency,
grounding — pro_validator.py) against VIP's schema (vip_json.py). Then
verify the following VIP-specific additions:

CONTEXT FIELDS:
[ ] market_regime is populated with a real classification and brief
    justification, not left as a generic placeholder.
[ ] monetary_policy_context and geopolitical_risk each contain either a
    genuine read or an honest "not currently material" statement — never
    an empty string with no explanation when the user might reasonably
    wonder why.

LADDER:
[ ] If decision is "Wait", take_profit_1/2/3 are all empty strings.
[ ] If decision is "Buy" or "Sell", take_profit_1 is populated and
    structurally valid; take_profit_2/3 are either validly populated (each
    further from entry than the previous rung, correct side) or correctly
    left empty — never partially invented to fill gaps.
[ ] risk_reward is computed against take_profit_1 only.

SELF-REVIEW:
[ ] vip_self_review is populated with a genuine, non-boilerplate summary
    of the adversarial pass (vip_self_review.py) — not a generic
    "everything looks fine" repeated verbatim across responses.

FINAL GATE:
[ ] The self-review pass (vip_self_review.py) was actually performed
    before this checklist, not skipped. If in doubt, perform it now before
    finalizing.

As with every tier, any check that fails and cannot be corrected honestly
resolves to "decision": "Wait" rather than shipping non-compliant output.
"""
