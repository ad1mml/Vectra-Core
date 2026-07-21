"""
VIP_PROMPT — assembled to mirror an actual institutional committee
structure, since several of the specialist modules explicitly describe
themselves as reporting UP to a Validator / Self-Review / Decision
Committee rather than deciding anything themselves. Order:

  1. IDENTITY & REASONING      -> who you are, how you think
  2. TECHNICAL SPECIALISTS     -> structure -> liquidity -> order flow
                                   -> technical synthesis
  3. FUNDAMENTAL SPECIALISTS   -> macro -> news -> monetary policy ->
                                   geopolitics -> intermarket ->
                                   fundamental synthesis
  4. MARKET REGIME             -> reads both clusters above
  5. RISK                      -> assesses the whole picture so far
  6. EXECUTION                 -> trade timing/entry mechanics
  7. VALIDATION COMMITTEE      -> validator -> self-review (each
                                   explicitly receives every specialist
                                   above)
  8. DECISION COMMITTEE        -> decision -> confluence score ->
                                   probability (each explicitly receives
                                   the validation committee's output too)
  9. CONTINUITY & COACHING     -> memory -> coach
 10. RULES RECAP               -> non-negotiable meta-rules, right
                                   before output
 11. OUTPUT FORMAT             -> JSON schema, always last

Each module is its own file under prompts/ so it can be tuned
independently without touching this file.
"""

# 1. Identity & reasoning
from prompts.vip_identity import VIP_IDENTITY
from prompts.vip_reasoning import VIP_REASONING

# 2. Technical specialists
from prompts.vip_structure import VIP_STRUCTURE
from prompts.vip_liquidity import VIP_LIQUIDITY
from prompts.vip_orderflow import VIP_ORDERFLOW
from prompts.vip_technical import VIP_TECHNICAL

# 3. Fundamental specialists
from prompts.vip_macro import VIP_MACRO
from prompts.vip_news import VIP_NEWS
from prompts.vip_monetary_policy import VIP_MONETARY_POLICY
from prompts.vip_geopolitics import VIP_GEOPOLITICS
from prompts.vip_intermarket import VIP_INTERMARKET
from prompts.vip_fundamental import VIP_FUNDAMENTAL

# 4. Market regime — reads both clusters above
from prompts.vip_market_regime import VIP_MARKET_REGIME

# 5. Risk — assesses the whole picture so far
from prompts.vip_risk import VIP_RISK

# 6. Execution — trade timing/entry mechanics
from prompts.vip_execution import VIP_EXECUTION

# 7. Validation committee
from prompts.vip_validator import VIP_VALIDATOR
from prompts.vip_self_review import VIP_SELF_REVIEW

# 8. Decision committee
from prompts.vip_decision import VIP_DECISION
from prompts.vip_score import VIP_SCORE
from prompts.vip_probability import VIP_PROBABILITY

# 9. Continuity & coaching
from prompts.vip_memory import VIP_MEMORY
from prompts.vip_coach import VIP_COACH

# 10. Rules recap
from prompts.vip_rules import VIP_RULES

# 11. Output format — always last
from prompts.vip_json import VIP_JSON


VIP_PROMPT = f"""
{VIP_IDENTITY}
==========================================================
VIP OPERATING MODE
==========================================================

You are an institutional committee.

Every specialist below exists.

However:

Only activate the specialists required for the user's request.

Examples

If a chart is uploaded:

Primary specialists:

• Technical
• Structure
• Liquidity
• Order Flow
• Market Regime
• Risk
• Validator
• Decision

Secondary specialists (only if needed):

• Macro
• News
• Monetary Policy
• Geopolitics
• Intermarket

If the user asks only a macro question:

Activate only:

Macro

News

Monetary

Intermarket

Decision

If the user requests combined technical and fundamental analysis,

activate every specialist.

Never spend reasoning on specialists that are irrelevant.

This does NOT remove any specialist.

It only determines which specialists actively participate in the current task.

{VIP_REASONING}

==========================================================
TECHNICAL SPECIALISTS
==========================================================

{VIP_STRUCTURE}

{VIP_LIQUIDITY}

{VIP_ORDERFLOW}

{VIP_TECHNICAL}

==========================================================
FUNDAMENTAL SPECIALISTS
==========================================================

{VIP_MACRO}

{VIP_NEWS}

{VIP_MONETARY_POLICY}

{VIP_GEOPOLITICS}

{VIP_INTERMARKET}

{VIP_FUNDAMENTAL}

==========================================================
MARKET REGIME
==========================================================

{VIP_MARKET_REGIME}

==========================================================
RISK
==========================================================

{VIP_RISK}

==========================================================
EXECUTION
==========================================================

{VIP_EXECUTION}

==========================================================
VALIDATION COMMITTEE
==========================================================

{VIP_VALIDATOR}

{VIP_SELF_REVIEW}

==========================================================
DECISION COMMITTEE
==========================================================

{VIP_DECISION}

{VIP_SCORE}

{VIP_PROBABILITY}

==========================================================
CONTINUITY & COACHING
==========================================================

{VIP_MEMORY}

{VIP_COACH}

==========================================================
RULES RECAP
==========================================================

{VIP_RULES}

==========================================================
OUTPUT FORMAT (always follow this exactly)
==========================================================

{VIP_JSON}
"""
