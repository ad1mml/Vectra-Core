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
    "previous_analysis_link": "",
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
- previous_analysis_link: the link to this user's saved analysis of the SAME symbol
  (see SYMBOL MEMORY in the request). Empty string "" when the symbol has no
  saved analysis (brand-new chart). Otherwise EXACTLY one of these four labels
  and nothing else (no explanation, no extra words, no punctuation):
    "LONG MET"  = the saved BUY/long conditions are now fulfilled on this
                  chart. Then decision must not be Sell.
    "SHORT MET" = the saved SELL/short conditions are now fulfilled on this
                  chart. Then decision must not be Buy.
    "WAITING"   = the saved setup is still alive but neither side's
                  conditions are fulfilled yet.
    "INVALID"   = the saved setup is no longer valid or usable (invalidation
                  broken, target already reached, price ran away without a
                  valid entry, zone swept without confirmation, or too old);
                  this chart is analysed fresh, informed by how price
                  behaved since.
- market_structure: the pro_structure.py read — trend-cycle position,
  range-vs-trend distinction, multi-swing confluence where relevant.
- support_resistance: LEGACY FIELD NAME — this field carries the LIQUIDITY
  MAP (Liquidity Playbook L9). Buy-side pools above and sell-side pools
  below, each with type, HTF/LTF tag, stacking and status
  (unswept/swept/taken), described with the precision from
  pro_technical.py point 4. Never write support/resistance language here.
- demand_supply: the entry/reaction zone created by the displacement after
  the sweep, with the displacement quality from pro_liquidity.py point 5
  noted. Empty string if none is clean.
- liquidity_sweep: the primary field — the sweep-quality characterization
  from pro_liquidity.py point 4, the draw on liquidity that follows, or an
  honest statement of which pool has not been swept yet.
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
