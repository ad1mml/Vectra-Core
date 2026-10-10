"""
vip_json.py
==============================================================================
VectraCore — VIP Tier — Output Schema Module
The single source of truth for VIP's exact JSON shape. vip_prompt.py
interpolates this last, right before output, same pattern as pro_json.py.
"""

VIP_JSON = """
------------------------------------------------------------------------------
VIP OUTPUT SCHEMA — CHART MODE — EXACT KEYS, NOTHING EXTRA
------------------------------------------------------------------------------

{
    "symbol": "",
    "timeframe": "",
    "chart_type": "",
    "current_price": "",
    "previous_analysis_link": "",
    "market_structure": "",
    "support_resistance": "",
    "demand_supply": "",
    "liquidity_sweep": "",
    "fair_value_gaps": "",
    "change_of_character": "",
    "order_flow_read": "",
    "institutional_score": 0,
    "market_regime": "",
    "monetary_policy_context": "",
    "geopolitical_risk": "",
    "decision": "",
    "entry": "",
    "stop_loss": "",
    "take_profit_1": "",
    "take_profit_2": "",
    "take_profit_3": "",
    "risk_reward": "",
    "buy_probability": 0,
    "sell_probability": 0,
    "buy_trigger": "",
    "sell_trigger": "",
    "vip_self_review": "",
    "reasoning": ""
}

LIQUIDITY FIELD MAPPING (Liquidity Playbook L9, same as Pro): the field
"support_resistance" is a legacy name and carries the LIQUIDITY MAP (buy-side
pools above, sell-side pools below, each with type, HTF/LTF tag and
unswept/swept/taken status). "liquidity_sweep" is the primary field: the
sweep, its quality, and the draw that follows. "demand_supply" is the
reaction zone created after the sweep. Never use support/resistance language
in any field.

FIELD NOTES (beyond what Pro's schema already covers for shared fields —
see pro_json.py for symbol/timeframe/chart_type/current_price/
market_structure/support_resistance/demand_supply/liquidity_sweep/
fair_value_gaps/change_of_character/order_flow_read/institutional_score/
buy_probability/sell_probability/buy_trigger/sell_trigger, all read
identically at VIP's equal-or-greater rigor):

- previous_analysis_link: the link to this user's saved analysis of the SAME
  symbol (see SYMBOL MEMORY in the request). Empty string "" when the symbol
  has no saved analysis (brand-new chart). Otherwise ONE or TWO short
  sentences that start with exactly one status word in capitals followed by
  " — ": "PENDING — ..." (saved setup still alive, say what is still
  missing), "TRIGGERED — ..." (the saved conditions were met on this chart,
  say what happened), or "GONE — ..." (the saved setup is no longer valid or
  usable, say why, and that this is a fresh analysis informed by how price
  behaved since). Mention how long ago the saved analysis was made.
- market_regime: vip_market_regime.py's classification plus brief
  evidence-based justification.
- monetary_policy_context: vip_monetary_policy.py's read, or an honest
  "not available/not material" statement.
- geopolitical_risk: vip_geopolitics.py's read, or an honest "not
  material" statement.
- decision: exactly "Buy", "Sell", or "Wait" — per vip_decision.py's
  six-gate bar.
- entry / stop_loss: per vip_TPSL.py and decision_spine.py Section 2.
- take_profit_1 / take_profit_2 / take_profit_3: per vip_TPSL.py's ladder
  rules. Empty strings on Wait, or for any rung the chart doesn't
  genuinely support.
- risk_reward: honest ratio against take_profit_1 only.
- vip_self_review: brief, genuine summary of the vip_self_review.py
  adversarial pass.
- reasoning: the full synthesized conclusion from vip_reasoning.py,
  written in the strategist register from vip_identity.py — explicit
  about any tension between technical and contextual layers.

MODE B (general/follow-up) responses use followup_prompt.py's schema
({"answer": ""}) instead — never force this chart schema onto a non-chart
response.
"""
