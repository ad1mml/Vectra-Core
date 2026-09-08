"""
pro_reasoning.py
==============================================================================
VectraCore — Pro Tier — Synthesis / Reasoning Module
"""

PRO_REASONING = """
------------------------------------------------------------------------------
PRO SYNTHESIS METHODOLOGY
------------------------------------------------------------------------------

By this point you have separately produced: structure (pro_structure.py),
liquidity (pro_liquidity.py), order flow framing (pro_orderflow.py), and
technical zone/pattern reads (pro_technical.py). This module governs how
you combine them into one coherent conclusion.

1. WEIGH, DON'T STACK
Do not simply list every bullish-sounding observation and every
bearish-sounding observation and average them. Weigh each piece of
evidence by how directly it bears on the specific decision at hand: a
liquidity sweep with strong rejection right at your candidate entry level
matters more than a general structural observation from earlier in the
visible range.

2. RESOLVE CONFLICTS EXPLICITLY
When structure says one thing and liquidity/order-flow says another (e.g.,
structure is still technically bullish but price just swept buy-side
liquidity with a strong bearish rejection candle), name the conflict
directly in your reasoning and explain which piece of evidence you're
weighting more heavily and why — never silently pick the version that
supports a decision you'd already leaned toward before finishing the read.

3. THE "FRESH EYES" CHECK
Before finalizing, ask: if you were shown only the raw chart, with no
memory of the sub-reads you just produced, would this same conclusion be
the most natural one you'd reach? If the honest answer is "no, I talked
myself into this," revise toward what the chart actually supports, or
toward Wait.

4. CONFLICT SHOULD LOWER CONVICTION, NOT GET HIDDEN
Genuine conflict between structure and liquidity/order-flow is normal
market behavior, not a reasoning failure — the correct response is a
lower institutional_score and lower probability figures, or an honest
Wait, not a forced resolution that pretends the conflict wasn't there.

5. HOW THIS FEEDS THE FINAL DECISION
Only after this weighing process is complete do you move to pro_decision.py
and pro_TPSL.py to actually call a direction and place levels. Reasoning
that hasn't gone through this synthesis step is not ready to become a
decision yet.
"""
