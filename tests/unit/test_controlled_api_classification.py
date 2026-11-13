"""专用执行状态的精确分类；未知数据库路径及改码后分类仍 fail-closed。"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.devops.controlled_api_budget import Budget
from scripts.devops.controlled_api_policy import ControlError
from scripts.ops import python_db_write_static_enforcement as scanner
from scripts.ops.helpers.python_db_write_enforcement_check import check_python_db_write_enforcement

PROJECT = Path(__file__).resolve().parents[2]
BUDGET_PATH = "scripts/devops/controlled_api_budget.py"


def test_new_state_classification_passes_without_historical_exemption():
    scan = scanner.changed_files_check([BUDGET_PATH])
    assert scan["would_hard_fail"] is False
    item = scan["passed"][0]
    assert item["allowlist_classification"] == "local_execution_state_write_runtime_guarded"
    assert not item["allowlist_classification"].startswith("historical_")
    errors, _ = check_python_db_write_enforcement({BUDGET_PATH})
    assert errors == []


@pytest.mark.parametrize("change", ["bytes", "hash", "path", "contract", "business"])
def test_runtime_state_classification_cannot_spread_or_accept_changed_code(
    tmp_path, monkeypatch, change
):
    entries = scanner._load_allowlist()
    entry = deepcopy(entries[BUDGET_PATH])
    path = tmp_path / BUDGET_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes((PROJECT / BUDGET_PATH).read_bytes())
    if change == "bytes":
        path.write_bytes(path.read_bytes() + b"\n# changed controller\n")
    elif change == "hash":
        entry["source_sha256"] = "0" * 64
    elif change == "path":
        entry["path"] = "src/database/other.py"
        path = tmp_path / entry["path"]
        path.parent.mkdir(parents=True)
        path.write_bytes((PROJECT / BUDGET_PATH).read_bytes())
    elif change == "contract":
        entry.pop("storage_contract")
    else:
        entry["protected_business_store_access"] = True
    monkeypatch.setattr(scanner, "REPO_ROOT", tmp_path)
    result = scanner._scan_file_for_signals(path)
    checked = scanner._apply_allowlist([result], {entry["path"]: entry})[0]
    assert checked["would_fail_changed_files_gate"] is True
    assert checked["allowlist_status"] == "not_in_allowlist"


def test_existing_historical_entries_unchanged():
    current = json.loads((PROJECT / "config/python_db_write_allowlist.json").read_text())
    historical = json.dumps(current["entries"], sort_keys=True, ensure_ascii=False).encode()
    assert (
        hashlib.sha256(historical).hexdigest()
        == "89554b042fb0a3ea601f43686abe10f39f17df3dbf45db4943b8cf1c6cf15e55"
    )


@pytest.mark.parametrize(
    "change", ["marker_missing", "marker_changed", "marker_link", "db_link", "existing_dir"]
)
def test_runtime_state_guard_refuses_unowned_or_unrelated_store(tmp_path, change):
    root = tmp_path / "state"
    if change == "existing_dir":
        root.mkdir(mode=0o700)
        (root / "receipt.json").write_text("historical evidence")
        with pytest.raises(FileExistsError):
            Budget(root, initialize=True)
        assert (root / "receipt.json").read_text() == "historical evidence"
        return
    budget = Budget(root, initialize=True)
    marker = root / ".execution-state"
    if change == "marker_missing":
        marker.unlink()
    elif change == "marker_changed":
        marker.write_text("different evidence store")
    elif change == "marker_link":
        original = marker.read_bytes()
        marker.unlink()
        other = tmp_path / "marker"
        other.write_bytes(original)
        marker.symlink_to(other)
    else:
        original = budget.path
        moved = tmp_path / "other.sqlite3"
        original.rename(moved)
        original.symlink_to(moved)
    with pytest.raises((ControlError, OSError)):
        budget.connect()


def test_marker_does_not_authorize_an_unrelated_sqlite_file(tmp_path):
    budget = Budget(tmp_path / "state", initialize=True)
    budget.path.write_bytes(b"")
    with pytest.raises(ControlError, match="EXECUTION_STATE_IDENTITY_REQUIRED"):
        Budget(budget.root)
