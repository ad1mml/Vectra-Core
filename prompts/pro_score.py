"""
pro_score.py
==============================================================================
VectraCore — Pro Tier — Institutional Score Module
"""

PRO_SCORE = """
------------------------------------------------------------------------------
PRO institutional_score METHODOLOGY
------------------------------------------------------------------------------

institutional_score is a 0-100 rating of SETUP QUALITY, independent of
direction and independent of whether you ultimately call Buy, Sell, or
Wait. A clean, high-confluence Sell setup scores exactly as high as an
equally clean Buy setup. A messy chart scores low even if you're still
willing to lean a direction.

WEIGH THESE INPUTS (roughly, not as a rigid formula — use judgment):
- Structural clarity (pro_structure.py): is the trend/range read clean and
  well-supported, or ambiguous?
- Liquidity/order-flow quality (pro_liquidity.py, pro_orderflow.py): is
  there a strong, confluent, well-characterized liquidity signature, or is
  it thin/isolated/absent?
- Confluence between structure, liquidity, and technical zones
  (pro_technical.py): do multiple independent forms of evidence agree, or
  is the read built on one thin thread?
- Invalidation clarity (pro_risk.py): is there one obvious, specific
  structural point that would prove the read wrong, or is the invalidation
  itself fuzzy?
- Reliance on an "obvious" retail level versus genuine structural footprint
  (pro_orderflow.py point 1): heavy reliance on an obvious level alone
  should cap the score lower even if other inputs look clean.

LIQUIDITY-SETUP INPUTS (part of the confluence and liquidity weighing above):
- Draw clarity: is there one clearly justified unswept pool price is being
  drawn to, or do two pools compete?
- Sweep quality: strong rejection from an external or stacked pool scores
  higher than a grinding reclaim or an internal-pool sweep.
- Confirmation: displacement plus CHOCH/MSS after the sweep is required for a
  high score; a sweep without it caps the score.
- HTF/LTF alignment: an LTF sweep opposite the HTF draw scores higher than
  one against it.
- Location: entry zone in discount (longs) / premium (shorts) supports the
  score.
- Clean target: an unswept opposing pool with room to travel supports the
  score; a nearby already-swept or taken target does not.

CALIBRATION GUIDANCE:
- 80-100: multiple forms of independently-confirming evidence, clear
  invalidation, low reliance on obvious/telegraphed levels. Genuinely rare.
- 50-79: solid, tradeable evidence with at least one real weakness or
  point of ambiguity — the normal range for a legitimate but imperfect
  setup.
- 20-49: thin, conflicted, or heavily dependent on a single weak signal.
  Still worth reporting honestly, especially alongside a Wait decision.
- 0-19: little to no coherent structural case. Should almost always
  accompany a Wait decision.

Never let this score be inflated just because a Buy/Sell decision was
made — plenty of legitimate Buy/Sell calls sit in the 50-79 range, and
that is an honest, useful number, not a disappointing one. Never let a
Wait decision automatically drag the score to 0 either — a genuinely
close-but-not-quite setup might reasonably score in the 40s-50s while
still correctly resulting in Wait for other reasons (e.g., a failed
reward-to-risk check, or a level not yet reached).
"""
