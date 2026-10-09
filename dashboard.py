"""VectraCore LIVE admin dashboard: every decision, grouped by symbol, with win rate.

Nothing to feed it. It reads your live files on every refresh:
  data/predictions.jsonl      written by benchmark.py the moment a prediction is made
  data/benchmark_report.json  written by evaluate_predictions.py (did SL or TP hit first?)

It also keeps the report fresh by itself: a background thread re-runs
evaluate_predictions.py every N minutes, but only when there are new predictions
or open (pending) trades, so it does not waste Twelve Data requests.

Predictions logged since the last evaluation show up straight away as
"awaiting" and turn into win/loss/pending after the next automatic check.

Install (in app.py, after `app` and `_require_admin` exist):
    from dashboard import register_dashboard
    register_dashboard(app, _require_admin, os.path.dirname(os.path.abspath(__file__)))
Keep dashboard.html in the same folder as dashboard.py.

Settings (.env or environment, all optional):
    DASHBOARD_AUTO_EVAL_MINUTES   default 30. 0 turns the automatic check off.
    DASHBOARD_EVAL_DAYS           default 30. Lookback window for the evaluator.

Pages (admin-only, same session login as /admin/feedback):
    GET  /admin/dashboard                 the live dashboard
    GET  /admin/dashboard/data            the numbers as JSON
    GET  /admin/dashboard/decisions.csv   every decision as CSV
    POST /admin/dashboard/refresh         check against the market right now
    GET  /admin/dashboard/status          is an evaluation running?
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import subprocess
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

from flask import Blueprint, Response, jsonify, request

import evaluate_predictions as ev

bp = Blueprint("vectra_dashboard", __name__)

_BASE = Path(__file__).resolve().parent
_REQUIRE_ADMIN = None
_refresh_lock = threading.Lock()
_refresh = {"running": False, "started": None, "finished": None, "ok": None, "message": ""}
_auto = {"enabled": False, "interval_minutes": 0, "next_run": None, "days": 30, "started": False}
MIN_REFRESH_GAP = 60  # seconds between manual evaluator runs (protects the Twelve Data quota)


# --------------------------------------------------------------------------- #
# Aggregation (pure functions, no Flask)
# --------------------------------------------------------------------------- #
def wilson(wins: int, n: int):
    """95% confidence interval for a win rate. Small samples give wide ranges."""
    if n <= 0:
        return None, None
    z = 1.96
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return round(100 * (centre - half), 1), round(100 * (centre + half), 1)


def stats(items):
    out = {"decisions": len(items), "wins": 0, "losses": 0, "pending": 0, "awaiting": 0,
           "ambiguous": 0, "no_trade": 0, "gate_blocked": 0, "not_evaluable": 0,
           "insufficient_data": 0, "errors": 0}
    r_values = []
    for it in items:
        o = it.get("outcome")
        if o == "win":
            out["wins"] += 1
        elif o == "loss":
            out["losses"] += 1
        elif o == "error":
            out["errors"] += 1
        elif o in out:
            out[o] += 1
        if it.get("gate_blocked"):
            out["gate_blocked"] += 1
        if o in ("win", "loss") and isinstance(it.get("r_multiple"), (int, float)):
            r_values.append(float(it["r_multiple"]))
    done = out["wins"] + out["losses"]
    lo, hi = wilson(out["wins"], done)
    out.update({
        "completed": done,
        "win_rate": round(100 * out["wins"] / done, 1) if done else None,
        "win_rate_low": lo,
        "win_rate_high": hi,
        "total_r": round(sum(r_values), 2) if r_values else 0.0,
        "avg_r": round(sum(r_values) / len(r_values), 2) if r_values else None,
    })
    return out


def group(items, key):
    buckets = defaultdict(list)
    for it in items:
        buckets[it.get(key) or "Unknown"].append(it)
    rows = [{"name": name, **stats(v)} for name, v in buckets.items()]
    rows.sort(key=lambda r: (-r["completed"], -r["decisions"], r["name"]))
    return rows


def _num(value):
    return ev.parse_number(value)


def _make_decision(item, record):
    """One dashboard row from an evaluator item plus its matching log record."""
    record = record or {}
    pred = record.get("prediction") if isinstance(record.get("prediction"), dict) else {}
    have = bool(record)
    direction = ev.normalize_decision(record, pred) if have else "unknown"
    entry = _num(ev.get_field(record, pred, "entry", "entry_price")) if have else None
    sl = _num(ev.get_field(record, pred, "stop_loss", "sl")) if have else None
    tp = _num(ev.get_field(record, pred, "take_profit", "take_profit_1", "target", "tp")) if have else None
    if item.get("gate_blocked"):
        proposed = item.get("proposed") or {}
        direction = "wait (gate blocked)"
        entry = _num(proposed.get("entry")) if entry is None else entry
        sl = _num(proposed.get("stop_loss")) if sl is None else sl
        tp = _num(proposed.get("take_profit") or proposed.get("take_profit_1")) if tp is None else tp
    return {
        "line": item.get("line"),
        "timestamp": item.get("timestamp"),
        "plan": item.get("plan"),
        "symbol": item.get("symbol") or "Unknown",
        "timeframe": item.get("timeframe") or "unknown",
        "direction": direction,
        "entry": entry, "stop_loss": sl, "take_profit": tp,
        "outcome": item.get("outcome"),
        "r_multiple": item.get("r_multiple"),
        "gate_blocked": bool(item.get("gate_blocked")),
        "closed_at": item.get("candle_time"),
        "reason": item.get("reason", ""),
    }


def _awaiting_item(line, record):
    """Describe a log record the evaluator has not seen yet."""
    pred = record.get("prediction") if isinstance(record.get("prediction"), dict) else {}
    ts = ev.parse_timestamp(record.get("timestamp"))
    symbol = ev.normalize_symbol(ev.get_field(record, pred, "symbol", "pair", "asset", "market"))
    raw_tf = ev.get_field(record, pred, "timeframe", "interval")
    timeframe = None
    if raw_tf is not None:
        timeframe = ev.TIMEFRAME_MAP.get(str(raw_tf).strip().lower()) or ev.TIMEFRAME_MAP.get(str(raw_tf).strip())
    item = {
        "line": line,
        "timestamp": ts.isoformat() if ts else record.get("timestamp"),
        "plan": str(record.get("plan") or "unknown").strip().lower(),
        "symbol": symbol,
        "timeframe": timeframe or str(raw_tf or "unknown"),
    }
    decision = ev.normalize_decision(record, pred)
    if not ts:
        item.update(outcome="not_evaluable", reason="missing or invalid prediction timestamp")
    elif decision == "wait":
        item.update(outcome="no_trade", reason="explicit Hold/Wait/no-trade decision")
        meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
        pre = meta.get("pre_gate") if isinstance(meta.get("pre_gate"), dict) else {}
        if str(pre.get("decision") or "").strip().lower().startswith(("buy", "sell", "long", "short")):
            item.update(gate_blocked=True, proposed={k: pre.get(k) for k in
                        ("entry", "stop_loss", "take_profit", "take_profit_1")},
                        reason=f"AI proposed {pre.get('decision')}; blocked by a safety gate")
    elif decision == "unknown":
        item.update(outcome="not_evaluable", reason="missing or unrecognized Buy/Sell decision")
    else:
        item.update(outcome="awaiting", reason="Logged after the last evaluation. Checked automatically on the next run.")
    return item


def build_data(report_file: Path, log_file: Path):
    report, log = {}, {}
    if report_file.exists():
        try:
            report = json.loads(report_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {}
    if log_file.exists():
        try:
            rows, _ = ev.load_records(log_file)
            log = dict(rows)
        except OSError:
            pass
    if not report and not log:
        return {"ready": False, "auto": auto_info(),
                "message": "No predictions logged yet. They appear here as soon as the app logs one."}

    decisions, seen = [], set()
    for item in report.get("predictions", []):
        seen.add(item.get("line"))
        record = log.get(item.get("line"))
        # Join only if the log line is still the same record the report saw.
        if record is not None:
            ts = ev.parse_timestamp(record.get("timestamp"))
            if not ts or ts.isoformat() != item.get("timestamp"):
                record = None
        decisions.append(_make_decision(item, record))

    skipped = set(report.get("excluded_log_lines") or [])
    for line, record in sorted(log.items()):
        if line in seen or line in skipped:
            continue
        decisions.append(_make_decision(_awaiting_item(line, record), record))

    decisions.sort(key=lambda d: d["timestamp"] or "", reverse=True)

    equity, running = [], 0.0
    for d in sorted((d for d in decisions if d["outcome"] in ("win", "loss")),
                    key=lambda d: d["timestamp"] or ""):
        running += float(d["r_multiple"] or 0)
        equity.append({"t": d["timestamp"], "r": round(running, 2)})

    pairs = defaultdict(list)
    for d in decisions:
        if d["direction"] in ("buy", "sell"):
            pairs[(d["symbol"], d["direction"])].append(d)
    by_symbol_direction = [{"name": f"{s} / {dr}", **stats(v)} for (s, dr), v in pairs.items()]
    by_symbol_direction.sort(key=lambda r: (-r["completed"], r["name"]))

    return {
        "ready": True,
        "live": True,
        "generated_at": report.get("generated_at"),
        "lookback_days": report.get("lookback_days"),
        "records_read": len(log) or report.get("records_read"),
        "malformed_lines": report.get("malformed_lines"),
        "overall": stats(decisions),
        "by_symbol": group(decisions, "symbol"),
        "by_timeframe": group(decisions, "timeframe"),
        "by_direction": group(decisions, "direction"),
        "by_plan": group(decisions, "plan"),
        "by_symbol_direction": by_symbol_direction,
        "equity": equity,
        "decisions": decisions,
        "note": report.get("note"),
        "auto": auto_info(),
    }


# --------------------------------------------------------------------------- #
# Evaluation runner (manual button + automatic background check)
# --------------------------------------------------------------------------- #
def _files():
    return _BASE / "data" / "benchmark_report.json", _BASE / "data" / "predictions.jsonl"


def _acquire_file_lock():
    """Cross-process lock so several gunicorn workers never evaluate at once."""
    (_BASE / "data").mkdir(parents=True, exist_ok=True)
    try:
        import fcntl
    except ImportError:          # Windows: fall back to the in-process lock only
        return object()
    handle = open(_BASE / "data" / ".evaluate.lock", "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def _release_file_lock(handle):
    try:
        if hasattr(handle, "close"):
            handle.close()      # closing releases the flock
    except OSError:
        pass


def _lock_busy() -> bool:
    handle = _acquire_file_lock()
    if handle is None:
        return True
    _release_file_lock(handle)
    return False


def _evaluate(days: int) -> bool:
    """Run evaluate_predictions.py once. Returns False if another run holds the lock."""
    handle = _acquire_file_lock()
    if handle is None:
        return False
    with _refresh_lock:
        _refresh.update(running=True, started=time.time(), ok=None, message="")
    try:
        proc = subprocess.run(
            [sys.executable, str(_BASE / "evaluate_predictions.py"), "--days", str(days)],
            cwd=str(_BASE), capture_output=True, text=True, timeout=900)
        ok = proc.returncode == 0
        msg = (proc.stdout if ok else (proc.stderr or proc.stdout)).strip()[-600:]
    except Exception as exc:    # timeout, missing interpreter, ...
        ok, msg = False, str(exc)[:300]
    finally:
        _release_file_lock(handle)
    with _refresh_lock:
        _refresh.update(running=False, finished=time.time(), ok=ok, message=msg)
    return True


def _needs_eval() -> bool:
    """New predictions in the log, or open trades that could have hit SL/TP by now."""
    report_file, log_file = _files()
    if not log_file.exists():
        return False
    if not report_file.exists():
        return True
    try:
        if log_file.stat().st_mtime > report_file.stat().st_mtime:
            return True
        report = json.loads(report_file.read_text(encoding="utf-8"))
        return any(p.get("outcome") == "pending" for p in report.get("predictions", []))
    except (OSError, json.JSONDecodeError):
        return True


def _auto_loop():
    time.sleep(10)
    while True:
        minutes = _auto["interval_minutes"]
        try:
            if not _refresh["running"] and _needs_eval():
                _evaluate(_auto["days"])
        except Exception:
            pass
        _auto["next_run"] = time.time() + minutes * 60
        time.sleep(minutes * 60)


def auto_info():
    with _refresh_lock:
        info = dict(_refresh)
    return {
        "enabled": _auto["enabled"],
        "interval_minutes": _auto["interval_minutes"],
        "next_run": _auto["next_run"],
        "running": bool(info["running"]) or _lock_busy(),
        "last_ok": info["ok"],
        "last_message": info["message"] if info["ok"] is False else "",
        "last_finished": info["finished"],
    }


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
def _guard():
    return _REQUIRE_ADMIN() if _REQUIRE_ADMIN else None


@bp.route("/admin/dashboard")
def dashboard_page():
    err = _guard()
    if err:
        return err
    html_file = Path(__file__).with_name("dashboard.html")
    if not html_file.exists():
        return Response("dashboard.html must sit next to dashboard.py", status=500, mimetype="text/plain")
    resp = Response(html_file.read_text(encoding="utf-8"), mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bp.route("/admin/dashboard/data")
def dashboard_data():
    err = _guard()
    if err:
        return err
    resp = jsonify(build_data(*_files()))
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bp.route("/admin/dashboard/decisions.csv")
def dashboard_csv():
    err = _guard()
    if err:
        return err
    data = build_data(*_files())
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["timestamp", "plan", "symbol", "timeframe", "direction", "entry", "stop_loss",
            "take_profit", "outcome", "r_multiple", "closed_at", "reason"]
    w.writerow(cols)
    for d in data.get("decisions", []):
        row = []
        for c in cols:
            v = d.get(c)
            if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
                v = "'" + v     # neutralise spreadsheet formula injection from AI-written text
            row.append("" if v is None else v)
        w.writerow(row)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=vectracore_decisions.csv"})


@bp.route("/admin/dashboard/refresh", methods=["POST"])
def dashboard_refresh():
    err = _guard()
    if err:
        return err
    # A custom header forces a CORS preflight, so other websites cannot trigger this.
    if request.headers.get("X-Requested-With") != "vectra-dashboard":
        return jsonify({"error": "Missing header."}), 400
    try:
        days = int((request.get_json(silent=True) or {}).get("days", _auto["days"]))
    except (TypeError, ValueError):
        days = _auto["days"]
    days = max(1, min(ev.MAX_DAYS, days))
    with _refresh_lock:
        if _refresh["running"] or _lock_busy():
            return jsonify({"error": "An evaluation is already running."}), 409
        if _refresh["finished"] and time.time() - _refresh["finished"] < MIN_REFRESH_GAP:
            return jsonify({"error": f"Please wait {MIN_REFRESH_GAP}s between evaluations."}), 429
    threading.Thread(target=_evaluate, args=(days,), daemon=True).start()
    return jsonify({"started": True, "days": days}), 202


@bp.route("/admin/dashboard/status")
def dashboard_status():
    err = _guard()
    if err:
        return err
    return jsonify(auto_info())


def register_dashboard(app, require_admin, base_dir=None):
    global _REQUIRE_ADMIN, _BASE
    _REQUIRE_ADMIN = require_admin
    if base_dir:
        _BASE = Path(base_dir)
    try:
        minutes = max(0, int(os.environ.get("DASHBOARD_AUTO_EVAL_MINUTES", "30")))
    except ValueError:
        minutes = 30
    try:
        days = max(1, min(ev.MAX_DAYS, int(os.environ.get("DASHBOARD_EVAL_DAYS", "30"))))
    except ValueError:
        days = 30
    _auto.update(enabled=minutes > 0, interval_minutes=minutes, days=days)
    app.register_blueprint(bp)
    if minutes > 0 and not _auto["started"]:
        _auto["started"] = True
        _auto["next_run"] = time.time() + 10
        threading.Thread(target=_auto_loop, daemon=True, name="dashboard-auto-eval").start()
