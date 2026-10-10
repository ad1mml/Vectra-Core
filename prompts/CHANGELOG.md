# VectraCore prompts — liquidity rebuild

## Method
Every tier now builds its analysis from liquidity: buy-side / sell-side pools (HTF and LTF), the draw on liquidity, sweep with rejection, confirmation (displacement + CHOCH/MSS), reaction zone (OB / FVG / supply-demand), stop beyond the swept extreme, target at the next unswept pool. Structure, supply/demand, FVG, fibonacci (premium/discount, OTE) and momentum are supporting tools. Support/resistance is banned as a trade rationale and as trigger language (L6 in liquidity_core.py).

## New
- `liquidity_core.py` — shared playbook (L1–L9) imported by Default, Pro and VIP right after the decision spine. Also holds `LIQUIDITY_FOLLOWUP` for follow-up mode.

## Rewritten
- `default_prompt.py` — liquidity-led Default tier (same JSON keys).
- `pro_liquidity.py`, `vip_liquidity.py` — full liquidity depth (map, draw, external/internal, sweep quality, confirmation, HTF/LTF alignment, regime/news addenda for VIP).

## Edited (small, targeted)
- `pro_prompt.py`, `vip_prompt.py` — include LIQUIDITY_CORE.
- `pro_identity.py`, `vip_identity.py` — method statement.
- `pro_reasoning.py`, `vip_reasoning.py` — liquidity-first synthesis; level-only thesis resolves to Wait.
- `pro_technical.py`, `vip_technical.py` — S/R precision replaced by liquidity pool/zone precision; horizontal patterns read as liquidity formations.
- `pro_structure.py` — range edges read as pools.
- `pro_score.py` — liquidity-setup inputs for institutional_score.
- `pro_coach.py`, `vip_coach.py` — "what am I looking for?" answered in liquidity terms.
- `pro_json.py`, `vip_json.py` — field notes: `support_resistance` key kept for backend compatibility but now carries the liquidity map.
- `followup_prompt.py` — follow-ups answer in liquidity language.
- `memory_summarizer.py` — preserves the liquidity read (pools, status, draw, zone, target).

## Untouched (byte-identical)
decision_spine.py, pro/vip _decision, _risk, _TPSL, _rules, _execution, _validator, _self_review, and all other modules not listed above.

## Notes
- JSON schemas: identical keys in all tiers. `support_resistance` is a legacy name for the liquidity map; renaming it later requires a matching change in app.py/frontend.
- Entry rules are unchanged: a Buy/Sell needs entry near current_price; if price has not swept the pool or has not returned to the reaction zone, the result is Wait with the liquidity sequence in buy_trigger/sell_trigger.
- Assembled prompt sizes (chars): Default ~47k, Pro ~81k, VIP ~86k.
