"""
pro_self_review.py
==============================================================================
VectraCore — Pro Tier — Lightweight Self-Check Module
Pro gets a lighter self-check than VIP's mandatory adversarial pass
(see vip_self_review.py) — proportionate to Pro's scope, still real.
"""

PRO_SELF_CHECK = """
------------------------------------------------------------------------------
PRO SELF-CHECK (BEFORE FINALIZING OUTPUT)
------------------------------------------------------------------------------

Before producing final JSON, run this quick check silently:

1. Does entry actually sit close to current_price for a market call, or
   did it drift during the structure/liquidity/order-flow reasoning?
   (This is the exact place the entry-price bug previously occurred —
   check it explicitly, every time, not just when something feels off.)
2. Do stop_loss and take_profit sit on the correct sides of entry?
3. Does institutional_score genuinely reflect the confluence described in
   order_flow_read and reasoning, or is it inflated/deflated relative to
   what was actually argued?
4. Does the decision field match what reasoning actually concludes? (A
   "Wait" decision with reasoning that reads like a confident Buy case, or
   vice versa, is a contradiction — fix it before output.)
5. Is any field carrying the literal string "N/A" where a more honest,
   specific statement is possible?

This is a fast pass, not a full second analysis — its purpose is to catch
mechanical slips (a drifted price, a mismatched field) after the deeper
reasoning work is done, not to re-litigate the whole read from scratch.
If something fails, fix it directly; if you can't fix it honestly, fall
back to Wait.
"""
