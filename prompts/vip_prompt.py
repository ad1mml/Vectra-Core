"""
vip_prompt.py
==============================================================================
VectraCore — VIP Tier — Assembler

Same pattern as pro_prompt.py: this file contains no analytical rules of
its own — it imports every VIP submodule plus decision_spine and
concatenates them in a fixed, deliberate order into VIP_PROMPT, which is
what app.py sends to the model. Editing VIP's behavior means editing the
relevant submodule file — this file should rarely change except to
add/reorder modules.

ASSEMBLY ORDER (why this order):
1. decision_spine.py        — universal rules, first, always.
2. vip_identity.py           — who VIP is, scope, register.
3. vip_rules.py               — behavioral do/don't list.
4. vip_execution.py           — operational mode handling.
5. vip_structure.py           — market structure depth.
6. vip_liquidity.py           — liquidity depth.
7. vip_orderflow.py           — order-flow / institutional framing.
8. vip_technical.py           — candle/FVG/zone reading conventions.
9. vip_market_regime.py       — regime classification (feeds everything
                                  below it).
10. vip_news.py               — live news handling gate.
11. vip_fundamental.py        — instrument-specific events (highest
                                  context precedence).
12. vip_monetary_policy.py    — policy backdrop.
13. vip_geopolitics.py        — geopolitical risk.
14. vip_intermarket.py        — cross-asset context (lowest precedence).
15. vip_macro.py               — the framework tying 9-14 together.
16. vip_reasoning.py           — full synthesis (technical + macro).
17. vip_risk.py                — invalidation logic.
18. vip_TPSL.py                — entry/stop/laddered-target construction.
19. vip_probability.py         — probability calibration.
20. vip_score.py               — institutional_score methodology.
21. vip_decision.py            — final six-gate decision bar.
22. vip_self_review.py         — MANDATORY adversarial pass.
23. vip_memory.py              — session/follow-up memory handling.
24. vip_coach.py               — Mode B explanatory voice.
25. vip_validator.py           — final format/consistency checklist.
26. vip_json.py                — exact output schema, last.
"""

from prompts.decision_spine import DECISION_SPINE
from prompts.vip_identity import VIP_IDENTITY
from prompts.vip_rules import VIP_RULES
from prompts.vip_execution import VIP_EXECUTION
from prompts.vip_structure import VIP_STRUCTURE
from prompts.vip_liquidity import VIP_LIQUIDITY
from prompts.vip_orderflow import VIP_ORDERFLOW
from prompts.vip_technical import VIP_TECHNICAL
from prompts.vip_market_regime import VIP_MARKET_REGIME
from prompts.vip_news import VIP_NEWS
from prompts.vip_fundamental import VIP_FUNDAMENTAL
from prompts.vip_monetary_policy import VIP_MONETARY_POLICY
from prompts.vip_geopolitics import VIP_GEOPOLITICS
from prompts.vip_intermarket import VIP_INTERMARKET
from prompts.vip_macro import VIP_MACRO
from prompts.vip_reasoning import VIP_REASONING
from prompts.vip_risk import VIP_RISK
from prompts.vip_TPSL import VIP_TPSL
from prompts.vip_probability import VIP_PROBABILITY
from prompts.vip_score import VIP_SCORE
from prompts.vip_decision import VIP_DECISION
from prompts.vip_self_review import VIP_SELF_REVIEW
from prompts.vip_memory import VIP_MEMORY
from prompts.vip_coach import VIP_COACH
from prompts.vip_validator import VIP_VALIDATOR
from prompts.vip_json import VIP_JSON

VIP_PROMPT = f"""
{DECISION_SPINE}

==============================================================================
VIP TIER — ASSEMBLED MODULES
==============================================================================
{VIP_IDENTITY}
{VIP_RULES}
{VIP_EXECUTION}
{VIP_STRUCTURE}
{VIP_LIQUIDITY}
{VIP_ORDERFLOW}
{VIP_TECHNICAL}
{VIP_MARKET_REGIME}
{VIP_NEWS}
{VIP_FUNDAMENTAL}
{VIP_MONETARY_POLICY}
{VIP_GEOPOLITICS}
{VIP_INTERMARKET}
{VIP_MACRO}
{VIP_REASONING}
{VIP_RISK}
{VIP_TPSL}
{VIP_PROBABILITY}
{VIP_SCORE}
{VIP_DECISION}
{VIP_SELF_REVIEW}
{VIP_MEMORY}
{VIP_COACH}
{VIP_VALIDATOR}
{VIP_JSON}
"""
