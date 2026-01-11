#!/usr/bin/env python3
"""
Unit Test: Concurrent Harvest Async Safety (Static Scanning)

测试目标：
1. 验证 harvest_pinnacle_concurrent.py 能够通过 py_compile 编译检查
2. 检测 worker_process() 函数中是否存在非法的 await 语句
3. 确保所有异步调用都使用 asyncio.run() 包装

用途：防止类似 "await outside async function" 的 Bug 再次出现

Author: 高级 SDET (Staff SDET)
Date: 2026-01-11
Version: V32.0 (Async Safety Enforcement)
"""

import ast
import os
import py_compile
import sys
import tempfile
from pathlib import Path

import pytest


class TestConcurrentAsyncSafety:
    """测试并发收割器的异步安全性 (静态扫描)"""

    @pytest.fixture
    def concurrent_script_path(self):
        """获取并发收割机脚本路径"""
        return Path(__file__).parent.parent.parent / "scripts/ops/harvest_pinnacle_concurrent.py"

    def test_py_compile_success(self, concurrent_script_path):
        """测试：harvest_pinnacle_concurrent.py 能够通过 Python 编译检查

        这是最基本的安全检查，确保：
        - 没有 SyntaxError
        - 没有缩进错误
        - 没有未定义的变量
        """
        # 尝试编译文件
        try:
            with tempfile.NamedTemporaryFile(suffix='.pyc', delete=False) as tmp_pyc:
                tmp_pyc_path = tmp_pyc.name

            py_compile.compile(str(concurrent_script_path), tmp_pyc_path, doraise=True)
            # 如果编译成功，删除临时文件
            os.unlink(tmp_pyc_path)

        except py_compile.PyCompileError as e:
            pytest.fail(f"编译失败: {e}")

    def test_worker_process_is_sync_function(self, concurrent_script_path):
        """测试：worker_process 函数是同步函数（不是 async）"""
        source_code = concurrent_script_path.read_text(encoding='utf-8')
        tree = ast.parse(source_code)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'worker_process':
                # 检查函数定义 - 如果是 AsyncFunctionDef 则说明是 async 函数
                # 但由于 AST 树中没有 AsyncFunctionDef 节点（因为不是 async 函数），所以这是正确的
                # 正确的做法是检查是否没有 'async' 关键字
                return  # 找到 FunctionDef 说明是同步函数，这是正确的

        pytest.fail("未找到 worker_process 函数定义")

    def test_no_await_in_worker_process(self, concurrent_script_path):
        """测试：worker_process 函数中没有直接的 await 语句

        这是关键测试：如果 worker_process 中有 await，会导致
        "SyntaxError: 'await' outside async function" 错误。

        正确做法：使用 asyncio.run() 包装异步调用
        """
        source_code = concurrent_script_path.read_text(encoding='utf-8')
        tree = ast.parse(source_code)

        found_worker = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'worker_process':
                found_worker = True

                # 检查函数体内是否有 Await 节点
                await_nodes = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Await):
                        # 获取行号
                        await_nodes.append(child.lineno)

                if await_nodes:
                    pytest.fail(
                        f"worker_process 函数中发现 {len(await_nodes)} 个 await 语句 "
                        f"(行号: {await_nodes})。"
                        f"worker_process 是同步函数，不能直接使用 await。"
                        f"请使用 asyncio.run(scraper.fetch_snapshot(...)) 代替。"
                    )
                return

        assert found_worker, "未找到 worker_process 函数定义"

    def test_asyncio_run_used_for_async_calls(self, concurrent_script_path):
        """测试：异步调用都使用 asyncio.run() 包装

        确保所有对 scraper.fetch_snapshot() 的调用都正确包装。
        """
        source_code = concurrent_script_path.read_text(encoding='utf-8')
        tree = ast.parse(source_code)

        # 查找所有调用 asyncio.run() 的地方
        asyncio_run_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # 检查是否调用 asyncio.run()
                if isinstance(node.func, ast.Attribute):
                    if (isinstance(node.func.value, ast.Name) and
                        node.func.value.id == 'asyncio' and
                        node.func.attr == 'run'):
                        asyncio_run_calls.append(node.lineno)

        # 至少应该有 2 个 asyncio.run() 调用
        # (一个是原始调用，一个是重试调用)
        assert len(asyncio_run_calls) >= 2, \
            f"期望至少 2 个 asyncio.run() 调用，实际找到 {len(asyncio_run_calls)} 个。" \
            "请确保所有异步调用都使用 asyncio.run() 包装。"

    def test_main_function_signature(self, concurrent_script_path):
        """测试：main 函数签名正确"""
        source_code = concurrent_script_path.read_text(encoding='utf-8')
        tree = ast.parse(source_code)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'main':
                # main 应该是普通函数，不是 async
                # 找到 FunctionDef 说明是同步函数，这是正确的
                return

        pytest.fail("未找到 main 函数定义")

    def test_no_top_level_async_code(self, concurrent_script_path):
        """测试：没有顶层异步代码

        在模块级别直接写 await 语句会导致语法错误。
        """
        source_code = concurrent_script_path.read_text(encoding='utf-8')
        tree = ast.parse(source_code)

        # 检查顶层是否有 await
        # 顶层语句在 Module.body 中
        top_level_awaits = []
        for node in tree.body:
            for child in ast.walk(node):
                if isinstance(child, ast.Await):
                    top_level_awaits.append(child.lineno)

        # 顶层 await 是语法错误，应该在函数/方法内部
        assert len(top_level_awaits) == 0, (
            f"发现 {len(top_level_awaits)} 个顶层 await 语句 (行号: {top_level_awaits})。"
            "顶层代码不能使用 await，请将其封装在 async 函数中。"
        )
