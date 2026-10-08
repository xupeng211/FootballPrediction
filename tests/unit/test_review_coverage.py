"""真实 Git blob 导出与删除内容 retention 的负面测试。"""

from hashlib import sha256
import json
import subprocess

import pytest

from scripts.devops.review_coverage import export_full_review_material, verify_full_review_material


def git(repo, *args):
    return (
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
        .stdout.decode()
        .strip()
    )


def test_full_deletion_bytes_and_identity_survive_export(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.invalid")
    original = b"\xff\x00complete deleted bytes\n" * 1000
    (repo / "deleted qa.bin").write_bytes(original)
    (repo / "active.py").write_text("before\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "deleted qa.bin").unlink()
    (repo / "active.py").write_text("after\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "candidate")
    head = git(repo, "rev-parse", "HEAD")
    folder = tmp_path / "external"
    manifest = export_full_review_material(repo, base, head, folder)
    deleted = next(x for x in manifest["changed_files"] if x["status"] == "D")
    assert deleted["after"] is None
    blob = deleted["before"]
    assert blob["bytes"] == len(original)
    assert blob["sha256"] == sha256(original).hexdigest()
    assert (folder / blob["artifact"]).read_bytes() == original
    assert blob["git_blob_oid"] == git(repo, "rev-parse", f"{base}:deleted qa.bin")
    assert manifest["diff_sha256"] == sha256((folder / "full.diff").read_bytes()).hexdigest()
    assert manifest["approval"] is False
    assert json.loads((folder / "manifest.json").read_text()) == manifest
    assert verify_full_review_material(repo, base, head, folder) == manifest
    artifact = folder / blob["artifact"]
    artifact.write_bytes(original[:-1])
    with pytest.raises(ValueError, match="CHANGED_BLOB_MISMATCH"):
        verify_full_review_material(repo, base, head, folder)
    artifact.write_bytes(original)
    (folder / "summary.json").write_text("{}")
    (folder / "summary.json").chmod(0o600)
    with pytest.raises(ValueError, match="MATERIAL_MANIFEST_OR_FILE_SET_MISMATCH"):
        verify_full_review_material(repo, base, head, folder)
    (folder / "summary.json").unlink()
    document = json.loads((folder / "manifest.json").read_text())
    document["changed_files"] = []
    (folder / "manifest.json").write_text(json.dumps(document))
    with pytest.raises(ValueError, match="MATERIAL_MANIFEST_OR_FILE_SET_MISMATCH"):
        verify_full_review_material(repo, base, head, folder)
    with pytest.raises(FileExistsError):
        export_full_review_material(repo, base, head, folder)
    with pytest.raises(ValueError, match="reviewed source tree"):
        export_full_review_material(repo, base, head, repo / "evidence")


def test_three_dot_records_effective_base_without_pretending_branch_tip_is_old_content(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "asset").write_text("shared-base")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "shared")
    shared = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-qb", "candidate")
    (repo / "asset").unlink()
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "delete")
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-qb", "base", shared)
    (repo / "asset").write_text("new-base-tip")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base-tip")
    base = git(repo, "rev-parse", "HEAD")
    manifest = export_full_review_material(repo, base, head, tmp_path / "bundle")
    assert manifest["base_sha"] == base
    assert manifest["effective_diff_base_sha"] == shared
    assert manifest["changed_files"][0]["before"]["sha256"] == sha256(b"shared-base").hexdigest()
