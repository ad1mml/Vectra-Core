PRO_JSON = r"""
PRO OUTPUT CONTRACT
===================

Return ONLY the schema required by the application. Do not add arbitrary
keys, markdown, hidden commentary, or competing decisions.

INTERNAL CONSISTENCY REQUIREMENTS
---------------------------------
- decision must be exactly BUY, SELL, or WAIT according to the application enum;
- if BUY, bullish probability should lead and Entry/SL/TP must be bullish-
  coherent when those fields are required;
- if SELL, bearish probability should lead and levels must be bearish-coherent;
- if WAIT because RR < 1.00, do not report an RR >= 1.00;
- if WAIT because no executable setup exists, do not fabricate Entry/SL/TP;
- numeric levels must be internally consistent;
- RR must equal the formula within normal rounding tolerance;
- probabilities must be valid numbers and not canned solely because a decision
  is uncertain.

Never output multiple alternative final trades when the schema expects one.
"""
