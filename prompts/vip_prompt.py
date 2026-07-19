"""
VIP_PROMPT — assembled in a deliberate task sequence, not just import order.

The sequence mirrors how a real institutional analyst actually works:

  1. IDENTITY & REASONING   -> who you are, how you think before answering
  2. TECHNICAL CLUSTER      -> build the technical picture, piece by piece
  3. FUNDAMENTAL CLUSTER    -> build the macro/news picture, piece by piece
  4. MARKET REGIME          -> combine technical + fundamental into one read
  5. DECISION-MAKING        -> execution timing, risk, confluence scoring,
                               final decision, probability calibration
  6. QUALITY CONTROL        -> validate and self-review the draft answer
                               before it goes out
  7. CONTINUITY & COACHING  -> long-term memory, trading-coach behavior
  8. RULES RECAP            -> the non-negotiable meta-rules, right before
                               output, so they're freshest in context
  9. OUTPUT FORMAT          -> JSON schema, always last

Each module below is its own file under prompts/ so it can be tuned
independently without touching this file.
"""

# 1. Identity & reasoning
from prompts.vip_identity import VIP_IDENTITY
from prompts.vip_reasoning import VIP_REASONING

# 2. Technical cluster (structure -> liquidity -> order flow -> synthesis)
from prompts.vip_structure import VIP_STRUCTURE
from prompts.vip_liquidity import VIP_LIQUIDITY
from prompts.vip_orderflow import VIP_ORDERFLOW
from prompts.vip_technical import VIP_TECHNICAL

# 3. Fundamental cluster (macro -> news -> policy -> geopolitics ->
#    intermarket -> synthesis)
from prompts.vip_macro import VIP_MACRO
from prompts.vip_news import VIP_NEWS
from prompts.vip_monetary_policy import VIP_MONETARY_POLICY
from prompts.vip_geopolitics import VIP_GEOPOLITICS
from prompts.vip_intermarket import VIP_INTERMARKET
from prompts.vip_fundamental import VIP_FUNDAMENTAL

# 4. Market regime — combines technical + fundamental into one read
from prompts.vip_market_regime import VIP_MARKET_REGIME

# 5. Decision-making (execution timing -> risk -> scoring -> decision ->
#    probability)
from prompts.vip_execution import VIP_EXECUTION
from prompts.vip_risk import VIP_RISK
from prompts.vip_score import VIP_SCORE
from prompts.vip_decision import VIP_DECISION
from prompts.vip_probability import VIP_PROBABILITY

# 6. Quality control — check the draft answer before it goes out
from prompts.vip_validator import VIP_VALIDATOR
from prompts.vip_self_review import VIP_SELF_REVIEW

# 7. Continuity & coaching
from prompts.vip_memory import VIP_MEMORY
from prompts.vip_coach import VIP_COACH

# 8. Rules recap — kept close to the end so it's freshest before output
from prompts.vip_rules import VIP_RULES

# 9. Output format — always last
from prompts.vip_json import VIP_JSON


VIP_PROMPT = f"""
{VIP_IDENTITY}

{VIP_REASONING}

==========================================================
TECHNICAL ANALYSIS CLUSTER
==========================================================

{VIP_STRUCTURE}

{VIP_LIQUIDITY}

{VIP_ORDERFLOW}

{VIP_TECHNICAL}

==========================================================
FUNDAMENTAL / MACRO ANALYSIS CLUSTER
==========================================================

{VIP_MACRO}

{VIP_NEWS}

{VIP_MONETARY_POLICY}

{VIP_GEOPOLITICS}

{VIP_INTERMARKET}

{VIP_FUNDAMENTAL}

==========================================================
MARKET REGIME (combines the two clusters above)
==========================================================

{VIP_MARKET_REGIME}

==========================================================
DECISION-MAKING
==========================================================

{VIP_EXECUTION}

{VIP_RISK}

{VIP_SCORE}

{VIP_DECISION}

{VIP_PROBABILITY}

==========================================================
QUALITY CONTROL — validate before answering
==========================================================

{VIP_VALIDATOR}

{VIP_SELF_REVIEW}

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
