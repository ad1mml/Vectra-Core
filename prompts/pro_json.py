PRO_JSON = '''
OUTPUT FORMAT

Return ONLY valid JSON.

When BUY or SELL:
- decision is exactly "Buy" or "Sell"
- entry, stop_loss and take_profit are mandatory
- risk_reward must be the real ratio and must be >= 1.00
- probability should reflect directional evidence
- WAIT-only trigger fields may remain empty for compatibility

When WAIT:
- entry, stop_loss, take_profit are empty
- risk_reward may show the failed ratio when available
- buy_probability and sell_probability must NOT default to 45/55 or 50/50
- if one side leads but is blocked by RR, preserve that directional bias
  in the probabilities/triggers and explain the actual RR failure

WAIT is not a probability state. It is a decision caused by a concrete
failure condition.

Return EXACTLY:

{
"symbol":"",
"timeframe":"",
"chart_type":"",
"market_structure":"",
"market_structure_simple":"",
"break_of_structure":"",
"change_of_character":"",
"liquidity_sweep":"",
"order_block":"",
"fair_value_gap":"",
"demand_supply":"",
"support_resistance":"",
"premium_discount":"",
"market_phase":"",
"market_sentiment":"",
"entry_quality":"",
"confirmation_quality":"",
"momentum_quality":"",
"risk_reward":"",
"institutional_score":0,
"decision":"",
"entry":"",
"stop_loss":"",
"take_profit":"",
"buy_probability":0,
"sell_probability":0,
"buy_trigger":"",
"sell_trigger":"",
"hold_time":"",
"confirmation_needed":"",
"reasoning":"",
"risk_warning":"This is not financial advice."
}

Never output markdown or text outside JSON.
'''
