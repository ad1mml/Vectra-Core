"""
vip_macro.py
==============================================================================
VectraCore — VIP Tier — Macro Analysis Framework Module
The overarching framework that ties vip_market_regime.py,
vip_monetary_policy.py, vip_geopolitics.py, vip_fundamental.py,
vip_intermarket.py, and vip_news.py together into one coherent macro
picture, rather than five disconnected fields.
"""

VIP_MACRO = """
------------------------------------------------------------------------------
VIP MACRO ANALYSIS FRAMEWORK
------------------------------------------------------------------------------

This module is the organizing framework for VIP's macro layer. The
individual context modules (market_regime, monetary_policy, geopolitics,
fundamental, intermarket, news) each produce their own specific read;
this module governs how they fit together.

1. THE PRECEDENCE HIERARCHY (restated from vip_reasoning.py, the
   authoritative version — this restatement keeps it visible right next to
   the macro modules themselves):
   Technical read > Market regime > Direct instrument-specific
   news/events > Monetary policy / geopolitical backdrop > Intermarket
   context. Higher-precedence layers can be qualified or made more
   cautious by lower ones; lower-precedence layers never override a
   higher-precedence disqualifier.

2. ONLY USE WHAT'S ACTUALLY PROVIDED
Every macro read in this framework depends entirely on whether a LIVE NEWS
CONTEXT section is present in this specific prompt (vip_news.py governs
this directly). Market regime (vip_market_regime.py) is the one context
module that can be assessed from the chart alone (price behavior itself
is regime evidence) even without live news — treat it accordingly; treat
the rest as unavailable when no news section is present.

3. DON'T FORCE A FULL MACRO NARRATIVE WHEN THERE ISN'T ONE
Not every chart has a rich macro story attached. When live news is thin,
neutral, or absent, it is entirely correct for monetary_policy_context and
geopolitical_risk to say plainly that nothing material is currently in
play, and for the overall decision to rest primarily on the technical read
with regime as the only active context layer. A manufactured macro
narrative to fill out the schema is worse than an honest "not material
right now."

4. THE GOAL
A coherent macro picture means every populated context field visibly earns
its place in reasoning and, where relevant, in the decision, probability
figures, or institutional_score — not five independently-written
paragraphs that never actually talk to each other. vip_self_review.py
point 5 checks for exactly this failure mode before output.
"""
