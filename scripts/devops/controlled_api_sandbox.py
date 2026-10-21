"""离线验收的真实网络隔离入口；无 bwrap/namespace 就拒绝，不退化为宿主执行。

lifecycle: permanent
只暴露代码、任务状态、单个 mock socket 和冻结 plan；不挂载 HOME、密钥或宿主网络。
这不是未来生产 broker 的认证或计费证明。
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from scripts.devops.controlled_api_policy import ControlError


def sandbox_command(
    project: Path, state: Path, plan: Path, mock_socket: Path, argv: list[str]
) -> list[str]:
    """生成显式 mount / unshare-all 命令；调用者不得传入真实凭据或生产 socket。"""
    binary = shutil.which("bwrap")
    if not binary:
        raise ControlError("NETWORK_ISOLATION_UNAVAILABLE")
    command = [
        binary,
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
        "--cap-drop",
        "ALL",
    ]
    for path in ("/usr", "/lib", "/lib64"):
        if Path(path).exists():
            command.extend(["--ro-bind", path, path])
    command.extend(
        [
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--dir",
            "/run",
            "--ro-bind",
            str(project.resolve(strict=True)),
            "/app",
            "--bind",
            str(state.resolve(strict=True)),
            "/run/state",
            "--ro-bind",
            str(plan.resolve(strict=True)),
            "/run/plan.json",
            "--ro-bind",
            str(mock_socket.resolve(strict=True)),
            "/run/mock.sock",
            "--chdir",
            "/app",
            "--setenv",
            "PYTHONPATH",
            "/app",
            "--setenv",
            "PYTHONDONTWRITEBYTECODE",
            "1",
            "--setenv",
            "PATH",
            "/usr/bin",
            "--setenv",
            "HOME",
            "/nonexistent",
            "--",
            "/usr/bin/python3",
            *argv,
        ]
    )
    return command


def run_offline(
    project: Path, state: Path, plan: Path, mock_socket: Path, task: str, slot: int
) -> subprocess.CompletedProcess:
    """只启动受控离线 Runner，环境白名单；失败返回非零并由 Controller 阻断。"""
    command = sandbox_command(
        project,
        state,
        plan,
        mock_socket,
        [
            "-m",
            "scripts.devops.controlled_api_runner",
            "--state-root",
            "/run/state",
            "--task",
            task,
            "--slot",
            str(slot),
            "--plan",
            "/run/plan.json",
            "--offline-socket",
            "/run/mock.sock",
        ],
    )
    return subprocess.run(command, env={}, capture_output=True, text=True, timeout=30, check=False)
