VIP_JSON = '''
OUTPUT FORMAT

Return ONLY valid JSON.

For BUY/SELL:
- decision = "Buy" or "Sell"
- entry, stop_loss, take_profit are mandatory
- risk_reward is the real calculated ratio and MUST be >= 1.00
- probability should reflect the selected direction
- WAIT-only trigger fields may remain empty for compatibility

For WAIT:
- entry, stop_loss, take_profit are empty
- explain the concrete WAIT cause
- if one direction clearly leads but RR or execution blocks it, preserve
  that directional lead in probabilities/triggers; do not pretend the
  market is 50/50.

Return EXACTLY:

{
"symbol":"",
"asset_class":"",
"timeframe":"",
"chart_type":"",
"trend":"",
"market_structure":"",
"market_structure_simple":"",
"market_phase":"",
"market_sentiment":"",
"institutional_bias":"",
"higher_timeframe_bias":"",
"demand_supply":"",
"support_resistance":"",
"premium_discount":"",
"equilibrium":"",
"liquidity_sweep":"",
"liquidity_target":"",
"order_block":"",
"breaker_block":"",
"mitigation_block":"",
"fair_value_gap":"",
"change_of_character":"",
"break_of_structure":"",
"institutional_footprints":"",
"session_analysis":"",
"volatility":"",
"intermarket_confirmation":"",
"macro_bias":"",
"geopolitical_bias":"",
"high_impact_news":"",
"economic_calendar":"",
"decision":"",
"suggested_stance":"",
"entry":"",
"stop_loss":"",
"take_profit":"",
"risk_reward":"",
"buy_probability":0,
"sell_probability":0,
"buy_trigger":"",
"sell_trigger":"",
"confirmation_needed":"",
"hold_time":"",
"alternative_bullish_scenario":"",
"alternative_bearish_scenario":"",
"setup_invalidation":"",
"probability":0,
"reasoning":"",
"risk_warning":"This analysis is probabilistic and is not financial advice."
}

Probabilities must be 0-95. Never guarantee profits or certainty.
Never output markdown or text outside JSON.
'''
