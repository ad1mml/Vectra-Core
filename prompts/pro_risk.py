PRO_RISK = r"""
PRO RISK ENGINE — HARD MATHEMATICAL GATE, NOT A DIRECTIONAL GATE
================================================================

Evaluate risk only after a coherent market thesis and honest levels exist.

CHECK
-----
- Entry is chart-grounded.
- SL represents genuine invalidation.
- TP is realistic and not artificially distant.
- There is a plausible path to TP.
- Risk is not based on an arbitrary cosmetic level.

FORMULA
-------
RR = abs(TP - Entry) / abs(Entry - SL)

HARD FLOOR
----------
RR < 1.00 -> WAIT.
RR >= 1.00 -> mathematically eligible.

There is no hidden higher threshold.
Do not modify Entry/SL/TP merely to pass the formula.
Do not use high RR to compensate for a poor thesis.
Do not convert RR failure into "no directional bias"; the direction may still
be clear even though execution is blocked.
"""
