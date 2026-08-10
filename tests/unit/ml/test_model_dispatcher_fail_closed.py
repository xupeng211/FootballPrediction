"""MLC-1 regression tests: canonical production predictor must FAIL CLOSED
when the expected model artifact is missing.

Contract under test (tests written before the fix):
- v26_7_aligned (and every production-like model type) with a missing
  artifact must raise ModelArtifactUnavailableError
- _create_mini_model() must NOT be called implicitly for production types
- save() must NOT be called and no model artifact / model_zoo directory may
  be created as a side effect
- v26_mini remains the only model type allowed to explicitly create the
  synthetic mini model (test/demo utility)

Side-effect safety:
- No test trains XGBoost: synthetic creation is observed via monkeypatch
  recorders, never executed.
- cwd is redirected to tmp_path so even a hypothetical write cannot touch
  the repository checkout.
"""

from pathlib import Path

import pytest

from src.ml.inference.model_dispatcher import ModelArtifactUnavailableError, Predictor

# 生产型模型类型：缺失产物时必须 FAIL-CLOSED
PRODUCTION_MODEL_TYPES = [
    "v19_rolling",
    "v26_5_production",
    "v26_6_pre_match",
    "v26_7_aligned",
    "v26_8_epl",
    "v26_8_serie_a",
]


@pytest.fixture
def isolated_cwd(tmp_path, monkeypatch) -> str:
    """将 cwd 重定向到临时目录，防止任何仓库相对路径的写入副作用。"""
    monkeypatch.chdir(tmp_path)
    return str(tmp_path)


@pytest.fixture(autouse=True)
def no_synthetic_creation(monkeypatch):
    """若生产模型类型被错误地引导到 _create_mini_model()，测试立即失败。"""

    def _boom(*_args, **_kwargs):
        raise AssertionError("_create_mini_model() 不得为生产模型类型隐式调用（MLC-1 fail-closed）")

    monkeypatch.setattr(Predictor, "_create_mini_model", _boom)
    return _boom


# ---------------------------------------------------------------------------
# TEST A + TEST C — 生产产物缺失 → FAIL CLOSED，无合成 fallback
# ---------------------------------------------------------------------------


def test_v26_7_aligned_missing_artifact_fails_closed(isolated_cwd, monkeypatch):
    """TEST A/C: v26_7 产物缺失 → 显式不可用异常；不调用 _create_mini_model / save。"""
    save_calls = []
    monkeypatch.setattr(Predictor, "save", lambda *_args, **_kwargs: save_calls.append(True))

    with pytest.raises(ModelArtifactUnavailableError) as exc_info:
        Predictor(model_type="v26_7_aligned")

    assert "v26_7_aligned" in str(exc_info.value)
    assert save_calls == []  # save() 从未被调用
    # 不得创建 model_zoo 目录作为副作用
    assert not Path(isolated_cwd, "model_zoo").exists()


@pytest.mark.parametrize("model_type", PRODUCTION_MODEL_TYPES)
def test_production_model_types_missing_artifact_fail_closed(model_type):
    """TEST A（参数化）: 所有生产型模型类型缺失产物时都抛显式异常。"""
    with pytest.raises(ModelArtifactUnavailableError):
        Predictor(model_type=model_type)


def test_missing_artifact_does_not_create_any_model_file(isolated_cwd):
    """TEST A（文件系统断言）: 构造失败后不得产生 model_zoo 或任何模型产物。

    注：conftest 的 autouse fixture 会在 cwd 创建 data/ logs/ models/ 测试目录，
    因此只断言模型产物相关路径（model_zoo、*.pkl、*.joblib）不存在。
    """
    with pytest.raises(ModelArtifactUnavailableError):
        Predictor(model_type="v26_7_aligned")

    cwd = Path(isolated_cwd)
    assert not cwd.joinpath("model_zoo").exists()
    assert not list(cwd.rglob("*.pkl"))
    assert not list(cwd.rglob("*.joblib"))


# ---------------------------------------------------------------------------
# TEST D — 显式 v26_mini 行为保留（不训练、不写盘，仅记录分派）
# ---------------------------------------------------------------------------


def test_v26_mini_explicit_synthetic_behavior_preserved(isolated_cwd, monkeypatch):
    """TEST D: v26_mini 作为显式测试/演示模型，缺失产物时仍走合成创建路径。

    用记录器替换 _create_mini_model，证明分派仍然到达该路径；
    不实际训练 XGBoost，不写任何文件。
    """
    mini_calls = []
    monkeypatch.setattr(Predictor, "_create_mini_model", lambda *_args: mini_calls.append(True))

    predictor = Predictor(model_type="v26_mini")

    assert mini_calls == [True]  # 显式 mini 路径仍触发合成创建
    assert predictor.model_type == "v26_mini"
    # 记录器未执行真实训练，model 保持 None
    assert predictor.model is None
    # 未在临时目录产生任何模型产物（model_zoo / *.pkl / *.joblib）
    cwd = Path(isolated_cwd)
    assert not cwd.joinpath("model_zoo").exists()
    assert not list(cwd.rglob("*.pkl"))
    assert not list(cwd.rglob("*.joblib"))
