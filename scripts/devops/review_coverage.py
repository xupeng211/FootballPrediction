"""导出完整 exact-Git 审核材料；摘要不能替代 diff 或被删除的 blob。

Lifecycle: permanent
Owner: engineering workflow governance
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any

from scripts.devops.codex_review_receipt import _require_external_path, diff_sha256
from scripts.devops.codex_review_verdict import assert_owner_only_directory
from scripts.devops.exact_head import normalize_full_sha

OWNER_ONLY_FILE_MODE = 0o600


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout


def _write_new(path: Path, value: bytes) -> None:
    with path.open("xb") as file:
        path.chmod(0o600)
        file.write(value)


def export_full_review_material(
    repo_root: Path, base: str, head: str, directory: Path
) -> dict[str, Any]:
    """与现行 receipt 的 three-dot diff 完全一致；记录真实 merge-base。

    导出所有变更文件的前后完整字节和 blob 身份，含删除和 symlink blob。
    retention 是实际 external blob 文件，不是“将来还能从 Git 找到”的承诺。
    material 完整性不等于语义 review 完成；不创建 approval receipt。
    """
    base = normalize_full_sha(base, role="base")
    head = normalize_full_sha(head, role="head")
    for value in (base, head):
        if _git(repo_root, "rev-parse", f"{value}^{{commit}}").decode().strip() != value:
            raise ValueError("EXACT_COMMIT_REQUIRED")
    directory = _require_external_path(directory, repo_root)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    assert_owner_only_directory(directory)
    effective_base = _git(repo_root, "merge-base", base, head).decode().strip()
    diff = _git(repo_root, "diff", "--binary", "--no-ext-diff", f"{base}...{head}")
    digest = sha256(diff).hexdigest()
    if digest != diff_sha256(repo_root, base, head):
        raise ValueError("CANONICAL_DIFF_CHANGED")
    _write_new(directory / "full.diff", diff)
    raw = _git(repo_root, "diff", "--name-status", "-z", "--no-renames", f"{base}...{head}")
    fields = raw.split(b"\0")
    if fields[-1] != b"" or (len(fields) - 1) % 2:
        raise ValueError("INVALID_CHANGED_PATH_SET")
    entries = []
    for index in range(0, len(fields) - 1, 2):
        status = fields[index].decode("ascii")
        path = fields[index + 1].decode("utf-8", "strict")
        if status not in {"A", "M", "D", "T"}:
            raise ValueError("UNSUPPORTED_CHANGE_KIND")
        entry: dict[str, Any] = {"path": path, "status": status, "before": None, "after": None}
        for label, commit, absent in [("before", effective_base, "A"), ("after", head, "D")]:
            if status == absent:
                continue
            blob = _git(repo_root, "rev-parse", f"{commit}:{path}").decode().strip()
            if _git(repo_root, "cat-file", "-t", blob).strip() != b"blob":
                raise ValueError("NON_BLOB_CHANGE_REQUIRES_SEPARATE_CONTRACT")
            body = _git(repo_root, "cat-file", "blob", blob)
            filename = f"{index // 2:04d}-{label}.blob"
            _write_new(directory / filename, body)
            entry[label] = {
                "git_blob_oid": blob,
                "bytes": len(body),
                "sha256": sha256(body).hexdigest(),
                "artifact": filename,
            }
        entries.append(entry)
    manifest = {
        "version": "full-git-review-material/v1",
        "base_sha": base,
        "effective_diff_base_sha": effective_base,
        "head_sha": head,
        "diff_sha256": digest,
        "diff_bytes": len(diff),
        "changed_files": entries,
        "representation": "FULL_DIFF_AND_FULL_CHANGED_BLOBS",
        "approval": False,
    }
    _write_new(
        directory / "manifest.json",
        (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(),
    )
    return manifest


def verify_full_review_material(
    repo_root: Path, base: str, head: str, directory: Path
) -> dict[str, Any]:
    """从 Git 重新证明所有材料；删除内容、身份、额外文件或摘要替换都 fail closed。"""
    base = normalize_full_sha(base, role="base")
    head = normalize_full_sha(head, role="head")
    directory = _require_external_path(directory, repo_root)
    assert_owner_only_directory(directory)
    for file in directory.iterdir():
        info = file.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != OWNER_ONLY_FILE_MODE
        ):
            raise ValueError("UNSAFE_MATERIAL_FILE")
    manifest: dict[str, Any] = json.loads((directory / "manifest.json").read_bytes())
    effective_base = _git(repo_root, "merge-base", base, head).decode().strip()
    diff = _git(repo_root, "diff", "--binary", "--no-ext-diff", f"{base}...{head}")
    if (directory / "full.diff").read_bytes() != diff:
        raise ValueError("FULL_DIFF_MISMATCH")
    raw = _git(repo_root, "diff", "--name-status", "-z", "--no-renames", f"{base}...{head}")
    fields = raw.split(b"\0")
    entries = []
    allowed = {"manifest.json", "full.diff"}
    for index in range(0, len(fields) - 1, 2):
        status = fields[index].decode("ascii")
        path = fields[index + 1].decode("utf-8", "strict")
        entry: dict[str, Any] = {"path": path, "status": status, "before": None, "after": None}
        for label, commit, absent in [("before", effective_base, "A"), ("after", head, "D")]:
            if status == absent:
                continue
            blob = _git(repo_root, "rev-parse", f"{commit}:{path}").decode().strip()
            body = _git(repo_root, "cat-file", "blob", blob)
            filename = f"{index // 2:04d}-{label}.blob"
            allowed.add(filename)
            if (directory / filename).read_bytes() != body:
                raise ValueError("CHANGED_BLOB_MISMATCH")
            entry[label] = {
                "git_blob_oid": blob,
                "bytes": len(body),
                "sha256": sha256(body).hexdigest(),
                "artifact": filename,
            }
        entries.append(entry)
    expected = {
        "version": "full-git-review-material/v1",
        "base_sha": base,
        "effective_diff_base_sha": effective_base,
        "head_sha": head,
        "diff_sha256": sha256(diff).hexdigest(),
        "diff_bytes": len(diff),
        "changed_files": entries,
        "representation": "FULL_DIFF_AND_FULL_CHANGED_BLOBS",
        "approval": False,
    }
    if manifest != expected or {file.name for file in directory.iterdir()} != allowed:
        raise ValueError("MATERIAL_MANIFEST_OR_FILE_SET_MISMATCH")
    return manifest


def main(argv: list[str] | None = None) -> int:
    """导出或核验材料；这不是审核通过入口。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    try:
        function = verify_full_review_material if args.verify else export_full_review_material
        manifest = function(args.repo_root, args.base, args.head, args.evidence_dir)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(
            json.dumps({"status": "INVALID", "error_class": type(exc).__name__, "approval": False})
        )
        return 1
    print(
        json.dumps(
            {
                "status": "MATERIAL_EXPORTED_NOT_APPROVAL",
                "approval": False,
                "diff_sha256": manifest["diff_sha256"],
                "changed_files": len(manifest["changed_files"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
