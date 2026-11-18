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
        "result_interpretation": "MARKET_BETTER_THAN_MODEL",
    }


def test_scores_between_overall_status_and_unchanged_groups():
    result = _report()
    before = deepcopy(result)
    payload = diagnostic.contract._canonical_json_bytes(result)
    text = diagnostic.render_summary_markdown(result)
    assert text.startswith(
        "# 中文配对校准摘要\n\n校准样本状态：仅供历史描述。\n\n"
        "| 指标 | 模型 | 收盘市场 |\n| --- | ---: | ---: |\n"
        "| Log Loss | 0.978340 | 0.899731 |\n| Brier | 0.584561 | 0.512345 |\n"
    )
    assert (
        text.index("| Brier |") < text.index("总体结论：市场更好。") < text.index("## 客胜(AWAY)")
    )
    assert "Log Loss、Brier 两项均越低越好。" in text
    assert "沿用原 Log Loss 配对差值区间的结论依据，不按展示评分重新判断。" in text
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


@pytest.mark.parametrize("has_scores", [False, True])
def test_real_analyze_to_cli_preserves_json_and_sources(
    sources, has_scores, tmp_path, monkeypatch, capsys
):
    """仅替换 loader 的合成来源；真实 analyze、评分、renderer 和 CLI 均执行。"""
    if not has_scores:
        monkeypatch.setattr(diagnostic, "MINIMUM_PAIRS", 30)
    before = deepcopy(sources)
    expected = diagnostic.analyze(sources)
    assert (expected["metrics"] is not None) == has_scores
    assert expected["paired_calibration"]["sample_status"] == "INSUFFICIENT_SAMPLE"
    expected_payload = diagnostic.contract._canonical_json_bytes(expected) + b"\n"
    calls = []
    monkeypatch.setattr(diagnostic, "load_sources", lambda _paths: calls.append("load") or sources)
    payloads = []
    json_outputs = []
    for summary_format in (None, "json", "markdown"):
        output = tmp_path / f"synthetic-{summary_format}.json"
        monkeypatch.setattr(sys, "argv", base._summary_cli_args(output, summary_format))
        assert cli.main() == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        payloads.append(output.read_bytes())
        assert json.loads(payloads[-1]) == expected
        if summary_format == "markdown":
            assert captured.out == diagnostic.render_summary_markdown(expected) + "\n"
            assert "校准样本状态：样本不足。" in captured.out
            if has_scores:
                for key, title in zip(SCORE_KEYS, ("Log Loss", "Brier"), strict=True):
                    model = expected["metrics"]["model"][key]
                    market = expected["metrics"]["market"][key]
                    assert f"| {title} | {model:.6f} | {market:.6f} |" in captured.out
                assert "无法给出评分" not in captured.out
            else:
                assert "样本不足，无法给出评分，也未生成区间。" in captured.out
                assert "总体结论：证据不足。" in captured.out
                assert "沿用原 Log Loss 配对差值区间" not in captured.out
        else:
            json_outputs.append(captured.out)
            assert captured.out == base._summary_stdout(expected, summary_format)
        assert sources == before
    assert calls == ["load", "load", "load"]
    assert payloads == [expected_payload] * 3
    assert json_outputs[0] == json_outputs[1]
    assert diagnostic.contract._canonical_json_bytes(expected) + b"\n" == expected_payload
