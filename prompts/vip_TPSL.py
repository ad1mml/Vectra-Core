"""
vip_TPSL.py
==============================================================================
VectraCore — VIP Tier — Entry/Stop/Laddered-Target Construction Module
Extends pro_TPSL.py with VIP's laddered take-profit structure. Restates
decision_spine.py's Price-Grounding Protocol deliberately (see
decision_spine.py header note on redundancy) — this is the highest-risk
area for the entry-price bug to recur, especially at VIP where more
reasoning happens before a price is committed to.

Revision note: aligned with pro_TPSL.py's "better entry location" rule and
the backend's Python-side risk_reward recompute. risk_reward is measured
against take_profit_1, so TP1 must be a real structural target, not the
smallest nearby bump.
"""

VIP_TPSL = """
------------------------------------------------------------------------------
VIP ENTRY / STOP / LADDERED TARGET CONSTRUCTION
------------------------------------------------------------------------------

Apply decision_spine.py Section 2 (Price-Grounding Protocol) in full,
before anything else in this module. This is non-negotiable at every tier,
VIP included.

1. ENTRY LOCATION
Same rule as Pro (pro_TPSL.py point 1). A market entry mid-range gives a
far stop and a near first target, which is what produces a ratio near 1:1.
Do not repair that by tightening the stop past structure or by inventing a
farther target; repair it by finding the better entry LOCATION (order block,
displacement-created reaction zone, fair value gap, or 50% of the leg),
where the structural stop is tight and the targets are far.
For a market-style Buy/Sell, entry must sit close to current_price. If the
better location is a level price has not reached yet, decision is "Wait"
and the pending level, its invalidation and TP1 are written into
buy_trigger/sell_trigger ("Buy at X on a pullback into the zone; invalid
below Y; TP1 Z"). The macro/regime reasoning VIP performs must never be
used to justify placing entry away from current price while still calling
it a market decision.

2. STOP_LOSS
Set per vip_risk.py — the structural invalidation point, regime-adjusted
for noise tolerance where appropriate. Confirm correct side of entry.
ATR sanity check (when VERIFIED MARKET FACTS give an ATR): a stop wider
than about 1.5x ATR usually signals a badly located entry; a stop much
tighter than about 0.8x ATR will be taken out by noise. This judges the
entry location; it never moves the stop off structure.

3. LADDERED TAKE-PROFIT (take_profit_1, take_profit_2, take_profit_3)
Where the chart genuinely supports multiple distinct structural targets,
report up to three rungs, each independently satisfying the Price-Grounding
Protocol: traceable to a real visible level, correctly ordered relative to
entry AND to each other (each successive rung further from entry in the
trade's direction).
  - take_profit_1: the first genuinely significant structural level — a real
    liquidity pool, opposing zone or swing point, not a trivial minor bump
    right next to entry. This is the rung risk_reward is measured against.
  - take_profit_2: the next real pool or higher-timeframe level.
  - take_profit_3: the major draw on liquidity, only if the chart supports it.
If the chart only clearly supports one honest target, leave take_profit_2
and take_profit_3 as empty strings. Do not invent a second or third rung to
make the ladder look fuller — a single honest target beats a fabricated
three-rung one.

4. RISK_REWARD
Measured against take_profit_1 only. The backend recomputes it in Python
from entry, stop_loss and take_profit_1 and overrides yours, so the three
numbers must be right; the ratio itself is not yours to tune. Never stretch
any rung to hit a target ratio. A TP1 ratio above about 3 on a normal setup
usually means a target was invented. 1.5-2.5 is a good TP1 ratio, and the
extra reward should come from TP2/TP3, not from an inflated TP1.

5. FINAL CROSS-CHECK BEFORE OUTPUT
Identical in spirit to Pro's cross-check (pro_TPSL.py point 5), extended
for the ladder:
  - entry is close to current_price (market call) or decision is "Wait"
    with the pending level written in the trigger.
  - the entry is a good location, not just the current price.
  - stop_loss and every populated take_profit rung sit on the
    structurally correct side of entry.
  - Each populated rung is further from entry than the previous one, in
    the trade's direction.
  - Every price traces to something actually visible on this chart or in
    the verified facts.
This check happens AFTER vip_self_review.py's broader adversarial pass,
as a final mechanical confirmation specifically on the numbers.
"""
