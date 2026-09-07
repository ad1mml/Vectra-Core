VIP_INTERMARKET = r"""
VIP INTERMARKET ENGINE
=====================

Use only relationships that are actually relevant to the asset.

Examples of relationship classes when data is available:
- currency vs rates/yields;
- index vs risk appetite;
- commodity vs related currency;
- bond/risk proxies vs defensive assets.

Do not assume correlation is permanent or causal.
Check direction, timeframe alignment and whether the relationship is currently
coherent. A conflicting intermarket signal is evidence, not an automatic veto.
Missing intermarket data = neutral.
"""
