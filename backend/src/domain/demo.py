"""澄浦 2 号线的可复现观测台账。"""

from datetime import date, timedelta
from math import exp
from random import Random

from .spec import SPEC


_INTERSECTIONS = (
    ("港湾路", "货栈街口", "混行"),
    ("港湾路", "渡口街口", "混行"),
    ("科创大道", "智造街口", "独立通行"),
    ("科创大道", "东环街口", "独立通行"),
)


def _poisson(rng, mean):
    limit = exp(-mean)
    product = rng.random()
    count = 0
    while product > limit:
        product *= rng.random()
        count += 1
    return count


def demo_rows():
    rng = Random(261160)
    rows = []
    for day in range(14):
        stamp = (date(2026, 11, 7) + timedelta(days=day)).isoformat()
        for road, intersection, track in _INTERSECTIONS:
            for shift in ("平峰", "高峰"):
                peak = shift == "高峰"
                exposure = (38 if peak else 20) + rng.randrange(13)
                rate = 0.035 * exp(0.9 * peak + 1.05 * (track == "混行"))
                rows.append({
                    "date": stamp, "road": road, "intersection": intersection,
                    "shift": shift, "track": track, "exposure": exposure,
                    "count": _poisson(rng, exposure * rate),
                })
    return rows


def grouped_rows():
    """Same observations as :func:`demo_rows`, reported by both source systems.

    Each windowed row becomes one station group (window count 1) with a matching
    汇总包 and 独立班报 record, so the joint trial reconciles cleanly and fits
    identically to the windowed data.
    """
    rows = []
    for row in demo_rows():
        for system in SPEC["grouped_sources"]:
            rows.append({
                "date": row["date"], "road": row["road"], "intersection": row["intersection"],
                "shift": row["shift"], "track": row["track"], "system": system,
                "windows": 1, "exposure": row["exposure"], "count": row["count"],
            })
    return rows
