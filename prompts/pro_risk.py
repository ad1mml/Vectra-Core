PRO_RISK = '''
RISK ENGINE

Assess:
- entry quality
- structural SL
- realistic TP
- RR
- volatility
- nearby opposing structure/liquidity
- execution risk

RR is calculated from the real structural levels.
RR < 1.00 is a hard reject.
RR >= 1.00 is eligible; higher RR is better only when the target remains
realistic.

Do not reject a coherent setup solely because RR is below an arbitrary
higher target such as 2.3R. Do not manipulate SL/TP.

Only flag WAIT when the levels are unsupported, the chart is unreadable,
there is a genuine hard contradiction, or RR < 1.00.
'''
