"""Lightweight domain self-checks that do not require a database.

Run with ``python -m scripts.selfcheck`` from ``backend/``.  These pin the
joint-trial contract: grouped statistics reconcile against the independent
duty report, stop the run on any gap or disagreement, and reproduce the
windowed fit exactly when the two systems agree.
"""
from src.domain.analysis import _reconcile, analyze, detect_format, validate_grouped_rows
from src.domain.demo import demo_rows, grouped_rows
from src.domain.spec import SPEC

PARAMS = {field["key"]: field["default"] for field in SPEC["params"]}


def main():
    assert detect_format(demo_rows()) == "windows"
    assert detect_format(grouped_rows()) == "grouped"

    windowed = analyze(demo_rows(), PARAMS)
    grouped = analyze(grouped_rows(), PARAMS)
    assert windowed["metrics"] == grouped["metrics"], "grouped metrics drifted from windowed"
    coefficient_rows = lambda result: [t for t in result["tables"] if t["title"] == "模型系数与发生率倍数"][0]["rows"]
    assert coefficient_rows(windowed) == coefficient_rows(grouped), "grouped coefficients drifted"

    days = sorted({row["date"] for row in demo_rows()})
    cutoff = days[-PARAMS["holdout_days"]]
    assert all(row["date"] < cutoff for row in demo_rows()[: len(demo_rows()) - 3 * 8]), "holdout split is not by whole day"

    _, detail = _reconcile(validate_grouped_rows(grouped_rows()))
    assert detail and all(item["reconcile"] == "一致" for item in detail), "demo groups should reconcile"

    stopped = {"missing": 0, "mismatch": 0}
    for kind, mutate in (
        ("missing", lambda rows: [r for r in rows if not (r["system"] == "汇总包" and r["date"] == "2026-11-07"
                                                          and r["intersection"] == "货栈街口" and r["shift"] == "高峰")]),
        ("mismatch", lambda rows: [dict(r, count=r["count"] + 1) if r["system"] == "独立班报" and r["date"] == "2026-11-20"
                                   else r for r in rows]),
    ):
        try:
            analyze(mutate(grouped_rows()), PARAMS)
        except ValueError as error:
            assert "停算" in str(error), error
            stopped[kind] = 1
    assert all(stopped.values()), f"stop conditions not enforced: {stopped}"
    print("selfcheck ok", {"reconciled_groups": len(detail), **stopped})


if __name__ == "__main__":
    main()
