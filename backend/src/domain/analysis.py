"""Fit a ridge Poisson rate model and review chronological holdout windows.

Two input formats are supported:

* ``windows`` - one row per observed date/road/intersection/shift/track window.
* ``grouped`` - the joint trial format: per station group, the aggregate
  (:mod:`汇总包`) and the independent duty report (:mod:`独立班报`) each report
  window count, exposure and confirmed blocks.  Both systems are reconciled
  before any fitting; a missing group or any disagreement stops the run.
"""

from collections import defaultdict
from datetime import date
from math import exp, fsum, isclose, log, log1p, ulp

from .spec import SPEC


_MAX_ROWS = 5000
_RIDGE = 1.0
_FEATURES = ((0, 0), (0, 1), (1, 0), (1, 1))
_GROUP_KEYS = ("date", "road", "intersection", "shift", "track")
_SUMMARY = "汇总包"
_STANDALONE = "独立班报"


def _validate_field(field, value):
    kind = field["type"]
    label = field["label"]
    if kind in {"int", "number"}:
        types = (int,) if kind == "int" else (int, float)
        if type(value) not in types or not field["min"] <= value <= field["max"]:
            unit = "整数" if kind == "int" else "数值"
            raise ValueError(f"{label}须为 {field['min']} 至 {field['max']} 之间的{unit}")
    elif kind == "date":
        try:
            if not isinstance(value, str) or len(value) != 10 or date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except ValueError:
            raise ValueError(f"{label}须为有效的 YYYY-MM-DD 日期") from None
    elif kind == "select":
        if value not in field["options"]:
            raise ValueError(f"{label}须为{'、'.join(field['options'])}之一")
    elif not isinstance(value, str) or len(value) > field["max_length"] or not value.strip():
        raise ValueError(f"{label}须为非空文本，最多 {field['max_length']} 字符")
    return value.strip() if kind == "string" else value


def detect_format(rows):
    """Infer the dataset format from its first record."""
    if not isinstance(rows, (list, tuple)) or not rows:
        return "windows"
    first = rows[0]
    keys = set(first) if isinstance(first, dict) else set()
    return "grouped" if {"system", "windows"} <= keys else "windows"


def validate_rows(rows):
    if not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= _MAX_ROWS:
        raise ValueError(f"观测台账须包含 1 至 {_MAX_ROWS} 行")
    readings = {}
    for index, row in enumerate(rows, start=1):
        try:
            if not isinstance(row, dict):
                raise ValueError("须为一条观测记录")
            clean = {field["key"]: _validate_field(field, row.get(field["key"])) for field in SPEC["fields"]}
            window = (clean["date"], clean["road"], clean["intersection"], clean["shift"])
            if window in readings:
                raise ValueError("日期、道路、路口与时段重复")
            readings[window] = clean
        except ValueError as error:
            raise ValueError(f"第 {index} 条观测 · {error}") from None
    return [readings[key] for key in sorted(readings)]


def validate_grouped_rows(rows):
    if not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= _MAX_ROWS:
        raise ValueError(f"分组统计台账须包含 1 至 {_MAX_ROWS} 行")
    readings = {}
    for index, row in enumerate(rows, start=1):
        try:
            if not isinstance(row, dict):
                raise ValueError("须为一条分组记录")
            clean = {field["key"]: _validate_field(field, row.get(field["key"])) for field in SPEC["grouped_fields"]}
            window = (*[clean[key] for key in _GROUP_KEYS], clean["system"])
            if window in readings:
                raise ValueError("日期、道路、路口、时段、通行方式与数据来源重复")
            readings[window] = clean
        except ValueError as error:
            raise ValueError(f"第 {index} 条分组 · {error}") from None
    return [readings[key] for key in sorted(readings)]


def _label(key):
    return f"{key[0]} {key[1]}·{key[2]} {key[3]}/{key[4]}"


_FIELD_LABELS = {"windows": "窗数", "exposure": "车次", "count": "阻断数"}


def _reconcile(rows):
    """Cross-check 汇总包 against 独立班报 for every station group.

    Each date/road/intersection/shift/track group must be reported by both
    systems with matching window counts, exposure and confirmed blocks.  Any
    missing group or mismatch raises so the worker stops before fitting.
    """
    paired = defaultdict(dict)
    for row in rows:
        key = tuple(row[name] for name in _GROUP_KEYS)
        paired[key][row["system"]] = row

    observations, detail, missing, mismatched = [], [], [], []
    for key in sorted(paired):
        pair = paired[key]
        summary, standalone = pair.get(_SUMMARY), pair.get(_STANDALONE)
        record = dict(zip(_GROUP_KEYS, key))
        record.update({
            "summary_windows": summary["windows"] if summary else None,
            "standalone_windows": standalone["windows"] if standalone else None,
            "summary_exposure": summary["exposure"] if summary else None,
            "standalone_exposure": standalone["exposure"] if standalone else None,
            "summary_count": summary["count"] if summary else None,
            "standalone_count": standalone["count"] if standalone else None,
        })
        if not summary or not standalone:
            absent = "、".join(name for name, item in ((_SUMMARY, summary), (_STANDALONE, standalone)) if not item)
            record["reconcile"] = f"缺{absent}"
            detail.append(record)
            missing.append(f"{_label(key)}（缺{absent}）")
            continue
        differ = [name for name in ("windows", "exposure", "count") if summary[name] != standalone[name]]
        if differ:
            record["reconcile"] = "不一致：" + "、".join(_FIELD_LABELS[name] for name in differ)
            detail.append(record)
            mismatched.append(f"{_label(key)}（{'、'.join(_FIELD_LABELS[name] for name in differ)}）")
            continue
        record["reconcile"] = "一致"
        detail.append(record)
        observations.append({
            **dict(zip(_GROUP_KEYS, key)),
            "windows": summary["windows"],
            "exposure": summary["exposure"],
            "count": summary["count"],
        })

    if missing or mismatched:
        parts = []
        if missing:
            parts.append(f"{len(missing)} 组缺少汇总包或独立班报")
        if mismatched:
            parts.append(f"{len(mismatched)} 组窗数、车次或阻断数不一致")
        examples = "；".join((missing + mismatched)[:4])
        raise ValueError("联合试算停算：" + "，".join(parts) + f"。示例：{examples}。请补齐分组或核对数值后重试。")
    return observations, detail


def _features(row):
    return (int(row["shift"] == "高峰"), int(row["track"] == "混行"))


def _profile(slopes, groups, total):
    """Profile out the intercept by matching the fitted training count total."""
    first, second = slopes
    log_weights = [log_exposure + first * peak + second * shared for peak, shared, log_exposure, _ in groups]
    center = max(log_weights)
    centered = [weight - center for weight in log_weights]
    weights = [exp(weight) for weight in centered]
    weight_sum = fsum(weights)
    dominant = log_weights.index(center)
    log_weight_sum = log1p(fsum(weight for index, weight in enumerate(weights) if index != dominant))
    probabilities = [weight / weight_sum for weight in weights]
    # This differs from the profile likelihood by a data-only constant. Center
    # before multiplying by counts to preserve precision under separation.
    objective = fsum(count * (log_weight_sum - weight)
                     for (_, _, _, count), weight in zip(groups, centered))
    objective += 0.5 * _RIDGE * (first * first + second * second)
    return objective, probabilities, center + log_weight_sum


def _fit(training):
    exposure = defaultdict(int)
    counts = defaultdict(int)
    for row in training:
        features = _features(row)
        exposure[features] += row["exposure"]
        counts[features] += row["count"]
    total = sum(counts.values())
    if not total:
        raise ValueError("训练期没有阻断事件，无法估计有限的截距。请补充观测或调整留出观测日数。")
    groups = [(peak, shared, log(exposure[peak, shared]), counts[peak, shared])
              for peak, shared in _FEATURES if (peak, shared) in exposure]
    observed_peak = sum(peak * count for peak, _, _, count in groups)
    observed_shared = sum(shared * count for _, shared, _, count in groups)
    slopes = (0.0, 0.0)
    for _ in range(100):
        objective, probabilities, normalizer = _profile(slopes, groups, total)
        mean_peak = fsum(p * group[0] for p, group in zip(probabilities, groups))
        mean_shared = fsum(p * group[1] for p, group in zip(probabilities, groups))
        mean_joint = fsum(p * group[0] * group[1] for p, group in zip(probabilities, groups))
        g_peak = total * mean_peak - observed_peak + _RIDGE * slopes[0]
        g_shared = total * mean_shared - observed_shared + _RIDGE * slopes[1]
        h_peak = total * mean_peak * (1 - mean_peak) + _RIDGE
        h_shared = total * mean_shared * (1 - mean_shared) + _RIDGE
        h_joint = total * (mean_joint - mean_peak * mean_shared)
        determinant = h_peak * h_shared - h_joint * h_joint
        step_peak = (h_shared * g_peak - h_joint * g_shared) / determinant
        step_shared = (h_peak * g_shared - h_joint * g_peak) / determinant
        step_size = max(abs(step_peak), abs(step_shared))
        if step_size <= 1e-8 * (1 + max(map(abs, slopes))):
            return (log(total) - normalizer, *slopes), total / sum(exposure.values()), set(exposure)

        # Small Newton steps can improve the score below objective rounding error.
        # For larger steps, backtrack on the profile objective.
        scale = 1.0
        descent = g_peak * step_peak + g_shared * step_shared
        for _ in range(40):
            candidate = (slopes[0] - scale * step_peak, slopes[1] - scale * step_shared)
            candidate_objective, _, _ = _profile(candidate, groups, total)
            rounding = 4 * ulp(objective)
            if step_size <= 1e-5 or candidate_objective <= objective - 1e-4 * scale * descent + rounding:
                slopes = candidate
                break
            scale *= 0.5
        else:
            break
    raise ValueError("阻断模型未在迭代上限内收敛，请核对训练期的车次和阻断次数。")


def _deviance(count, expected):
    if count == 0:
        return 2 * expected
    return max(0.0, 2 * (count * (log(count) - log(expected)) - count + expected))


def _planning(windows, keys, threshold):
    groups = defaultdict(list)
    for row in windows:
        groups[tuple(row[key] for key in keys)].append(row)
    plan = []
    for group, records in groups.items():
        exposure = sum(row["exposure"] for row in records)
        expected = fsum(row["predicted"] for row in records)
        rate = 100 * expected / exposure
        severity = sum(rate >= limit or isclose(rate, limit, rel_tol=1e-12)
                       for limit in (threshold, 2 * threshold))
        plan.append({
            **dict(zip(keys, group)), "exposure": exposure, "predicted": expected,
            "rate": rate, "severity": ("常规", "重点", "优先")[severity],
            "action": ("按常规频次抽查", "增排路口巡查", "优先复核放行相位与混行冲突")[severity],
        })
    return sorted(plan, key=lambda row: (-row["predicted"], -row["rate"], *(row[key] for key in keys)))


def _table(title, columns, rows):
    return {"title": title, "columns": [{"key": key, "label": label} for key, label in columns], "rows": rows}


_RECONCILE_COLUMNS = (
    ("date", "观测日期"), ("road", "道路"), ("intersection", "路口"),
    ("shift", "时段"), ("track", "通行方式"),
    ("summary_windows", "汇总包窗数"), ("standalone_windows", "班报窗数"),
    ("summary_exposure", "汇总包车次"), ("standalone_exposure", "班报车次"),
    ("summary_count", "汇总包阻断"), ("standalone_count", "班报阻断"),
    ("reconcile", "核对"),
)


def analyze(rows, normalized_params):
    fmt = detect_format(rows)
    if fmt == "grouped":
        observations, reconciliation = _reconcile(validate_grouped_rows(rows))
    else:
        observations = [{**row, "windows": 1} for row in validate_rows(rows)]
        reconciliation = None
    if set(normalized_params) - {field["key"] for field in SPEC["params"]}:
        raise ValueError("存在未知运行参数")
    params = {field["key"]: _validate_field(field, normalized_params.get(field["key"], field["default"]))
              for field in SPEC["params"]}
    days = sorted({row["date"] for row in observations})
    holdout_days = params["holdout_days"]
    if len(days) <= holdout_days:
        raise ValueError("留出观测日数须少于台账中的不同日期数，以保留训练数据。")
    cutoff = days[-holdout_days]
    # Split whole observation days first; only then merge the training groups.
    training = [row for row in observations if row["date"] < cutoff]
    holdout = [row for row in observations if row["date"] >= cutoff]
    coefficients, baseline_rate, seen = _fit(training)
    intercept, peak_coefficient, shared_coefficient = coefficients
    windows = []
    total_windows = 0
    unseen_windows = 0
    model_totals, baseline_totals = [], []
    for row in holdout:
        peak, shared = _features(row)
        log_mean = log(row["exposure"]) + intercept + peak_coefficient * peak + shared_coefficient * shared
        expected = exp(log_mean)
        baseline = row["exposure"] * baseline_rate
        model_total = _deviance(row["count"], expected)
        baseline_total = _deviance(row["count"], baseline)
        model_totals.append(model_total)
        baseline_totals.append(baseline_total)
        total_windows += row["windows"]
        unseen = (peak, shared) not in seen
        unseen_windows += row["windows"] if unseen else 0
        windows.append({
            **row, "predicted": expected, "baseline": baseline, "unseen": unseen,
            "model_deviance": model_total / row["windows"], "baseline_deviance": baseline_total / row["windows"],
        })
    # Average over observation windows, not station groups.  With one window per
    # group this is bit-for-bit the windowed mean.
    mean_model = fsum(model_totals) / total_windows
    mean_baseline = fsum(baseline_totals) / total_windows
    better = mean_model < mean_baseline and not isclose(mean_model, mean_baseline, rel_tol=1e-12, abs_tol=1e-12)
    training_windows = sum(row["windows"] for row in training)
    threshold = params["severity_rate"]
    roads = _planning(windows, ("road",), threshold)
    intersections = _planning(windows, ("road", "intersection"), threshold)
    focus = intersections[0]
    plan_columns = (("exposure", "情景车次"), ("predicted", "预计阻断次数"), ("rate", "预计次／百车次"),
                    ("severity", "巡查级别"), ("action", "排班动作"))
    coefficient_rows = [
        {"term": term, "coefficient": coefficient, "multiplier": exp(coefficient)}
        for term, coefficient in zip(("截距（平峰、独立通行）", "高峰（对比平峰）", "混行（对比独立通行）"), coefficients)
    ]
    span = f"训练 {days[0]} 至 {training[-1]['date']}，留出 {cutoff} 至 {days[-1]}。"
    if fmt == "grouped":
        note = (f"{span}汇总包与独立班报 {len(reconciliation)} 组对账通过，"
                f"留出 {total_windows:g} 个观测窗口。"
                f"重点阈值 {threshold:g} 次／百车次，优先阈值 {2 * threshold:g} 次／百车次。")
    else:
        note = (f"{span}重点阈值 {threshold:g} 次／百车次，优先阈值 {2 * threshold:g} 次／百车次。")
    comparison = "GLM 留出偏差低于基线" if better else "GLM 留出偏差未低于基线"
    if fmt == "grouped":
        labels = {field["key"]: field["label"] for field in (*SPEC["fields"], *SPEC["grouped_fields"],)}
        window_fields = tuple((key, labels[key]) for key in (*_GROUP_KEYS, "windows", "exposure", "count"))
    else:
        window_fields = tuple((field["key"], field["label"]) for field in SPEC["fields"])
    tables = []
    if reconciliation is not None:
        tables.append(_table("汇总包与独立班报对账", _RECONCILE_COLUMNS, reconciliation))
    tables.extend([
        _table("道路巡查计划", (("road", "道路"),) + plan_columns, roads),
        _table("路口巡查计划", (("road", "道路"), ("intersection", "路口")) + plan_columns, intersections),
        _table("模型系数与发生率倍数", (("term", "模型项"), ("coefficient", "系数"),
             ("multiplier", "每车次基准率或发生率倍数")), coefficient_rows),
        _table("留出窗口核对", window_fields + (
            ("predicted", "GLM 预计次数"), ("baseline", "基线预计次数"), ("model_deviance", "GLM 偏差"),
            ("baseline_deviance", "基线偏差"), ("unseen", "未见条件组合"),
        ), windows),
    ])
    sections = [
        {"title": "系数口径", "text": "截距的指数为平峰、独立通行条件下的每车次发生率。"
         "其余系数取指数后表示另一项条件相同时的发生率倍数。过车车次翻倍时，预计次数也翻倍。"},
        {"title": "排班口径", "text": "巡查表复用留出期的过车车次和条件，按预计阻断次数排序。"
         "路段和路口各自按每百车次的预计发生率定级。复核时请对照留出偏差和未见条件组合。"},
    ]
    if fmt == "grouped":
        sections.append({"title": "联合试算口径", "text": "联合试算只收分组统计：先逐站逐日按高峰与混行核对"
                         "汇总包与独立班报的窗数、车次和阻断数，任一组缺失或数值不一致即停算。"
                         "对账通过后按观测日整组划出留出期，再合并训练分组；分组口径的系数与逐窗平均偏差"
                         "与使用逐窗观测时一致。"})
    return {
        "format": fmt,
        "state": "ok" if better and not unseen_windows else "warning",
        "headline": f"{comparison}，{focus['road']} · {focus['intersection']}预计工作量最高。",
        "note": note,
        "metrics": [
            {"label": "训练窗口", "value": training_windows, "detail": f"{len(days) - holdout_days} 个观测日"},
            {"label": "留出窗口", "value": total_windows, "detail": f"{holdout_days} 个观测日 · {unseen_windows:g} 个窗口的条件组合未见于训练"},
            {"label": "GLM 平均偏差", "value": mean_model, "detail": "留出期每窗口 Poisson 偏差"},
            {"label": "基线平均偏差", "value": mean_baseline, "detail": f"训练基线 {100 * baseline_rate:.4g} 次／百车次"},
            {"label": "偏差减少量", "value": mean_baseline - mean_model, "detail": "基线平均偏差减去 GLM 平均偏差"},
        ],
        "charts": [
            {"title": "留出窗口平均 Poisson 偏差", "kind": "bar", "series": [
                {"label": "GLM", "value": mean_model}, {"label": "单一阻断率", "value": mean_baseline},
            ]},
            {"title": "预计阻断次数最高的路口（前 10）", "kind": "bar", "series": [
                {"label": f"{row['road']} · {row['intersection']}", "value": row["predicted"]}
                for row in intersections[:10]
            ]},
        ],
        "tables": tables,
        "sections": sections,
    }
