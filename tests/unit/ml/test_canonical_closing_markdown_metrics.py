"""收盘评分展示的合成回归；复用来源 fixture，不读取真实研究资产。"""

from __future__ import annotations

from copy import deepcopy
import json
import sys

import pytest

from scripts.model_evaluation import canonical_closing_retrospective as cli
from src.ml.evaluation import canonical_closing_retrospective as diagnostic
from tests.unit.ml import test_canonical_closing_retrospective as base

# 直接复用既有来源及 autouse 保护，不复制数据链或放开副作用。
prohibit_side_effects = base.prohibit_side_effects
sources = base.sources

SCORE_KEYS = ("multiclass_log_loss", "multiclass_brier_score")
PAIRED_METRICS = (("log_loss", "Log Loss"), ("brier", "Brier"))
MATCH_COUNT_KEYS = ("accounted_matches", "valid_paired_matches", "excluded_matches")
CONCLUSIONS = (
    ("MODEL_BETTER_THAN_CLOSING", "模型更好"),
    ("MARKET_BETTER_THAN_MODEL", "市场更好"),
    ("INCONCLUSIVE", "证据不足以区分"),
    ("INSUFFICIENT_EVIDENCE", "证据不足"),
)


def _report():
    return {
        "paired_calibration": base._uniform_calibration(10),
        "metrics": {
            "model": dict(zip(SCORE_KEYS, (0.978340123456, 0.584560876543), strict=True)),
            "market": dict(zip(SCORE_KEYS, (0.899730876543, 0.512345123456), strict=True)),
        },
        "uncertainty": {
            "log_loss": {
                "paired_delta_mean": 0.078609803723,
                "paired_delta_95_percentile_ci": [0.015476340689, 0.140815637412],
            },
            "brier": {
                "paired_delta_mean": -0.023456789,
                "paired_delta_95_percentile_ci": [-0.034567891, -0.012345678],
            },
        },
        "result_interpretation": "MARKET_BETTER_THAN_MODEL",
    }


def test_scores_between_overall_status_and_unchanged_groups():
    result = _report()
    before = deepcopy(result)
    payload = diagnostic.contract._canonical_json_bytes(result)
    text = diagnostic.render_summary_markdown(result)
    assert text.startswith(
        "# 中文配对校准摘要\n\n校准样本状态：仅供历史描述。\n\n"
        "分箱样本：最小非空分箱 10 场，至少需要 10 场。评分另按有效配对总数判断。\n\n"
        "| 指标 | 模型 | 收盘市场 |\n| --- | ---: | ---: |\n"
        "| Log Loss | 0.978340 | 0.899731 |\n| Brier | 0.584561 | 0.512345 |\n"
    )
    assert (
        text.index("| Brier |") < text.index("总体结论：市场更好。") < text.index("## 客胜(AWAY)")
    )
    assert "Log Loss、Brier 两项均越低越好。" in text
    assert (
        "总体结论：市场更好。\n"
        "Log Loss 配对平均差值（模型减收盘市场）：+0.078610；"
        "95% 配对 bootstrap 区间：[+0.015476, +0.140816]。\n"
        "Brier 配对平均差值（模型减收盘市场）：-0.023457；"
        "95% 配对 bootstrap 区间：[-0.034568, -0.012346]。\n"
        "Brier 为补充指标。\n"
        "沿用原 Log Loss 配对差值区间的结论依据，不按展示评分重新判断。\n"
    ) in text
    assert text.count("| 指标 | 模型 | 收盘市场 |") == 1
    assert [line for line in text.splitlines() if line.startswith("## ")] == [
        "## 客胜(AWAY)",
        "## 平局(DRAW)",
        "## 主胜(HOME)",
    ]
    without_metrics = diagnostic.render_summary_markdown(
        {"paired_calibration": result["paired_calibration"]}
    )
    assert text.split("## 客胜(AWAY)", 1)[1] == without_metrics.split("## 客胜(AWAY)", 1)[1]
    assert text == diagnostic.render_summary_markdown(result)
    assert result == before
    assert diagnostic.contract._canonical_json_bytes(result) == payload


@pytest.mark.parametrize(
    ("count", "status", "observed"),
    [
        (0, "样本不足", "没有非空分箱"),
        (1, "样本不足", "最小非空分箱 1 场"),
        (9, "样本不足", "最小非空分箱 9 场"),
        (10, "仅供历史描述", "最小非空分箱 10 场"),
    ],
)
def test_bin_sample_explanation_at_thresholds(count, status, observed):
    result = {"paired_calibration": base._uniform_calibration(count)}
    before = deepcopy(result)
    markdown = diagnostic.render_summary_markdown(result)
    assert (
        f"校准样本状态：{status}。\n\n"
        f"分箱样本：{observed}，至少需要 10 场。评分另按有效配对总数判断。\n\n"
        "样本不足，无法给出评分，也未生成区间。"
    ) in markdown
    assert markdown.count("分箱样本：") == 1
    assert result == before


def test_exact_zero_scores_are_available():
    result = _report()
    for side in ("model", "market"):
        result["metrics"][side] = dict.fromkeys(SCORE_KEYS, 0.0)
    before = deepcopy(result)
    text = diagnostic.render_summary_markdown(result)
    for title in ("Log Loss", "Brier"):
        assert f"| {title} | 0.000000 | 0.000000 |" in text
    assert "无法给出评分" not in text
    assert "总体结论：市场更好。" in text
    assert result == before


@pytest.mark.parametrize("side", ["model", "market"])
@pytest.mark.parametrize("key", SCORE_KEYS)
@pytest.mark.parametrize("missing", [False, True])
def test_missing_score_is_not_zero(side, key, missing):
    result = _report()
    if missing:
        del result["metrics"][side][key]
    else:
        result["metrics"][side][key] = None
    before = deepcopy(result)
    text = diagnostic.render_summary_markdown(result)
    title = "Log Loss" if key == SCORE_KEYS[0] else "Brier"
    row = next(line for line in text.splitlines() if line.startswith(f"| {title} |"))
    cells = [cell.strip() for cell in row.strip("|").split("|")]
    assert cells[1 if side == "model" else 2] == "无"
    other_side = "market" if side == "model" else "model"
    assert f"{result['metrics'][other_side][key]:.6f}" in row
    assert "0.000000" not in row
    assert result == before


@pytest.mark.parametrize("side", ["model", "market"])
@pytest.mark.parametrize("missing", [False, True])
def test_missing_score_bundle_preserves_other_side(side, missing):
    result = _report()
    if missing:
        del result["metrics"][side]
    else:
        result["metrics"][side] = None
    before = deepcopy(result)
    text = diagnostic.render_summary_markdown(result)
    if side == "model":
        assert "| Log Loss | 无 | 0.899731 |" in text
        assert "| Brier | 无 | 0.512345 |" in text
    else:
        assert "| Log Loss | 0.978340 | 无 |" in text
        assert "| Brier | 0.584561 | 无 |" in text
    assert result == before


@pytest.mark.parametrize("missing", [False, True])
def test_no_metrics_explicitly_reports_insufficient_sample(missing):
    result = _report()
    result["result_interpretation"] = "INSUFFICIENT_EVIDENCE"
    if missing:
        del result["metrics"]
    else:
        result["metrics"] = None
    before = deepcopy(result)
    text = diagnostic.render_summary_markdown(result)
    assert "校准样本状态：仅供历史描述。" in text
    assert text.index("样本不足，无法给出评分，也未生成区间。") < text.index("## 客胜(AWAY)")
    assert "| 指标 |" not in text
    assert "Log Loss 配对平均差值" not in text
    assert "Brier 配对平均差值" not in text
    assert "Brier 为补充指标。" not in text
    assert "沿用原 Log Loss 配对差值区间" not in text
    assert "总体结论：证据不足。" in text
    assert text.count("| [") == base.EXPECTED_CLASS_COUNT * base.EXPECTED_CALIBRATION_BIN_COUNT
    assert result == before


@pytest.mark.parametrize(("label", "notice"), CONCLUSIONS)
@pytest.mark.parametrize("rounded_equal", [False, True])
def test_conclusion_uses_original_label_even_when_scores_disagree(label, notice, rounded_equal):
    result = _report()
    result["result_interpretation"] = label
    if rounded_equal:
        # 舍入后完全相同仍保留各标签；不从展示值裁决。
        result["metrics"]["model"] = dict.fromkeys(SCORE_KEYS, 0.5000001)
        result["metrics"]["market"] = dict.fromkeys(SCORE_KEYS, 0.5000002)
    else:
        # Log Loss 指向市场、Brier 指向模型，二者都不能替代已有标签。
        result["metrics"]["model"][SCORE_KEYS[1]] = 0.1
    before = deepcopy(result)
    text = diagnostic.render_summary_markdown(result)
    assert f"总体结论：{notice}。" in text
    assert text.count("总体结论：") == 1
    if rounded_equal:
        for title in ("Log Loss", "Brier"):
            assert f"| {title} | 0.500000 | 0.500000 |" in text
    assert result == before


def test_unknown_conclusion_text_is_escaped():
    result = _report()
    hostile = "&<>\"'\\`*_{}[]()#+!|~\r\n"
    result["result_interpretation"] = hostile
    before = deepcopy(result)
    text = diagnostic.render_summary_markdown(result)
    assert "总体结论：" + "".join(f"&#{ord(char)};" for char in hostile) + "。" in text
    assert result == before


@pytest.mark.parametrize(("key", "title"), PAIRED_METRICS)
@pytest.mark.parametrize(("label", "notice"), CONCLUSIONS)
@pytest.mark.parametrize(
    ("mean", "interval", "display"),
    [
        (
            0.078609803723,
            [0.015476340689, 0.140815637412],
            "+0.078610；95% 配对 bootstrap 区间：[+0.015476, +0.140816]。",
        ),
        (
            -0.078609803723,
            [-0.140815637412, -0.015476340689],
            "-0.078610；95% 配对 bootstrap 区间：[-0.140816, -0.015476]。",
        ),
        (
            0.0123456789,
            [-0.03456789, 0.05678912],
            "+0.012346；95% 配对 bootstrap 区间：[-0.034568, +0.056789]。",
        ),
        (0.0, [0.0, 0.0], "+0.000000；95% 配对 bootstrap 区间：[+0.000000, +0.000000]。"),
        (-0.0, [-0.0, 0.0], "-0.000000；95% 配对 bootstrap 区间：[-0.000000, +0.000000]。"),
        (
            -0.0000001,
            [-0.0000002, 0.0000002],
            "-0.000000；95% 配对 bootstrap 区间：[-0.000000, +0.000000]。",
        ),
    ],
)
def test_paired_delta_displays_source_values_without_rejudging(
    key, title, label, notice, mean, interval, display
):
    result = _report()
    result["result_interpretation"] = label
    result["uncertainty"][key] = {
        "paired_delta_mean": mean,
        "paired_delta_95_percentile_ci": interval,
    }
    # 评分舍入后相等，且与给定配对均值不一致；不得通过评分重算或改判。
    result["metrics"]["model"] = dict.fromkeys(SCORE_KEYS, 0.5000001)
    result["metrics"]["market"] = dict.fromkeys(SCORE_KEYS, 0.5000002)
    before = deepcopy(result)
    payload = diagnostic.contract._canonical_json_bytes(result)
    text = diagnostic.render_summary_markdown(result)
    line = f"{title} 配对平均差值（模型减收盘市场）：{display}"
    assert text.index(f"总体结论：{notice}。") < text.index(line) < text.index("## 客胜(AWAY)")
    assert text.count(f"{title} 配对平均差值") == 1
    for score_title in ("Log Loss", "Brier"):
        assert f"| {score_title} | 0.500000 | 0.500000 |" in text
    assert "未生成" not in text
    assert result == before
    assert diagnostic.contract._canonical_json_bytes(result) == payload


@pytest.mark.parametrize(("key", "title"), PAIRED_METRICS)
@pytest.mark.parametrize(
    ("paired", "mean_text", "interval_text"),
    [
        (None, "未生成", "未生成"),
        ({}, "未生成", "未生成"),
        ({"paired_delta_mean": 0.0}, "+0.000000", "未生成"),
        (
            {"paired_delta_95_percentile_ci": [0.0, 0.0]},
            "未生成",
            "[+0.000000, +0.000000]",
        ),
        (
            {"paired_delta_mean": None, "paired_delta_95_percentile_ci": [0.1, 0.2]},
            "未生成",
            "[+0.100000, +0.200000]",
        ),
    ],
)
def test_missing_paired_information_preserves_scores(key, title, paired, mean_text, interval_text):
    result = _report()
    result["uncertainty"][key] = paired
    before = deepcopy(result)
    payload = diagnostic.contract._canonical_json_bytes(result)
    text = diagnostic.render_summary_markdown(result)
    assert (
        f"{title} 配对平均差值（模型减收盘市场）：{mean_text}；"
        f"95% 配对 bootstrap 区间：{interval_text}。"
    ) in text
    assert "| Log Loss | 0.978340 | 0.899731 |" in text
    assert "| Brier | 0.584561 | 0.512345 |" in text
    assert "总体结论：市场更好。" in text
    assert "样本不足，无法给出评分" not in text
    assert text.count("未生成") == (mean_text == "未生成") + (interval_text == "未生成")
    assert text.count("| [") == base.EXPECTED_CLASS_COUNT * base.EXPECTED_CALIBRATION_BIN_COUNT
    assert result == before
    assert diagnostic.contract._canonical_json_bytes(result) == payload


@pytest.mark.parametrize(("key", "title"), PAIRED_METRICS)
@pytest.mark.parametrize("interval", [None, [], [0.1], [None, 0.2], [0.1, None], [0.1, 0.2, 0.3]])
def test_incomplete_interval_is_not_invented(key, title, interval):
    result = _report()
    paired = result["uncertainty"][key]
    paired["paired_delta_95_percentile_ci"] = interval
    before = deepcopy(result)
    text = diagnostic.render_summary_markdown(result)
    assert (
        f"{title} 配对平均差值（模型减收盘市场）：{paired['paired_delta_mean']:+.6f}；"
        "95% 配对 bootstrap 区间：未生成。"
    ) in text
    assert "0.000000" not in text.split("## 客胜(AWAY)", 1)[0]
    assert result == before


@pytest.mark.parametrize("fields", [{}, {"uncertainty": None}, {"uncertainty": {}}])
def test_unavailable_uncertainty_is_not_zero(fields):
    result = {key: value for key, value in _report().items() if key != "uncertainty"} | fields
    before = deepcopy(result)
    text = diagnostic.render_summary_markdown(result)
    for _, title in PAIRED_METRICS:
        assert (
            f"{title} 配对平均差值（模型减收盘市场）：未生成；95% 配对 bootstrap 区间：未生成。"
        ) in text
    assert "| Log Loss | 0.978340 | 0.899731 |" in text
    assert result == before


def test_missing_brier_preserves_log_loss():
    result = _report()
    del result["uncertainty"]["brier"]
    text = diagnostic.render_summary_markdown(result)
    assert (
        "Log Loss 配对平均差值（模型减收盘市场）：+0.078610；"
        "95% 配对 bootstrap 区间：[+0.015476, +0.140816]。\n"
        "Brier 配对平均差值（模型减收盘市场）：未生成；95% 配对 bootstrap 区间：未生成。\n"
        "Brier 为补充指标。\n"
    ) in text


@pytest.mark.parametrize("missing_keys", [MATCH_COUNT_KEYS, *((key,) for key in MATCH_COUNT_KEYS)])
@pytest.mark.parametrize("has_scores", [False, True])
def test_incomplete_match_counts_keep_legacy_markdown(missing_keys, has_scores):
    legacy = _report()
    if not has_scores:
        legacy["metrics"] = None
    expected = diagnostic.render_summary_markdown(legacy)
    result = {**legacy, **dict(zip(MATCH_COUNT_KEYS, (11, 10, 1), strict=True))}
    for key in missing_keys:
        del result[key]
    null_fields = dict.fromkeys(missing_keys)
    assert "总场数：" not in expected
    assert diagnostic.render_summary_markdown(result) == expected
    assert diagnostic.render_summary_markdown({**result, **null_fields}) == expected


@pytest.mark.parametrize(
    ("counts", "line"),
    [
        ((0, 0, 0), "总场数：0 场，有效配对：0 场，排除场数：0 场。"),
        (("<7>\n", 2, 1), "总场数：&#60;7&#62;&#10; 场，有效配对：2 场，排除场数：1 场。"),
    ],
)
def test_match_counts_display_source_values_unchanged(counts, line):
    legacy = _report()
    result = {**legacy, **dict(zip(MATCH_COUNT_KEYS, counts, strict=True))}
    before = deepcopy(result)
    text = diagnostic.render_summary_markdown(result)
    assert text.count("总场数：") == 1
    segment = f"{line}\n\n"
    assert f"评分另按有效配对总数判断。\n\n{segment}| 指标 |" in text
    assert text.replace(segment, "", 1) == diagnostic.render_summary_markdown(legacy)
    assert result == before


def _assert_cli_markdown(text, expected, excluded, has_scores):
    paired = 3 - excluded
    observed = f"最小非空分箱 {paired} 场" if paired else "没有非空分箱"
    counts = f"总场数：3 场，有效配对：{paired} 场，排除场数：{excluded} 场。\n\n"
    scoring = "| 指标 |" if has_scores else "样本不足，无法给出评分，也未生成区间。"
    assert text.count("总场数：") == 1
    assert (
        "校准样本状态：样本不足。\n\n"
        f"分箱样本：{observed}，至少需要 10 场。评分另按有效配对总数判断。\n\n"
        f"{counts}{scoring}"
    ) in text
    legacy = {key: value for key, value in expected.items() if key not in MATCH_COUNT_KEYS}
    assert text.replace(counts, "", 1) == diagnostic.render_summary_markdown(legacy) + "\n"
    if excluded:
        assert f"| MISSING&#95;FROZEN&#95;PREDICTION | {excluded} |" in text
        assert "无排除比赛" not in text
    else:
        assert "无排除比赛" in text
    assert text.index("总体结论：") < text.index("### 比赛排除原因") < text.index("## 客胜(AWAY)")
    if has_scores:
        for key, title in zip(SCORE_KEYS, ("Log Loss", "Brier"), strict=True):
            model = expected["metrics"]["model"][key]
            market = expected["metrics"]["market"][key]
            assert f"| {title} | {model:.6f} | {market:.6f} |" in text
        assert "无法给出评分" not in text
        paired_lines = []
        for key, title in PAIRED_METRICS:
            paired = expected["uncertainty"][key]
            low, high = paired["paired_delta_95_percentile_ci"]
            paired_lines.append(
                f"{title} 配对平均差值（模型减收盘市场）：{paired['paired_delta_mean']:+.6f}；"
                f"95% 配对 bootstrap 区间：[{low:+.6f}, {high:+.6f}]。"
            )
        assert "\n".join([*paired_lines, "Brier 为补充指标。", ""]) in text
    else:
        assert "总体结论：证据不足。" in text
        assert "配对平均差值" not in text
        assert "Brier 为补充指标。" not in text
        assert "沿用原 Log Loss 配对差值区间" not in text


@pytest.mark.parametrize(
    ("excluded", "has_scores"), [(0, True), (1, True), (0, False), (1, False), (3, False)]
)
def test_real_analyze_to_cli_preserves_json_and_sources(
    sources, excluded, has_scores, tmp_path, monkeypatch, capsysbinary
):
    """仅替换 loader 的合成来源；真实 analyze、评分、renderer 和 CLI 均执行。"""
    del sources["evaluation"]["prediction_rows"][3 - excluded :]
    if not has_scores:
        monkeypatch.setattr(diagnostic, "MINIMUM_PAIRS", 30)
    before = deepcopy(sources)
    expected = diagnostic.analyze(sources)
    assert (expected["metrics"] is not None) == has_scores
    assert expected["paired_calibration"]["sample_status"] == "INSUFFICIENT_SAMPLE"
    expected_reasons = {"MISSING_FROZEN_PREDICTION": excluded} if excluded else {}
    assert expected["exclusion_reasons"] == expected_reasons
    assert tuple(expected[key] for key in MATCH_COUNT_KEYS) == (3, 3 - excluded, excluded)
    assert sources == before
    expected_before = deepcopy(expected)
    expected_payload = diagnostic.contract._canonical_json_bytes(expected) + b"\n"
    calls = []
    monkeypatch.setattr(diagnostic, "load_sources", lambda _paths: calls.append("load") or sources)
    payloads = []
    json_outputs = []
    for summary_format in (None, "json", "markdown"):
        output = tmp_path / f"synthetic-{summary_format}.json"
        monkeypatch.setattr(sys, "argv", base._summary_cli_args(output, summary_format))
        assert cli.main() == 0
        captured = capsysbinary.readouterr()
        assert captured.err == b""
        payloads.append(output.read_bytes())
        assert json.loads(payloads[-1]) == expected
        if summary_format == "markdown":
            _assert_cli_markdown(captured.out.decode(), expected, excluded, has_scores)
        else:
            json_outputs.append(captured.out)
            assert captured.out == base._summary_stdout(expected, summary_format).encode()
        assert sources == before
        assert expected == expected_before
    assert calls == ["load", "load", "load"]
    assert payloads == [expected_payload] * 3
    assert json_outputs[0] == json_outputs[1]
    assert diagnostic.contract._canonical_json_bytes(expected) + b"\n" == expected_payload


@pytest.mark.parametrize("metrics_state", ["available", "missing", "null"])
def test_exclusion_reasons_sorted_escaped_and_independent_of_scores(metrics_state):
    result = _report()
    if metrics_state == "missing":
        del result["metrics"]
    elif metrics_state == "null":
        result["metrics"] = None
    # 插入顺序与场数顺序不同；同数时按原始原因码而非转义后的文本排序。
    result["exclusion_reasons"] = {"Z": 2, "A|\r\n": 2, "A": 1, "B": 12, "A~": 2, "A_": 2}
    before = deepcopy(result)
    payload = diagnostic.contract._canonical_json_bytes(result)
    text = diagnostic.render_summary_markdown(result)
    prefix, remaining = text.split("### 比赛排除原因\n\n", 1)
    section, groups = remaining.split("## 客胜(AWAY)", 1)
    assert "总体结论：市场更好。" in prefix
    if metrics_state == "available":
        assert prefix.endswith("沿用原 Log Loss 配对差值区间的结论依据，不按展示评分重新判断。\n\n")
    else:
        assert "样本不足，无法给出评分，也未生成区间。" in prefix
    assert section == (
        "| 原因码 | 场数 |\n| --- | ---: |\n"
        "| B | 12 |\n| A&#95; | 2 |\n| A&#124;&#13;&#10; | 2 |\n"
        "| A&#126; | 2 |\n| Z | 2 |\n| A | 1 |\n\n"
    )
    assert text.count("### 比赛排除原因") == 1
    assert "未提供排除原因" not in text
    assert "无排除比赛" not in text
    without_reasons = deepcopy(result)
    del without_reasons["exclusion_reasons"]
    baseline = diagnostic.render_summary_markdown(without_reasons)
    assert baseline.split("### 比赛排除原因\n\n", 1)[0] == prefix
    assert baseline.split("## 客胜(AWAY)", 1)[1] == groups
    assert text == diagnostic.render_summary_markdown(result)
    assert result == before
    assert diagnostic.contract._canonical_json_bytes(result) == payload


@pytest.mark.parametrize(
    ("fields", "notice"),
    [
        ({"exclusion_reasons": {}}, "无排除比赛"),
        ({}, "未提供排除原因"),
        ({"exclusion_reasons": None}, "未提供排除原因"),
    ],
)
def test_empty_or_unprovided_exclusion_reasons(fields, notice):
    result = {**_report(), **fields}
    before = deepcopy(result)
    payload = diagnostic.contract._canonical_json_bytes(result)
    text = diagnostic.render_summary_markdown(result)
    assert f"### 比赛排除原因\n\n{notice}\n\n## 客胜(AWAY)" in text
    assert "| 原因码 | 场数 |" not in text
    assert result == before
    assert diagnostic.contract._canonical_json_bytes(result) == payload
