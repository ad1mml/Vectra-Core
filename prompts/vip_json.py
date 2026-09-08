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

FIELD NOTES (beyond what Pro's schema already covers for shared fields —
see pro_json.py for symbol/timeframe/chart_type/current_price/
market_structure/support_resistance/demand_supply/liquidity_sweep/
fair_value_gaps/change_of_character/order_flow_read/institutional_score/
buy_probability/sell_probability/buy_trigger/sell_trigger, all read
identically at VIP's equal-or-greater rigor):

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
