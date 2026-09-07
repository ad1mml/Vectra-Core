PRO_TPSL = r"""
PRO TP / SL ENGINE — INVALIDATION FIRST, DESTINATION SECOND
============================================================

STOP LOSS
---------
Place SL beyond the structural point that proves the thesis wrong.
BUY -> below meaningful bullish invalidation.
SELL -> above meaningful bearish invalidation.

SL must:
- protect against normal chart noise;
- remain tied to the actual thesis;
- not be arbitrary;
- not be tightened only to inflate RR;
- not be placed beyond a structure that has already failed.

TAKE PROFIT
-----------
Choose the nearest realistic objective that has a market reason, such as:
- opposing external liquidity;
- major swing point;
- range boundary;
- opposing supply/demand;
- HTF objective;
- other clearly visible destination.

TP must not be stretched into empty space just to pass RR.

GEOMETRY
--------
For BUY: risk = Entry - SL; reward = TP - Entry.
For SELL: risk = SL - Entry; reward = Entry - TP.
Use absolute values in the formal RR formula.

VALIDATION
----------
If the honest target gives RR < 1.00, the trade is not executable under the
master contract. Return the geometry to the decision engine; do not alter the
levels artificially.
"""
