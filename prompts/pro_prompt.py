from prompts.pro_identity import PRO_IDENTITY
from prompts.pro_technical import PRO_TECHNICAL
from prompts.pro_execution import PRO_EXECUTION
from prompts.pro_TPSL import PRO_TPSL
from prompts.pro_score import PRO_SCORE
from prompts.pro_rules import PRO_RULES
from prompts.pro_reasoning import PRO_REASONING
from prompts.pro_json import PRO_JSON
from prompts.pro_coach import PRO_COACH
from prompts.pro_structure import PRO_STRUCTURE
from prompts.pro_liquidity import PRO_LIQUIDITY
from prompts.pro_orderflow import PRO_ORDERFLOW
from prompts.pro_validator import PRO_VALIDATOR
from prompts.pro_risk import PRO_RISK
from prompts.pro_decision import PRO_DECISION
from prompts.pro_self_review import PRO_SELF_REVIEW
from prompts.decision_spine import DECISION_SPINE

PRO_PROMPT = f"""
{PRO_IDENTITY}

{PRO_TECHNICAL}

{PRO_STRUCTURE}

{PRO_LIQUIDITY}

{PRO_ORDERFLOW}

{PRO_EXECUTION}

{PRO_TPSL}

{PRO_RISK}

{PRO_VALIDATOR}

{PRO_SELF_REVIEW}

{PRO_DECISION}

{PRO_SCORE}

{PRO_RULES}

{PRO_REASONING}

{PRO_COACH}

INSTITUTIONAL SIGNAL QUALITY OVERRIDE
------------------------------------
Before accepting any BUY/SELL evidence, discount isolated retail patterns and
test the apparent signal for fakeout, liquidity trap, failed breakout, level
acceptance/rejection, and continuation-vs-reversal context. A signal is not
validated merely because an indicator, candle pattern, S/R level, FVG, OB, or
liquidity sweep is present. Prefer causal price behavior and structural
consequences over visual pattern recognition.

{DECISION_SPINE}

{PRO_JSON}
"""
