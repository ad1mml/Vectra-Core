"""
Tests for the trade-validation layer.

These run the REAL functions from app.py (extracted from the source file, so
they do not need Flask, Gemini or the prompts/ folder) plus trade_validation.py.

Run from the project folder:
    python -m unittest tests.test_trade_validation -v
or:
    python tests/test_trade_validation.py
"""
import ast
import logging
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import trade_validation as tv  # noqa: E402

WANTED = {
    "_parse_price", "_calc_rr", "_downgrade_to_wait",
    "_sanity_check_levels", "_enforce_min_rr", "_reconcile_link_with_decision",
}


def _load_app_functions():
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    chunks = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in WANTED:
            chunks.append(ast.get_source_segment(src, node))
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "MIN_ACCEPTABLE_RR" in names or "MAX_ENTRY_DISTANCE_DAILY_ATR" in names:
                chunks.append(ast.get_source_segment(src, node))

    class _App:
        logger = logging.getLogger("test")

    ns = {"re": re, "tv": tv, "app": _App}
    exec("\n\n".join(chunks), ns)
    return ns


NS = _load_app_functions()
sanity = NS["_sanity_check_levels"]
enforce = NS["_enforce_min_rr"]


def run_pipeline(result, facts=None):
    """Same order as the /analyze-chart route."""
    result = sanity(result, facts)
    result = enforce(result)
    return result


def base(decision="Buy", entry="100.00", sl="99.00", tp="102.00", cp="100.00", **extra):
    r = {
        "symbol": "TEST", "decision": decision, "entry": entry, "stop_loss": sl,
        "take_profit": tp, "current_price": cp, "risk_reward": "9.99",
        "buy_probability": 60, "sell_probability": 40, "reasoning": "model text",
    }
    r.update(extra)
    return r


class GeometryTests(unittest.TestCase):
    def test_valid_buy(self):
        g = tv.trade_geometry("Buy", 100, 99, 102)
        self.assertTrue(g["ok"])
        self.assertAlmostEqual(g["rr"], 2.0)

    def test_valid_sell(self):
        g = tv.trade_geometry("Sell", 100, 101, 98)
        self.assertTrue(g["ok"])
        self.assertAlmostEqual(g["rr"], 2.0)

    def test_buy_stop_wrong_side(self):
        g = tv.trade_geometry("Buy", 100, 101, 102)
        self.assertFalse(g["ok"])
        self.assertEqual(g["code"], tv.CODE_STOP_WRONG_SIDE)

    def test_buy_target_wrong_side(self):
        g = tv.trade_geometry("Buy", 100, 99, 99.5)
        self.assertEqual(g["code"], tv.CODE_TARGET_WRONG_SIDE)

    def test_sell_stop_wrong_side(self):
        g = tv.trade_geometry("Sell", 100, 99, 98)
        self.assertEqual(g["code"], tv.CODE_STOP_WRONG_SIDE)

    def test_sell_target_wrong_side(self):
        g = tv.trade_geometry("Sell", 100, 101, 101.5)
        self.assertEqual(g["code"], tv.CODE_TARGET_WRONG_SIDE)

    def test_zero_risk(self):
        g = tv.trade_geometry("Buy", 100, 100, 102)
        self.assertEqual(g["code"], tv.CODE_ZERO_RISK)

    def test_unparseable(self):
        self.assertEqual(tv.trade_geometry("Buy", "abc", 99, 102)["code"], tv.CODE_UNPARSEABLE)
        self.assertEqual(tv.trade_geometry("Buy", None, 99, 102)["code"], tv.CODE_UNPARSEABLE)
        self.assertEqual(tv.trade_geometry("Wait", 100, 99, 102)["code"], tv.CODE_UNPARSEABLE)

    def test_price_formats(self):
        self.assertEqual(tv.parse_price("1,245.50"), 1245.5)
        self.assertEqual(tv.parse_price("$1.2450"), 1.245)
        self.assertIsNone(tv.parse_price(""))
        self.assertIsNone(tv.parse_price(True))

    def test_small_forex_precision(self):
        # 5-decimal forex numbers must keep their precision.
        g = tv.trade_geometry("Buy", "1.08250", "1.08150", "1.08550")
        self.assertTrue(g["ok"])
        self.assertAlmostEqual(g["rr"], 3.0, places=6)


class RRQualityTests(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(tv.rr_quality(0.9), "below_min")
        self.assertEqual(tv.rr_quality(1.0), "acceptable")
        self.assertEqual(tv.rr_quality(1.49), "acceptable")
        self.assertEqual(tv.rr_quality(1.5), "preferred")
        self.assertIsNone(tv.rr_quality(None))


class EntryClassificationTests(unittest.TestCase):
    def test_market(self):
        self.assertEqual(tv.classify_entry(base(entry="100.10")), "market")

    def test_pending(self):
        self.assertEqual(tv.classify_entry(base(entry="103.00")), "pending")

    def test_unknown_without_current_price(self):
        self.assertEqual(tv.classify_entry(base(cp="")), "unknown")

    def test_declared_pending_wins(self):
        self.assertEqual(tv.classify_entry(base(entry="100.00", order_type="Buy limit")), "pending")


class PipelineTests(unittest.TestCase):
    def test_good_market_buy_passes_and_rr_is_recomputed(self):
        r = run_pipeline(base(entry="100.00", sl="99.00", tp="102.50"))
        self.assertEqual(r["decision"], "Buy")
        self.assertEqual(r["risk_reward"], "2.50")   # model said 9.99, code overrides it
        self.assertEqual(r["rr_quality"], "preferred")
        self.assertEqual(r["entry_type"], "market")
        self.assertEqual(r["validation"]["status"], "passed")
        self.assertEqual(r["entry"], "100.00")       # levels never edited
        self.assertEqual(r["stop_loss"], "99.00")
        self.assertEqual(r["take_profit"], "102.50")

    def test_rr_between_floor_and_preferred_is_allowed_but_warned(self):
        r = run_pipeline(base(tp="101.20"))          # 1.2 R
        self.assertEqual(r["decision"], "Buy")
        self.assertEqual(r["rr_quality"], "acceptable")
        codes = [w["code"] for w in r["validation"]["warnings"]]
        self.assertIn(tv.CODE_RR_BELOW_PREFERRED, codes)

    def test_rr_below_floor_downgrades_and_clears_trade_numbers(self):
        r = run_pipeline(base(tp="100.80", take_profit_1="100.80"))   # 0.8 R
        self.assertEqual(r["decision"], "Wait")
        self.assertEqual(r["entry"], "")
        self.assertEqual(r["take_profit"], "")
        self.assertEqual(r["risk_reward"], "")        # bug fix: used to survive a downgrade
        self.assertEqual(r["take_profit_1"], "")      # bug fix: VIP ladder used to survive
        self.assertEqual(r["validation"]["status"], "changed")
        self.assertEqual(r["validation"]["changes"][0]["code"], tv.CODE_RR_BELOW_MIN)
        self.assertEqual(r["validation"]["original"]["decision"], "Buy")
        self.assertEqual(r["validation"]["original"]["take_profit"], "100.80")
        self.assertIn("0.80", r["reasoning"])         # explanation matches the downgrade

    def test_wrong_side_stop_buy(self):
        r = run_pipeline(base(sl="101.00"))
        self.assertEqual(r["decision"], "Wait")
        self.assertEqual(r["validation"]["changes"][0]["code"], tv.CODE_STOP_WRONG_SIDE)

    def test_wrong_side_target_sell(self):
        r = run_pipeline(base(decision="Sell", sl="101.00", tp="101.50"))
        self.assertEqual(r["decision"], "Wait")
        self.assertEqual(r["validation"]["changes"][0]["code"], tv.CODE_TARGET_WRONG_SIDE)

    def test_zero_risk(self):
        r = run_pipeline(base(sl="100.00"))
        self.assertEqual(r["decision"], "Wait")
        self.assertEqual(r["validation"]["changes"][0]["code"], tv.CODE_ZERO_RISK)

    def test_missing_levels_on_buy_is_wait(self):
        r = run_pipeline(base(sl=""))
        self.assertEqual(r["decision"], "Wait")
        self.assertEqual(r["validation"]["changes"][0]["code"], tv.CODE_UNPARSEABLE)

    def test_far_entry_becomes_pending_wait_with_levels_kept(self):
        # entry 3% away from current price, good R:R -> pending idea, not a market Buy
        r = run_pipeline(base(entry="97.00", sl="96.00", tp="100.00", cp="100.00"))
        self.assertEqual(r["decision"], "Wait")
        self.assertEqual(r["entry_type"], "pending")
        self.assertEqual(r["pending_setup"]["entry"], "97.00")
        self.assertEqual(r["pending_setup"]["rr"], "3.00")
        self.assertEqual(r["validation"]["changes"][0]["code"], tv.CODE_ENTRY_FAR_PENDING)
        self.assertIn("pending", r["buy_trigger"].lower() if "buy_trigger" in r else r["reasoning"].lower())

    def test_far_entry_with_declared_pending_is_not_downgraded(self):
        r = run_pipeline(base(entry="97.00", sl="96.00", tp="100.00", order_type="Buy limit"))
        self.assertEqual(r["decision"], "Buy")
        self.assertEqual(r["entry_type"], "pending")

    def test_far_entry_with_bad_rr_is_not_offered_as_pending(self):
        r = run_pipeline(base(entry="97.00", sl="96.00", tp="97.50", cp="100.00"))  # 0.5 R
        self.assertEqual(r["decision"], "Wait")
        self.assertNotIn("pending_setup", r)
        self.assertEqual(r["validation"]["changes"][0]["code"], tv.CODE_RR_BELOW_MIN)

    def test_missing_current_price_warns_but_does_not_block(self):
        r = run_pipeline(base(cp="", tp="102.00"))
        self.assertEqual(r["decision"], "Buy")
        codes = [w["code"] for w in r["validation"]["warnings"]]
        self.assertIn(tv.CODE_CURRENT_PRICE_MISSING, codes)

    def test_wait_passes_through_untouched(self):
        r = base(decision="Wait", entry="", sl="", tp="")
        before = dict(r)
        r = run_pipeline(r)
        self.assertEqual(r, before)

    def test_unusually_high_rr_warns(self):
        r = run_pipeline(base(tp="110.00"))           # 10 R
        self.assertEqual(r["decision"], "Buy")
        codes = [w["code"] for w in r["validation"]["warnings"]]
        self.assertIn(tv.CODE_RR_HIGH_CHECK_TARGET, codes)

    def test_live_price_mismatch_with_facts(self):
        facts = {"1day": {"price": 200.0, "atr": 2.0, "trend": "bullish"}}
        r = run_pipeline(base(), facts)               # levels ~100 vs live 200, limit 5*2=10
        self.assertEqual(r["decision"], "Wait")
        self.assertEqual(r["validation"]["changes"][0]["code"], tv.CODE_PRICE_FAR_FROM_LIVE)

    def test_htf_conflict_is_warning_only(self):
        facts = {"1day": {"price": 100.0, "atr": 2.0, "trend": "bearish (lower highs)"}}
        r = run_pipeline(base(), facts)
        self.assertEqual(r["decision"], "Buy")
        self.assertIn("counter-trend", r["context_warning"])

    def test_sell_direction_rr(self):
        r = run_pipeline(base(decision="Sell", entry="100.00", sl="101.00", tp="98.00"))
        self.assertEqual(r["decision"], "Sell")
        self.assertEqual(r["risk_reward"], "2.00")

    def test_non_dict_input(self):
        self.assertEqual(sanity("x"), "x")
        self.assertEqual(enforce("x"), "x")


class MinFloorConfigTests(unittest.TestCase):
    def test_floor_is_read_from_trade_validation(self):
        self.assertEqual(NS["MIN_ACCEPTABLE_RR"], tv.MIN_ACCEPTABLE_RR)
        self.assertEqual(tv.MIN_ACCEPTABLE_RR, 1.0)   # default unchanged unless .env overrides


if __name__ == "__main__":
    unittest.main(verbosity=2)
