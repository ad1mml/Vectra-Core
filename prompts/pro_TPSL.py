"""
pro_TPSL.py
==============================================================================
VectraCore — Pro Tier — Entry/Stop/Target Construction Module
Restates and extends decision_spine.py's Price-Grounding Protocol
specifically for how Pro constructs and reports entry/stop_loss/take_profit.
This restatement is intentional (see decision_spine.py's header note on
redundancy) — this is the single highest-risk area for the entry-price bug
to recur, so it is covered explicitly at every tier's own module too.

Revision note: added the "better entry location" rule, stop-from-zone and
target-from-next-pool construction, and an ATR sanity check. The backend
(app.py + trade_validation.py) now recomputes risk_reward in Python and
treats a far-from-price entry as a pending setup, so this module tells the
model to fix the ENTRY LOCATION when the numbers are poor, never to bend the
stop or target.
"""

PRO_TPSL = """
------------------------------------------------------------------------------
PRO ENTRY / STOP / TARGET CONSTRUCTION
------------------------------------------------------------------------------

Apply decision_spine.py Section 2 (Price-Grounding Protocol) in full before
anything in this module. This module adds Pro-specific construction detail
on top of that mandatory floor.

1. ENTRY LOCATION (the biggest lever on risk/reward)
A market entry in the middle of a range is the usual reason for a ratio
stuck near 1:1: the stop must sit beyond the last swept extreme (far away)
while the first target is only the nearest minor level (close by).

For a market-style Buy/Sell, entry must sit close to current_price per
decision_spine.py Section 2.3(a). Before committing to a market call,
build the trade and look at the ratio it gives:
  - If entry-to-stop is large and entry-to-first-target is small, price is
    badly located for this trade. Do NOT fix it by moving the stop closer
    than structure allows, and do NOT fix it by inventing a farther target.
  - Fix it by finding the better entry LOCATION: the order block, the
    displacement-created reaction zone (demand_supply), the fair value gap,
    or the 50% retracement of the leg. Entered there, the structural stop
    sits just beyond the zone (much tighter) and the same target is farther
    away, which is how a real 1.5-2.5 ratio is produced.
  - If that better location is a level price has not reached yet, it is a
    pending idea, not a market call: follow decision_spine.py Section 2.3(b)
    — decision is "Wait", and the exact level, the invalidation and the
    target are described in buy_trigger/sell_trigger ("Buy at X if price
    pulls back into the zone; invalid below Y; first target Z").
A valid setup that is waiting for location is a useful answer. A dead
"Wait" with no level, or a forced market entry at a poor price, is not.

2. STOP_LOSS
Set per pro_risk.py point 1 — the specific structural invalidation point
(just beyond the zone or the swept extreme), not a convenience distance.
Confirm it sits on the correct side of entry for the direction called
(decision_spine.py Section 2.3c) before finalizing.
ATR sanity check when VERIFIED MARKET FACTS give an ATR: a stop wider than
about 1.5x ATR usually means the entry is badly located (see point 1); a
stop far tighter than about 0.8x ATR will be taken out by noise. Use this
to judge the entry location, never to move the stop away from structure.

3. TAKE_PROFIT
Pro reports a single take_profit. Choose the next genuinely significant
structural target in the trade's direction — the next real liquidity pool,
opposing zone, or swing point — not automatically the nearest minor level
(a tiny intraday high or an inside-the-range bump). If there is a minor
level close by AND a real pool further along, the take_profit is the real
pool, and the minor level may be mentioned in reasoning as a place to trim.
Never stretch the target to hit a specific ratio, and never place it at a
level you cannot see on the chart or in the verified facts. (Laddering into
three targets is VIP-only, see vip_TPSL.py.)

4. RISK_REWARD
Report the ratio your own entry/stop/take_profit produce. The backend
recomputes risk_reward in Python from those three numbers and overrides
yours, so an arithmetic slip costs nothing, but the three numbers must be
right. Do not pre-filter for "acceptable" ratios yourself and do not tune
levels to land on a ratio: a ratio above about 3 on a normal setup usually
means a target was invented, not that the trade is excellent. Keep
expectations honest: 1.5-2.5 is a good ratio.

5. FINAL CROSS-CHECK BEFORE OUTPUT
Before finalizing, explicitly re-verify:
  - entry is close to current_price (market call) or the decision is
    "Wait" (pending idea, with the level written in the trigger).
  - stop_loss and take_profit sit on the structurally correct sides of
    entry.
  - the entry is a good LOCATION (point 1), not just the current price.
  - Every one of these three numbers traces to something actually visible
    on this chart or in the verified facts, not a remembered "typical"
    level for the instrument.
This cross-check is not optional flavor text — it is the direct, final
defense against the exact bug this rewrite exists to fix.
"""
