from prompts.pro_prompt import PRO_PROMPT
from prompts.vip_identity import VIP_IDENTITY
from prompts.vip_market_regime import VIP_MARKET_REGIME
from prompts.vip_liquidity import VIP_LIQUIDITY
from prompts.vip_orderflow import VIP_ORDERFLOW
from prompts.vip_technical import VIP_TECHNICAL
from prompts.vip_structure import VIP_STRUCTURE
from prompts.vip_macro import VIP_MACRO
from prompts.vip_news import VIP_NEWS
from prompts.vip_monetary_policy import VIP_MONETARY_POLICY
from prompts.vip_geopolitics import VIP_GEOPOLITICS
from prompts.vip_intermarket import VIP_INTERMARKET
from prompts.vip_fundamental import VIP_FUNDAMENTAL
from prompts.vip_memory import VIP_MEMORY
from prompts.vip_probability import VIP_PROBABILITY
from prompts.vip_decision import VIP_DECISION
from prompts.vip_validator import VIP_VALIDATOR
from prompts.vip_self_review import VIP_SELF_REVIEW
from prompts.vip_score import VIP_SCORE
from prompts.vip_risk import VIP_RISK
from prompts.vip_execution import VIP_EXECUTION
from prompts.vip_TPSL import VIP_TPSL
from prompts.vip_coach import VIP_COACH
from prompts.vip_rules import VIP_RULES
from prompts.vip_json import VIP_JSON

VIP_PROMPT = f"""
{PRO_PROMPT}

============================================================
VIP EXTENSION — SAME PRO DECISION CONTRACT + EXTRA CONTEXT
============================================================

{VIP_IDENTITY}
{VIP_MARKET_REGIME}
{VIP_STRUCTURE}
{VIP_LIQUIDITY}
{VIP_ORDERFLOW}
{VIP_TECHNICAL}
{VIP_MACRO}
{VIP_NEWS}
{VIP_MONETARY_POLICY}
{VIP_GEOPOLITICS}
{VIP_INTERMARKET}
{VIP_FUNDAMENTAL}
{VIP_MEMORY}
{VIP_PROBABILITY}
{VIP_RISK}
{VIP_EXECUTION}
{VIP_TPSL}
{VIP_VALIDATOR}
{VIP_SELF_REVIEW}
{VIP_DECISION}
{VIP_SCORE}
{VIP_COACH}
{VIP_RULES}
{VIP_JSON}
"""
