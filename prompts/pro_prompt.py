"""
pro_prompt.py
==============================================================================
VectraCore — Pro Tier — Assembler

This file does not contain analytical rules itself — it imports every Pro
submodule and the shared decision_spine, and concatenates them in a fixed,
deliberate order into PRO_PROMPT, which is what app.py actually sends to
the model. Editing Pro's behavior means editing the relevant submodule
file (pro_identity.py, pro_structure.py, pro_liquidity.py, etc.) — this
file should rarely need to change except to add/reorder modules.

ASSEMBLY ORDER (why this order):
1. decision_spine.py    — universal rules every tier obeys, first.
2. pro_identity.py       — who Pro is, the Mode A/B split.
3. pro_rules.py          — behavioral do/don't list.
4. pro_execution.py      — operational Mode A/B handling, market vs pending.
5. pro_structure.py      — market structure depth.
6. pro_liquidity.py      — liquidity depth.
7. pro_orderflow.py      — order-flow / institutional framing.
8. pro_technical.py      — candle/FVG/zone reading conventions.
9. pro_reasoning.py      — synthesis methodology (combines 5-8).
10. pro_risk.py          — invalidation logic.
11. pro_TPSL.py          — entry/stop/target construction (uses 10).
12. pro_score.py         — institutional_score methodology.
13. pro_decision.py      — final Buy/Sell/Wait decision bar.
14. pro_self_review.py   — lightweight mechanical self-check.
15. pro_coach.py         — Mode B explanatory voice.
16. pro_validator.py     — final format/consistency checklist.
17. pro_json.py          — exact output schema, last, right before output.
"""

from prompts.decision_spine import DECISION_SPINE
from prompts.pro_identity import PRO_IDENTITY
from prompts.pro_rules import PRO_RULES
from prompts.pro_execution import PRO_EXECUTION
from prompts.pro_structure import PRO_STRUCTURE
from prompts.pro_liquidity import PRO_LIQUIDITY
from prompts.pro_orderflow import PRO_ORDERFLOW
from prompts.pro_technical import PRO_TECHNICAL
from prompts.pro_reasoning import PRO_REASONING
from prompts.pro_risk import PRO_RISK
from prompts.pro_TPSL import PRO_TPSL
from prompts.pro_score import PRO_SCORE
from prompts.pro_decision import PRO_DECISION
from prompts.pro_self_review import PRO_SELF_CHECK
from prompts.pro_coach import PRO_COACH
from prompts.pro_validator import PRO_VALIDATOR
from prompts.pro_json import PRO_JSON

PRO_PROMPT = f"""
{DECISION_SPINE}

==============================================================================
PRO TIER — ASSEMBLED MODULES
==============================================================================
{PRO_IDENTITY}
{PRO_RULES}
{PRO_EXECUTION}
{PRO_STRUCTURE}
{PRO_LIQUIDITY}
{PRO_ORDERFLOW}
{PRO_TECHNICAL}
{PRO_REASONING}
{PRO_RISK}
{PRO_TPSL}
{PRO_SCORE}
{PRO_DECISION}
{PRO_SELF_CHECK}
{PRO_COACH}
{PRO_VALIDATOR}
{PRO_JSON}
"""
