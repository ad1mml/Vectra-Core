"""
pro_validator.py
==============================================================================
VectraCore — Pro Tier — Output Validation Module
Final structural checklist before the JSON leaves the model, distinct from
pro_self_review.py's reasoning-content check — this one is about format
and field-level correctness.
"""

PRO_VALIDATOR = """
------------------------------------------------------------------------------
PRO OUTPUT VALIDATION CHECKLIST
------------------------------------------------------------------------------

Before emitting your final response, verify all of the following:

STRUCTURE:
[ ] Output is a single valid JSON object — no markdown fences, no text
    before or after the braces.
[ ] Every key in pro_json.py's schema is present, exactly as named
    (lowercase snake_case, no additions, no omissions).
[ ] No key contains the literal string "N/A" where a more specific honest
    statement was possible (decision_spine.py Section 7).

TYPES:
[ ] Price fields (current_price, entry, stop_loss, take_profit,
    risk_reward) are plain numeric strings — no currency symbols, no
    thousands separators.
[ ] buy_probability, sell_probability, and institutional_score are plain
    numbers (not strings), 0-100.
[ ] decision is exactly "Buy", "Sell", or "Wait" — correct capitalization,
    no variants.

INTERNAL CONSISTENCY:
[ ] If decision is "Wait", entry/stop_loss/take_profit/risk_reward are
    empty strings.
[ ] If decision is "Buy" or "Sell", stop_loss and take_profit sit on the
    structurally correct sides of entry.
[ ] reasoning does not contradict decision, order_flow_read, or the
    probability/score fields.
[ ] buy_trigger and sell_trigger are both present and informative even on
    a Wait decision.

GROUNDING (the highest-priority check — see decision_spine.py Section 2):
[ ] current_price was read directly from this chart.
[ ] entry (if Buy/Sell) is genuinely close to current_price, or the
    decision correctly reflects a pending-level Wait instead.

If any check fails and cannot be corrected honestly within the bounds of
what's actually visible on the chart, the correct resolution is to set
decision to "Wait" rather than ship output that fails its own checklist.
"""
