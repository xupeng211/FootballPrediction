"""本次 repair 的固定手工表适配；不是任意任务的上下文分组器。

lifecycle: permanent
owner: engineering workflow governance
"""

from __future__ import annotations

import ast
import json
import subprocess

from scripts.devops.independent_review_protocol import sha256_bytes, validate_sha

MISSION = "FP_PERCENT_PILOT_INPUT_ADMISSION_REPAIR_20261105"
VERSION = "fixed-repair-packets/v1"
BASE = "714ee95ebbd34aca3182697aab7348a0d4965af3"
MAX_DIFF = 32_000
MAX_PROMPT = 40_000
MAX_COUNT = 64
TABLE = "docs/agentic/review_inputs/FP_PERCENT_PILOT_INPUT_ADMISSION_REPAIR_20261105.json"
TABLE_SHA256 = "011903643704efddc7bbb3c7cadfc1dd578a6cba7e1ce2044d90c27e9ab3fe98"
SOURCE_PATHS = frozenset(
    (
        "docs/agentic/review_inputs/FP_PERCENT_PILOT_INPUT_ADMISSION_REPAIR_20261105.json",
        "scripts/devops/claude_deepseek_independent_review.py",
        "scripts/devops/deepseek_chunk_receipt_validation.py",
        "scripts/devops/deepseek_receipt_evidence.py",
        "scripts/devops/deepseek_review_chunks.py",
        "scripts/devops/independent_review_backends/claude_code_deepseek.py",
        "scripts/devops/independent_review_protocol.py",
        "scripts/devops/independent_review_receipt.py",
        "scripts/devops/percent_repair_input.py",
        "scripts/devops/percent_repair_packets.py",
        "scripts/ops/ai_workflow_gate.py",
        "scripts/ops/helpers/documentation_backflow.py",
        "scripts/ops/helpers/pr_authorization_matrix.py",
        "tests/unit/test_deepseek_frozen_source_context.py",
        "tests/unit/test_deepseek_percent_source_context.py",
        "tests/unit/test_deepseek_review_chunks.py",
        "tests/unit/test_percent_pilot_documentation_backflow.py",
        "tests/unit/test_percent_repair_packets.py",
        "tests/unit/test_project_knowledge_convergence.py",
    )
)


def _git(root, *args):
    return subprocess.check_output(
        [
            "git",
            "--no-replace-objects",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(root),
            *args,
        ],
        stderr=subprocess.PIPE,
    )


def _blob(root, revision, path):
    if path not in SOURCE_PATHS:
        raise ValueError("repair source path is not authorized")
    validate_sha(revision, name="repair source commit", length=40)
    row = _git(root, "ls-tree", "-z", revision, "--", path)
    if not row:
        return None, "ABSENT"
    meta, actual = row.rstrip(b"\0").split(b"\t")
    mode, kind, oid = meta.decode().split()
    if actual.decode() != path or kind != "blob" or mode not in {"100644", "100755"}:
        raise ValueError("repair requires ordinary Git blobs")
    raw = _git(root, "cat-file", "blob", oid)
    raw.decode("utf-8")
    if b"\0" in raw:
        raise ValueError("repair requires complete text blobs")
    return raw, f"{mode} blob {oid}\t{path}"


def _sources(root, base, head, selectors):
    rendered = []
    for selector in selectors:
        path = selector["path"]
        version = selector.get("version", "HEAD")
        if version not in {"BASE", "HEAD"}:
            raise ValueError("unapproved repair source version")
        revision = base if version == "BASE" else head
        raw, identity = _blob(root, revision, path)
        if raw is None:
            raise ValueError("required repair source is missing")
        _, old_identity = _blob(root, base, path)
        rendered.append(
            f"\nSOURCE {path}\n{version} {revision} {identity.split()[0]} "
            f"blob={identity.split()[2]} file_sha256={sha256_bytes(raw)}\n"
            f"BASE {base} {old_identity}\n"
        )
        if selector["symbols"] == "@identity" and path == TABLE:
            continue
        if selector["symbols"] == "@file":
            rendered.append(raw.decode() + "\n")
            continue
        lines = raw.decode().splitlines(keepends=True)
        tree = ast.parse(raw)
        available = {getattr(node, "name", "") for node in tree.body}
        symbols = selector["symbols"]
        definitions = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if len(definitions) != len(set(definitions)):
            raise ValueError("ambiguous repair definitions")
        if symbols != "*" and not set(symbols) <= available:
            raise ValueError("required repair definition is missing")
        for node in tree.body:
            names = (
                [node.name]
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                else []
            )
            chosen = (
                symbols == "*"
                or bool(set(names) & set(symbols))
                or isinstance(node, (ast.Import, ast.ImportFrom))
                or (selector["constants"] and isinstance(node, (ast.Assign, ast.AnnAssign)))
                or (
                    isinstance(node, ast.If)
                    and isinstance(node.test, ast.Name)
                    and node.test.id == "TYPE_CHECKING"
                )
            )
            if chosen:
                start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
                rendered.append(
                    f"[{start}:{node.end_lineno}]\n"
                    + "".join(lines[start - 1 : node.end_lineno])
                    + "\n"
                )
    return "".join(rendered)


def repair_plan(diff, *, base_sha, head_sha, mission_id, mission_scope_sha256, repo_root):  # noqa: C901
    """按唯一固定表构造完整输入；首次派发前拒绝缺失或超限。"""
    # Local import avoids a cycle; this code is only selected for the exact repair.
    from scripts.devops.deepseek_review_chunks import (  # noqa: PLC0415
        Chunk,
        Manifest,
        _file_ranges,
        _range_paths,
        build_chunk_prompt,
        validate_manifest,
    )

    if mission_id != MISSION or base_sha != BASE:
        raise ValueError("fixed packets belong only to the approved repair and BASE")
    validate_sha(head_sha, name="repair head", length=40)
    validate_sha(mission_scope_sha256, name="repair scope", length=64)
    _git(repo_root, "merge-base", "--is-ancestor", base_sha, head_sha)
    actual = _git(repo_root, "diff", "--binary", "--no-ext-diff", base_sha + "..." + head_sha)
    if actual != diff:
        raise ValueError("repair canonical diff mismatch")
    raw_table, _ = _blob(repo_root, head_sha, TABLE)
    if raw_table is None or sha256_bytes(raw_table) != TABLE_SHA256:
        raise ValueError("unapproved repair fixed table")
    table = json.loads(raw_table)
    if table["mission_id"] != MISSION or table["base"] != BASE or table["version"] != VERSION:
        raise ValueError("fixed repair table identity mismatch")
    files = _file_ranges(diff)
    if tuple(
        dict.fromkeys(p for row in table["packets"] for p in [row["diff_path"]])
    ) != _range_paths(files, 0, len(diff)):
        raise ValueError("repair table does not cover the exact changed paths")
    sections = {paths[0]: (left, right) for left, right, paths in files if len(paths) == 1}
    if len(sections) != len(files):
        raise ValueError("repair does not allow rename/copy or ambiguous sections")
    positions = {path: left for path, (left, _) in sections.items()}
    chunks, contexts = [], []
    for index, packet in enumerate(table["packets"]):
        path = packet["diff_path"]
        left, right = positions[path], sections[path][1]
        if packet["diff_lines"] is not None:
            right = left + sum(
                map(len, diff[left:right].splitlines(keepends=True)[: packet["diff_lines"]])
            )
        if not 0 < right - left <= MAX_DIFF:
            raise ValueError("repair packet diff is empty or over capacity")
        contexts.append(
            (
                "Question: "
                + packet["question"]
                + "\n"
                + _sources(
                    repo_root,
                    base_sha,
                    head_sha,
                    [table["source_sets"][key] for key in packet["sources"]],
                )
            ).encode()
        )
        chunks.append(Chunk(index, left, right, sha256_bytes(diff[left:right]), (path,)))
        positions[path] = right
    if len(chunks) > MAX_COUNT or any(
        positions[path] != end for path, (_, end) in sections.items()
    ):
        raise ValueError("repair packets are incomplete or over count")
    manifest = Manifest(
        base_sha,
        head_sha,
        mission_id,
        mission_scope_sha256,
        sha256_bytes(diff),
        len(diff),
        tuple(chunks),
        _range_paths(files, 0, len(diff)),
        VERSION,
        raw_table,
        32000,
        tuple(contexts),
    )
    validate_manifest(manifest, diff)
    for chunk in chunks:
        prompt = build_chunk_prompt(
            chunk=chunk,
            source=diff[chunk.start : chunk.end],
            manifest=manifest,
            scope_sha=mission_scope_sha256,
        )
        if len(prompt.encode()) > MAX_PROMPT or "\0" in prompt:
            raise ValueError("repair final backend prompt exceeds capacity")
    return manifest
