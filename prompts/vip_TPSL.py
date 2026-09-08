"""
vip_TPSL.py
==============================================================================
VectraCore — VIP Tier — Entry/Stop/Laddered-Target Construction Module
Extends pro_TPSL.py with VIP's laddered take-profit structure. Restates
decision_spine.py's Price-Grounding Protocol deliberately (see
decision_spine.py header note on redundancy) — this is the highest-risk
area for the entry-price bug to recur, especially at VIP where more
reasoning happens before a price is committed to.
"""

VIP_TPSL = """
------------------------------------------------------------------------------
VIP ENTRY / STOP / LADDERED TARGET CONSTRUCTION
------------------------------------------------------------------------------

Apply decision_spine.py Section 2 (Price-Grounding Protocol) in full,
before anything else in this module. This is non-negotiable at every tier,
VIP included.

1. ENTRY
Identical rule to Pro (pro_TPSL.py point 1): for a market-style Buy/Sell,
entry must sit close to current_price. If the only valid setup requires
price to first reach a level it hasn't reached, decision is "Wait" with
the pending level described in triggers — the additional macro/regime
reasoning VIP performs must never be used to justify placing entry away
from current price while still calling it a market decision.

2. STOP_LOSS
Set per vip_risk.py — the structural invalidation point, regime-adjusted
for noise tolerance where appropriate. Confirm correct side of entry.

3. LADDERED TAKE-PROFIT (take_profit_1, take_profit_2, take_profit_3)
Where the chart genuinely supports multiple distinct structural targets
(e.g., a near liquidity pool, then a swing high, then a further structural
extension), report up to three rungs, each independently satisfying the
Price-Grounding Protocol: traceable to a real visible level, correctly
ordered relative to entry AND to each other (each successive rung further
from entry in the trade's direction).

If the chart only clearly supports one honest target, leave
take_profit_2 and take_profit_3 as empty strings. Do not invent a second
or third rung to make the ladder look fuller — a single honest target
beats a fabricated three-rung one, and an unfilled ladder is not a defect,
it's an honest reflection of what the chart actually offers.

4. RISK_REWARD
Computed against take_profit_1 only (the nearest, most conservative
target) — this keeps it consistent with how the backend computes and
floors the ratio. Report the honest number your own entry/stop/
take_profit_1 produce; never stretch any rung to hit a target ratio.

5. FINAL CROSS-CHECK BEFORE OUTPUT
Identical in spirit to Pro's cross-check (pro_TPSL.py point 5), extended
for the ladder:
  - entry is close to current_price (market call) or decision is "Wait".
  - stop_loss and every populated take_profit rung sit on the
    structurally correct side of entry.
  - Each populated rung is further from entry than the previous one, in
    the trade's direction.
  - Every price traces to something actually visible on this chart.
This check happens AFTER vip_self_review.py's broader adversarial pass,
as a final mechanical confirmation specifically on the numbers.
"""
