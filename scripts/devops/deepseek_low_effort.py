"""Stage D 单轮四块审核的受信 Controller 接口及原件核验。

Lifecycle: permanent
Owner: engineering workflow governance
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha1
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from scripts.devops.deepseek_review_chunks import MAX_CHUNK_PROMPT_BYTES, validate_manifest
from scripts.devops.independent_review_backends import claude_code_deepseek as backend
from scripts.devops.independent_review_protocol import canonical_json, sha256_bytes

MISSION = "FP_STAGE_D_FORWARD_ACCOUNTING_RUNTIME"
VERSION = "independent-review-receipt/stage-d-low-v2"
HARNESS_REVISION = "f280615b10a44cc361ecc8cf01e86048d509acae"
CAPTURE_PATH = "scripts/devops/independent_review_backends/claude_code_deepseek.py"
POLICY_PATH = "scripts/devops/deepseek_low_effort.py"
CHUNKS = 4
LOW_INDEX = 1
MAX_RECORD = 16 * 1024 * 1024
PRIVATE_MODE = 0o600


def _check(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(f"Stage D supervised review: {reason}")


def _private(path: Path, *, directory=False) -> None:
    info = path.lstat()
    _check(
        (
            stat.S_ISDIR(info.st_mode)
            if directory
            else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        )
        and info.st_uid == os.getuid()
        and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600)
        and path.resolve(strict=True) == path,
        "private original required",
    )


def _read(path: Path) -> bytes:
    _check(path.resolve(strict=True) == path, "direct original required")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        _check(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and info.st_nlink == 1
            and stat.S_IMODE(info.st_mode) == PRIVATE_MODE
            and 0 < info.st_size <= MAX_RECORD,
            "invalid original metadata",
        )
        data = stream.read(info.st_size + 1)
        after = os.fstat(stream.fileno())
        _check(
            len(data) == info.st_size
            and after.st_mtime_ns == info.st_mtime_ns
            and path.lstat().st_ino == info.st_ino,
            "original changed during validation",
        )
        return data


def _record(path: Path, data: bytes) -> None:
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def frozen_target(worktree: Path, manifest, diff: bytes, prompts: list[bytes]) -> dict:
    """仅从准确 Git 派生输入；Controller 另行提供 Owner 已批准的冻结值。"""
    tree = subprocess.check_output(
        ["git", "rev-parse", "--verify", manifest.head_sha + "^{tree}"], cwd=worktree, text=True
    ).strip()
    validate_manifest(manifest, diff)
    _check(
        manifest.mission_id == MISSION and len(manifest.chunks) == len(prompts) == CHUNKS,
        "four mission chunks required",
    )
    _check(all(0 < len(p) <= MAX_CHUNK_PROMPT_BYTES for p in prompts), "invalid prompt size")
    return {
        "policy": VERSION,
        "mission": MISSION,
        "base": manifest.base_sha,
        "head": manifest.head_sha,
        "tree": tree,
        "scope_sha256": manifest.mission_scope_sha256,
        "diff_sha256": sha256_bytes(diff),
        "manifest_sha256": manifest.sha256,
        "backend": backend.BACKEND_ID,
        "model": backend.MODEL,
        "endpoint": backend.ENDPOINT,
        "starts": CHUNKS,
        "chunks": [
            {
                "index": c.index,
                "source_sha256": c.source_sha256,
                "prompt_sha256": sha256_bytes(p),
                "effort_request": ["low"] if c.index == LOW_INDEX else [],
            }
            for c, p in zip(manifest.chunks, prompts, strict=True)
        ],
    }


def _loaded_from(package: str, root: Path) -> bool:
    for name, module in tuple(sys.modules.items()):
        if name != package and not name.startswith(package + "."):
            continue
        file = getattr(module, "__file__", None)
        paths = [file] if file else tuple(getattr(module, "__path__", ()))
        if not paths or any(
            not Path(path).resolve(strict=True).is_relative_to(root) for path in paths
        ):
            return False
    return True


@dataclass(frozen=True)
class ToolOrigin:
    """由候选外 Controller 在导入任何项目模块前解析的物理工作区与已批准 BASE。"""

    candidate: Path
    project_base: str
    checkout: Path
    harness_checkout: Path

    def capture(self, expected_base: str) -> tuple[Path, str]:
        """保持两级启动信任；固定目标来自 BASE Git blob，文件路径不由已加载模块指定。"""
        # 只有已独立验证的 Controller 会预装此版本的 Harness。旧默认路径不依赖 Harness。
        from harness import adapters  # noqa: PLC0415

        _check(
            self.project_base == expected_base
            and re.fullmatch(r"[0-9a-f]{40}", expected_base) is not None
            and self.candidate == self.candidate.resolve(strict=True)
            and self.harness_checkout == self.harness_checkout.resolve(strict=True)
            and Path(adapters.__file__) == self.harness_checkout / "src/harness/adapters.py",
            "unverified tool origin",
        )
        adapter = adapters.FootballPredictionAdapter()
        git = adapter._trusted_git_output
        _check(
            git(self.harness_checkout, "rev-parse", "HEAD").strip() == HARNESS_REVISION,
            "unexpected Controller tool revision",
        )
        root = self.checkout
        _check(
            _loaded_from("scripts", root / "scripts")
            and _loaded_from("harness", self.harness_checkout / "src/harness"),
            "pre-import project or supervisor origin differs",
        )
        # 原 resolver 核验同库注册的干净 detached BASE 及全部脚本 blob。
        _check(
            adapter._trusted_base_checkout(str(self.candidate), expected_base) == root,
            "trusted registered checkout differs",
        )
        _check(
            root == root.resolve(strict=True)
            and root != self.candidate
            and Path(__file__) == root / POLICY_PATH
            and Path(backend.__file__) == root / CAPTURE_PATH
            and git(root, "rev-parse", "HEAD").strip() == expected_base,
            "project import origin differs",
        )
        helper = root / CAPTURE_PATH
        metadata = git(self.candidate, "ls-tree", expected_base, "--", CAPTURE_PATH).rstrip("\n")
        kind, path = metadata.split("\t", 1)
        mode, entry, oid = kind.split()
        _check(
            path == CAPTURE_PATH
            and mode == "100644"
            and entry == "blob"
            and helper.resolve(strict=True) == helper,
            "untrusted capture path",
        )
        with os.fdopen(
            os.open(helper, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb"
        ) as stream:
            info = os.fstat(stream.fileno())
            _check(
                stat.S_ISREG(info.st_mode) and 0 < info.st_size <= MAX_RECORD,
                "invalid capture metadata",
            )
            raw = stream.read(info.st_size + 1)
        observed = sha1(f"blob {len(raw)}\0".encode() + raw, usedforsecurity=False).hexdigest()
        _check(
            len(raw) == info.st_size and observed == oid, "capture differs from approved BASE blob"
        )
        return helper, sha256_bytes(raw)


def verified_capture(pilot: LowReview, base: str) -> tuple[Path, str]:
    """核对接收凭据的监督方法及停止校验器，再返回可信 BASE 的固定捕获程序。"""
    from harness.appserver_process import validate_supervised_stop  # noqa: PLC0415
    from harness.factory_runtime import LocalRuntime  # noqa: PLC0415

    _check(
        type(pilot) is LowReview and type(pilot.origin) is ToolOrigin,
        "unverified Controller context",
    )
    method = pilot.supervise
    _check(
        type(getattr(method, "__self__", None)) is LocalRuntime
        and getattr(method, "__func__", None) is LocalRuntime._supervised_review_step
        and pilot.verify_stop is validate_supervised_stop,
        "unverified Controller methods",
    )
    return pilot.origin.capture(base)


@dataclass(frozen=True)
class LowReview:
    """仅由候选外可信 Controller 构造；无 CLI、配置文件或 receipt 转对象的入口。

    supervise 为已安装 Harness LocalRuntime 的 _supervised_review_step；
    verify_stop 为该 Harness 的 validate_supervised_stop。trusted_dir 是该批准专用
    的外部私有目录，run_id、evidence_dir 和 approved_target 为批准时冻结的值。
    """

    run_id: str
    trusted_dir: Path
    evidence_dir: Path
    approved_target: bytes
    supervise: Callable
    verify_stop: Callable
    origin: ToolOrigin

    def target(self) -> dict:
        """核对私有目录与冻结的批准输入。"""
        _check(re.fullmatch(r"[0-9a-f]{32}", self.run_id) is not None, "invalid run id")
        for directory in (self.trusted_dir, self.evidence_dir):
            _private(directory, directory=True)
            _check(
                not directory.is_relative_to(Path(__file__).resolve().parents[2]),
                "external Controller directories required",
            )
        _check(
            not self.trusted_dir.is_relative_to(self.evidence_dir)
            and not self.evidence_dir.is_relative_to(self.trusted_dir),
            "separate Controller originals required",
        )
        target = json.loads(self.approved_target)
        _check(canonical_json(target) == self.approved_target, "noncanonical approval")
        return target

    def check_inputs(self, root, manifest, diff, prompts) -> None:
        """逐字节匹配 Owner 批准的输入与本次重建。"""
        verified_capture(self, self.target()["base"])
        _check(
            self.target() == frozen_target(root, manifest, diff, prompts), "approved inputs differ"
        )
        _check(
            not self.trusted_dir.is_relative_to(root.resolve())
            and not self.evidence_dir.is_relative_to(root.resolve()),
            "external evidence required",
        )

    def claim(self) -> None:
        """以唯一批准目录独占消耗整轮启动许可。"""
        # 原子消耗整轮批准。错误或崩溃也不移除此标记，不自动重开。
        _record(self.trusted_dir / "claimed.json", self.approved_target)

    def worktree(self) -> Path:
        """用批准的运行号和 HEAD 绑定保留工作区。"""
        return (
            self.evidence_dir
            / f"claude-deepseek-worktree-{self.target()['head'][:12]}-{self.run_id}"
        )

    def _paths(self, index: int) -> tuple[Path, Path]:
        _check(type(index) is int and 0 <= index < CHUNKS, "invalid chunk position")
        return self.trusted_dir / f"chunk-{index}.stdout", self.trusted_dir / f"chunk-{index}.seal"

    def _binding(self, index, command, cwd) -> dict:
        target = self.target()
        transcript, _ = self._paths(index)
        spec = target["chunks"][index]
        _check(
            cwd == self.worktree()
            and cwd.resolve(strict=True) == cwd
            and spec["index"] == index
            and sha256_bytes(command[-1].encode()) == spec["prompt_sha256"],
            "command target mismatch",
        )
        binary, binary_sha = backend._approved_claude_binary(command[0])
        home = Path(command[command.index("--settings") + 1]).parent
        runtime = self.evidence_dir / f"claude-deepseek-runtime-{target['head'][:12]}-{self.run_id}"
        _private(runtime, directory=True)
        _private(home, directory=True)
        settings = home / "settings.json"
        _check(
            home.parent == runtime
            and _read(settings) == backend.DEDICATED_SETTINGS
            and command == backend.reviewer_command(binary, settings, command[-1]),
            "noncanonical client inputs",
        )
        helper, digest = verified_capture(self, target["base"])
        _check(not helper.is_relative_to(cwd), "trusted adapter must be outside reviewed candidate")
        args = [
            sys.executable,
            "-I",
            "-B",
            str(helper),
            "--capture-supervised",
            binary_sha,
            *command,
        ]
        return {
            "argv": args,
            "cwd": str(cwd),
            "run": self.run_id,
            "chunk_index": index,
            "effort_request": spec["effort_request"],
            "target_sha256": sha256_bytes(self.approved_target),
            "adapter_sha256": digest,
            "tool_base": self.origin.project_base,
            "supervisor_revision": HARNESS_REVISION,
            "transcript": str(transcript),
        }

    def run_client(self, index, command, cwd, env, timeout) -> subprocess.CompletedProcess:
        """在固定批准下调用受监护的凭据过滤器，先验同次停止再读取输出。"""
        binding = self._binding(index, command, cwd)
        transcript, _ = self._paths(index)
        _check(_read(self.trusted_dir / "claimed.json") == self.approved_target, "unclaimed round")
        if index:
            _read(self._paths(index - 1)[1])  # 上一个 seal 只在证停、原件与强度均通过后写入。
        _record(self.trusted_dir / f"chunk-{index}.started", canonical_json(binding))
        expected_env = backend.child_environment(env["ANTHROPIC_API_KEY"])
        expected_env["HOME"] = str(Path(command[command.index("--settings") + 1]).parent)
        _check(env == expected_env, "noncanonical client environment")
        if index == LOW_INDEX:
            env["CLAUDE_CODE_EFFORT_LEVEL"] = "low"
        try:
            code, reference = self.supervise(
                binding, binding["argv"], cwd, env, transcript, timeout
            )
            stop_path = transcript.with_suffix(".stdout.stop.json")
            _check(
                reference["path"] == str(stop_path)
                and self.verify_stop(reference, binding) == code == 0,
                "unconfirmed client tree",
            )
        except Exception as exc:
            raise ValueError("Stage D supervision incomplete; retained originals") from exc
        _record(self.trusted_dir / f"chunk-{index}.stop-ref", canonical_json(reference))
        record = self._observed_process(index, command, cwd)
        if record["returncode"]:
            raise backend.BackendInfrastructureError(
                f"CLI_RUNTIME_FAILURE: {record['error_class']}"
            )
        return subprocess.CompletedProcess(
            command, 0, base64.b64decode(record["stdout"], validate=True), b""
        )

    def _observed_process(self, index, command, cwd) -> dict:
        transcript, _ = self._paths(index)
        binding = self._binding(index, command, cwd)
        _check(
            _read(self.trusted_dir / f"chunk-{index}.started") == canonical_json(binding),
            "start binding changed",
        )
        ref = json.loads(_read(self.trusted_dir / f"chunk-{index}.stop-ref"))
        stop_path = transcript.with_suffix(".stdout.stop.json")
        _check(
            ref["path"] == str(stop_path) and self.verify_stop(ref, binding) == 0,
            "stop binding changed",
        )
        process = json.loads(_read(stop_path))["payload"]
        record = json.loads(_read(transcript))
        _check(
            record["parent_pid"] == process["pid"]
            and record["parent_starttime"] == int(process["starttime"])
            and record["pid"] != process["pid"]
            and type(record["pid"]) is int
            and record["pid"] > 0
            and type(record["starttime"]) is int
            and record["starttime"] >= int(process["starttime"])
            and record["cwd"] == str(cwd)
            and record["effort_request"] == binding["effort_request"],
            "supervised client identity/effort mismatch",
        )
        return record

    def check_chunk(self, index, item, *, seal: bool) -> dict:
        """从独立的同次进程与客户端原件核实已执行的一块。"""
        execution = item["execution"]
        command = execution.reviewer_command
        cwd = self.worktree()
        _check(_read(self.trusted_dir / "claimed.json") == self.approved_target, "claim changed")
        record = self._observed_process(index, command, cwd)
        _check(
            record["returncode"] == 0
            and base64.b64decode(record["stdout"], validate=True) == item["raw"],
            "supervised raw output mismatch",
        )
        _, binary_sha = backend._approved_claude_binary(command[0])
        _check(
            binary_sha == execution.claude_binary_sha256
            and execution.settings_sha256 == sha256_bytes(backend.DEDICATED_SETTINGS),
            "client provenance mismatch",
        )
        home = Path(command[command.index("--settings") + 1]).parent
        observed = backend._observe_client_effort(
            home, item["prompt"].decode(), cwd, execution.session_id, strict=True
        )
        level = observed["observed_client_effort"]
        _check(
            level in backend._CLIENT_EFFORT_LEVELS and (index != LOW_INDEX or level == "low"),
            "unexpected client effort",
        )
        transcript, path = self._paths(index)
        facts = {
            "index": index,
            "session": execution.session_id,
            "trace": observed["trace_sha256"],
            "level": level,
            "source": item["source_sha256"],
            "prompt": sha256_bytes(item["prompt"]),
            "raw": sha256_bytes(item["raw"]),
            "final": sha256_bytes(item["final"]),
            "transcript": sha256_bytes(_read(transcript)),
            "run": self.run_id,
            "stop_reference": sha256_bytes(_read(self.trusted_dir / f"chunk-{index}.stop-ref")),
        }
        payload = canonical_json(facts)
        if seal:
            _check(
                all(
                    json.loads(_read(self._paths(previous)[1]))["session"] != execution.session_id
                    for previous in range(index)
                ),
                "duplicate client session",
            )
            _record(path, payload)
        else:
            _check(_read(path) == payload, "retained originals differ from Controller binding")
        return facts
