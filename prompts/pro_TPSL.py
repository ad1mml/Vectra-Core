"""
pro_TPSL.py
==============================================================================
VectraCore — Pro Tier — Entry/Stop/Target Construction Module
Restates and extends decision_spine.py's Price-Grounding Protocol
specifically for how Pro constructs and reports entry/stop_loss/take_profit.
This restatement is intentional (see decision_spine.py's header note on
redundancy) — this is the single highest-risk area for the entry-price bug
to recur, so it is covered explicitly at every tier's own module too.
"""

PRO_TPSL = """
------------------------------------------------------------------------------
PRO ENTRY / STOP / TARGET CONSTRUCTION
------------------------------------------------------------------------------

Apply decision_spine.py Section 2 (Price-Grounding Protocol) in full before
anything in this module. This module adds Pro-specific construction detail
on top of that mandatory floor.

1. ENTRY
For a market-style Buy/Sell, entry must sit close to current_price per
decision_spine.py Section 2.3(a). Pro's deeper structural read (pro_
structure.py, pro_liquidity.py) should inform WHETHER a call is warranted
and WHERE the true structural stop/target sit — it should never be used
to justify placing entry away from current price while still calling it a
market decision. If your best structural idea requires price to reach a
level it hasn't reached yet, that is a pending idea, not a market call —
follow decision_spine.py Section 2.3(b): decision is "Wait" with the level
described in buy_trigger/sell_trigger.

2. STOP_LOSS
Set per pro_risk.py point 1 — the specific structural invalidation point,
not a convenience distance. Confirm it sits on the correct side of entry
for the direction called (decision_spine.py Section 2.3c) before
finalizing.

3. TAKE_PROFIT
Set at the nearest genuinely significant structural target in the trade's
direction — the next meaningful liquidity pool, opposing zone, or swing
point. Never stretch it to hit a specific ratio. If multiple honest
targets exist, Pro still reports a single take_profit (laddering is
VIP-only, see vip_TPSL.py) — choose the first, most immediately relevant
one, and you may mention further potential targets in reasoning as
context without making them part of the structured output.

4. RISK_REWARD
Report the honest ratio your own entry/stop/target numbers produce. Do not
pre-filter for "acceptable" ratios yourself — the backend applies a
transparent floor downstream; your job is honest numbers, not gaming the
floor.

5. FINAL CROSS-CHECK BEFORE OUTPUT
Before finalizing, explicitly re-verify:
  - entry is close to current_price (market call) or the decision is
    "Wait" (pending idea).
  - stop_loss and take_profit sit on the structurally correct sides of
    entry.
  - Every one of these three numbers traces to something actually visible
    on this chart, not a remembered "typical" level for the instrument.
This cross-check is not optional flavor text — it is the direct, final
defense against the exact bug this rewrite exists to fix.
"""
