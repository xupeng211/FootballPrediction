#!/usr/bin/env python3
"""Git集成工具库."""

import subprocess
from pathlib import Path


class QuickGitManager:
    """快速Git管理器."""

    def __init__(self, repo_path="."):
        self.repo_path = Path(repo_path)

    def run_git(self, command):
        """运行Git命令."""
        cmd = ["git"] + command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                 cwd=self.repo_path, timeout=60)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def quick_commit(self, message, files=None):
        """快速提交."""
        if files:
            self.run_git(["add"] + files)
        else:
            self.run_git(["add", "."])

        return self.run_git(["commit", "-m", message])

    def quick_push(self, branch="main"):
        """快速推送."""
        return self.run_git(["push", "origin", branch])

def quick_git_commit(message, files=None):
    """快速Git提交."""
    git = QuickGitManager()
    return git.quick_commit(message, files)
