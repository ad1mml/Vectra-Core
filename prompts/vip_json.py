VIP_JSON = r"""
VIP OUTPUT CONTRACT
===================

Use the application's required JSON schema exactly.

Consistency rules:
- one final decision only;
- BUY/SELL must agree with probabilities and levels;
- WAIT due RR failure must report the actual sub-1.00 RR if that field is part
  of the application schema;
- WAIT due unreadable/no executable setup must not contain fabricated levels;
- all numeric fields must be internally consistent;
- VIP context must not appear as a contradictory second decision.

Do not add keys unless the application schema already supports them.
"""
