"""
pro_json.py
==============================================================================
VectraCore — Pro Tier — Output Schema Module
The single source of truth for Pro's exact JSON shape. pro_prompt.py
interpolates this near the end of the assembled prompt, after all
analytical modules, so the schema is the last thing reinforced before the
model produces output.
"""

PRO_JSON = """
------------------------------------------------------------------------------
PRO OUTPUT SCHEMA — CHART MODE (MODE A) — EXACT KEYS, NOTHING EXTRA
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
    "decision": "",
    "entry": "",
    "stop_loss": "",
    "take_profit": "",
    "risk_reward": "",
    "buy_probability": 0,
    "sell_probability": 0,
    "buy_trigger": "",
    "sell_trigger": "",
    "reasoning": ""
}

FIELD NOTES:

- symbol / timeframe / chart_type: read directly off the chart. State
  plainly ("not visible on this chart") if genuinely unreadable — never
  guess.
- current_price: the Price-Grounding Protocol anchor (decision_spine.py
  Section 2.1), exactly as read.
- market_structure: the pro_structure.py read — trend-cycle position,
  range-vs-trend distinction, multi-swing confluence where relevant.
- support_resistance: the most relevant zones, described with the
  precision from pro_technical.py point 4.
- demand_supply: the most relevant zone(s), with the displacement quality
  from pro_liquidity.py point 2 noted.
- liquidity_sweep: the sweep-quality characterization from pro_liquidity.py
  point 1, or an honest statement that none is currently visible.
- fair_value_gaps: per pro_technical.py point 2's precise definition, with
  fill status noted.
- change_of_character: whether a CHOCH is currently in play, per
  decision_spine.py Section 3.4.
- order_flow_read: the pro_orderflow.py synthesis — obvious-level-vs-
  structural-footprint distinction, directional intent where visible.
- institutional_score: per pro_score.py's methodology, 0-100.
- decision: exactly "Buy", "Sell", or "Wait".
- entry / stop_loss / take_profit: per pro_TPSL.py and decision_spine.py
  Section 2. Empty strings if decision is "Wait".
- risk_reward: the honest ratio, as a plain number-string (e.g. "1.8").
  Empty on Wait.
- buy_probability / sell_probability: calibrated 0-100 per pro_decision.py.
- buy_trigger / sell_trigger: what would need to happen for that side to
  become valid — informative even (especially) on a Wait.
- reasoning: the synthesized conclusion from pro_reasoning.py, written at
  Pro's assumed fluency level (pro_coach.py point 1's framing applies to
  chart reasoning too, not just Mode B answers).

MODE B (general/follow-up) responses use followup_prompt.py's schema
({"answer": ""}) instead — never force this chart schema onto a non-chart
response.
"""
