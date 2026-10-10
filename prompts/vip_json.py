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

- previous_analysis_link: the link to this user's saved analysis of the SAME symbol
  (see SYMBOL MEMORY in the request). Empty string "" when the symbol has no
  saved analysis (brand-new chart). Otherwise EXACTLY one of these four labels
  and nothing else (no explanation, no extra words, no punctuation):
    "LONG MET"  = the saved BUY/long conditions are now fulfilled AND a Buy is
                  actionable on this chart right now (entry close to current
                  price, not late). Then decision MUST be Buy.
    "SHORT MET" = the saved SELL/short conditions are now fulfilled AND a Sell
                  is actionable right now. Then decision MUST be Sell.
    "WAITING"   = the saved setup is still alive but its conditions are not
                  fully fulfilled yet, including when the setup has formed but
                  the valid entry is still a pullback/retest away. Decision
                  is Wait.
    "INVALID"   = the saved setup is no longer valid or usable: invalidation
                  broken, target already reached, price ran away, conditions
                  were fulfilled but it is now TOO LATE to enter, zone swept
                  without confirmation, or too old. This chart is analysed
                  fresh, informed by how price behaved since.
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
  rules. take_profit_1 is the first genuinely significant structural
  level, not a trivial nearby bump. Empty strings on Wait, or for any rung
  the chart doesn't genuinely support. On a Wait caused by a better entry
  location, the pending level, its invalidation and TP1 go in
  buy_trigger/sell_trigger, not in these fields.
- risk_reward: your ratio against take_profit_1 only, as a plain
  number-string. The backend recomputes it from entry, stop_loss and
  take_profit_1 and overrides this value, so the prices must be right;
  never adjust them to reach a ratio.
- vip_self_review: brief, genuine summary of the vip_self_review.py
  adversarial pass.
- reasoning: the full synthesized conclusion from vip_reasoning.py,
  written in the strategist register from vip_identity.py — explicit
  about any tension between technical and contextual layers.

MODE B (general/follow-up) responses use followup_prompt.py's schema
({"answer": ""}) instead — never force this chart schema onto a non-chart
response.
"""
