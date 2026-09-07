FOLLOWUP_PROMPT = r"""
VECTRACORE FOLLOW-UP ANALYSIS
=============================

Treat the newest uploaded chart as the current source of truth.
Do not preserve an earlier BUY/SELL/WAIT merely for consistency.

1. Re-read current chart structure.
2. Identify what changed from the previous visible state, if comparison is
   actually possible.
3. Re-evaluate regime, liquidity, reaction and structural control.
4. Check whether the previous thesis remains valid or has been invalidated.
5. If a valid executable setup now exists, do not send the user into another
   confirmation loop.
6. If WAIT remains necessary, identify the concrete blocker under the master
   rules, especially RR < 1.00 or genuine structural ambiguity.

Previous analysis is context, not evidence.
"""
