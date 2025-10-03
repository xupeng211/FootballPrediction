from pathlib import Path
import os

from analyze_coverage import (
from unittest.mock import Mock, patch, mock_open
import pytest

"""
Unit tests for analyze_coverage.py
测试代码覆盖率和文件分析功能
"""

    analyze_source_files,
    count_lines_of_code,
    get_coverage_data,
    main)
class TestCountLinesOfCode:
    """测试代码行数计算功能"""
    def test_count_lines_of_code_valid_file(self, tmp_path):
        """测试正常文件的代码行数计算"""
        test_file = tmp_path / "test.py[": test_content = "]""#!/usr/bin/env python3[""""
# 这是一个测试文件
def test_function():
    # 函数注释
    x = 1
    y = 2
    return x + y
# 另一个注释
class TestClass:
    pass
"]"""
        test_file.write_text(test_content, encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_32"))": result = count_lines_of_code(str(test_file))"""
        # 应该排除空行和注释行，只计算实际代码行
        assert (
            result ==6
        )  # def + x=1 + y=2 + return + class + pass (shebang is treated as comment)
    def test_count_lines_of_code_empty_file(self, tmp_path):
        "]""测试空文件的代码行数计算"""
        test_file = tmp_path / "empty.py[": test_file.write_text("]", encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_32"))": result = count_lines_of_code(str(test_file))": assert result ==0[" def test_count_lines_of_code_comments_only(self, tmp_path):"
        "]]""测试只有注释的文件"""
        test_file = tmp_path / "comments.py[": test_content = "]""#!/usr/bin/env python3[""""
# 注释1
# 注释2
# 更多注释
"]"""
        test_file.write_text(test_content, encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_32"))": result = count_lines_of_code(str(test_file))": assert result ==0  # shebang 也被当作注释处理[" def test_count_lines_of_code_file_not_found(self):"
        "]]""测试不存在的文件"""
        result = count_lines_of_code("/nonexistent/file.py[")": assert result ==0[" def test_count_lines_of_code_mixed_content(self, tmp_path):""
        "]]""测试混合内容（代码、注释、空行）"""
        test_file = tmp_path / "mixed.py[": test_content = "]""#!/usr/bin/env python3[""""
# 文件头部注释
def function1():
    '''函数文档字符串'''
    x = 1  # 行内注释
    y = 2
    return x + y
# 函数间注释
def function2():
    pass
class TestClass:
    def method(self):
        '''方法文档'''
        return "]test["""""
"]"""
        test_file.write_text(test_content, encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_32"))": result = count_lines_of_code(str(test_file))"""
        # def + docstring(算代码) + x=1 + y=2 + return + def + pass + class + def + docstring + return
        assert result ==11
class TestGetCoverageData:
    "]""测试覆盖率数据获取功能"""
    @patch("subprocess.run[")": def test_get_coverage_data_success(self, mock_run):"""
        "]""测试成功获取覆盖率数据"""
        # 模拟 pytest 输出 - 使用正确的格式
        mock_output = """src/module1.py                             100      50      0    50%   1-20,30-40[": src/module2.py                             200     100      0    50%   10-30,50-70[": src/utils/helper.py                        150       75      0    50%   5-25[""
"]]]"""
        mock_result = Mock()
        mock_result.stdout = mock_output
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        result = get_coverage_data()
        expected = {
            "src/module1.py[": (100, 50, 50.0),""""
            "]src/module2.py[": (200, 100, 50.0),""""
            "]src/utils/helper.py[": (150, 75, 50.0)}": assert result ==expected["""
    @patch("]]subprocess.run[")": def test_get_coverage_data_empty_output(self, mock_run):"""
        "]""测试空输出的情况"""
        mock_result = Mock()
        mock_result.stdout = : 
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        result = get_coverage_data()
        assert result =={}
    @patch("subprocess.run[")": def test_get_coverage_data_malformed_output(self, mock_run):"""
        "]""测试格式错误的输出"""
        mock_result = Mock()
        mock_result.stdout = os.getenv("TEST_ANALYZE_COVERAGE_STDOUT_92")""""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        result = get_coverage_data()
        assert result =={}
    @patch("]subprocess.run[")": def test_get_coverage_data_subprocess_error(self, mock_run):"""
        "]""测试子进程错误"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = os.getenv("TEST_ANALYZE_COVERAGE_STDERR_100"): mock_result.stdout = "]"  # 确保stdout是字符串[": mock_run.return_value = mock_result[": result = get_coverage_data()": assert result =={}"
class TestAnalyzeSourceFiles:
    "]]""测试源文件分析功能"""
    @patch("analyze_coverage.Path[")": def test_analyze_source_files_success(self, mock_path_class):"""
        "]""测试成功分析源文件"""
        # 创建模拟的 Path 对象
        mock_src_dir = Mock()
        mock_path_class.return_value = mock_src_dir
        # 模拟文件列表
        mock_files = [
            Mock(name="file1.py[", relative_to=Mock(return_value=Path("]src/file1.py["))),": Mock(name = os.getenv("TEST_ANALYZE_COVERAGE_NAME_111"), relative_to=Mock(return_value=Path("]src/file2.py["))),": Mock(": name = os.getenv("TEST_ANALYZE_COVERAGE_NAME_114"),": relative_to=Mock(return_value=Path("]__pycache__/cache.py["))),  # 应该被跳过[""""
        ]
        mock_src_dir.rglob.return_value = mock_files
        # 模拟 count_lines_of_code 函数
        with patch("]]analyze_coverage.count_lines_of_code[") as mock_count:": mock_count.side_effect = [100, 200, 50]  # 最后一个应该被跳过[": result = analyze_source_files()""
            # 验证结果
            assert len(result) ==2  # __pycache__ 文件应该被跳过
            assert result[0]"]]file_path[" =="]src/file1.py[" assert result[0]"]loc[" ==100[" assert result[1]"]]file_path[" =="]src/file2.py[" assert result[1]"]loc[" ==200[""""
    @patch("]]analyze_coverage.Path[")": def test_analyze_source_files_no_files(self, mock_path_class):"""
        "]""测试没有文件的情况"""
        mock_src_dir = Mock()
        mock_path_class.return_value = mock_src_dir
        mock_src_dir.rglob.return_value = []
        result = analyze_source_files()
        assert result ==[]
    @patch("analyze_coverage.Path[")""""
    @patch("]analyze_coverage.count_lines_of_code[")": def test_analyze_source_files_count_error(self, mock_count, mock_path_class):"""
        "]""测试代码行数计算错误的情况"""
        mock_src_dir = Mock()
        mock_path_class.return_value = mock_src_dir
        mock_file = Mock(
            name="test.py[", relative_to=Mock(return_value=Path("]src/test.py["))""""
        )
        mock_src_dir.rglob.return_value = ["]mock_file["""""
        # 模拟 count_lines_of_code 返回0（错误情况）
        mock_count.return_value = 0
        result = analyze_source_files()
        assert len(result) ==1
        assert result[0]"]file_path[" =="]src/test.py[" assert result[0]"]loc[" ==0[" class TestMainFunction:"""
    "]]""测试主函数功能"""
    @patch("analyze_coverage.analyze_source_files[")""""
    @patch("]analyze_coverage.get_coverage_data[")""""
    @patch("]builtins.open[", new_callable=mock_open)""""
    @patch("]subprocess.run[")": def test_main_function_success(": self, mock_subprocess, mock_open, mock_get_coverage, mock_analyze[""
    ):
        "]]""测试主函数成功执行"""
        # 模拟源文件数据
        mock_files_data = [
            {"file_path[: "src/file1.py"", "loc["]},""""
            {"]file_path[: "src/file2.py"", "loc["]}]": mock_analyze.return_value = mock_files_data["""
        # 模拟覆盖率数据
        mock_coverage_data = {
            "]]src/file1.py[": (50, 25, 50.0),""""
            "]src/file2.py[": (100, 80, 20.0)}": mock_get_coverage.return_value = mock_coverage_data["""
        # 模拟文件写入
        mock_file = mock_open()
        # 模拟日期命令
        mock_date_result = Mock()
        mock_date_result.stdout = os.getenv("TEST_ANALYZE_COVERAGE_STDOUT_156"): mock_subprocess.return_value = mock_date_result[""""
        # 捕获打印输出
        with patch("]]builtins.print["):": result = main()"""
            # 验证结果
            assert len(result) ==2  # 返回 top 10 文件
            assert result[0]"]file_path[" =="]src/file2.py["  # 按覆盖率排序，20% 在前面[""""
            # 验证文件写入
            mock_open.assert_called()
            mock_file.write.assert_called()
    @patch("]]analyze_coverage.analyze_source_files[")""""
    @patch("]analyze_coverage.get_coverage_data[")""""
    @patch("]builtins.open[", new_callable=mock_open)""""
    @patch("]subprocess.run[")": def test_main_function_no_coverage_data(": self, mock_subprocess, mock_open, mock_get_coverage, mock_analyze[""
    ):
        "]]""测试没有覆盖率数据的情况"""
        mock_files_data = [
            {"file_path[: "src/file1.py"", "loc["]}""""
        ]
        mock_analyze.return_value = mock_files_data
        mock_get_coverage.return_value = {}  # 空的覆盖率数据
        mock_open()
        mock_date_result = Mock()
        mock_date_result.stdout = os.getenv("TEST_ANALYZE_COVERAGE_STDOUT_177"): mock_subprocess.return_value = mock_date_result[": with patch("]]builtins.print["):": result = main()"""
            # 验证没有覆盖率数据的文件被设置为0
            assert result[0]"]file_path[" =="]src/file1.py[" assert result[0]"]coverage[" ==0.0[" class TestIntegration:"""
    "]]""集成测试"""
    def test_full_workflow_with_real_files(self, tmp_path):
        """测试完整的工作流程（使用真实文件）"""
        # 创建临时测试文件
        test_dir = tmp_path / "src[": test_dir.mkdir()""""
        # 创建测试Python文件
        test_file1 = test_dir / "]file1.py[": test_file1.write_text(""""
            "]""#!/usr/bin/env python3[": def test_func():": return "]test["""""
"]"",": encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_32"))": test_file2 = test_dir / "]file2.py[": test_file2.write_text(""""
            "]""#!/usr/bin/env python3[""""
# 只有一个注释的文件
"]"",": encoding = os.getenv("TEST_ANALYZE_COVERAGE_ENCODING_32"))""""
        # 临时修改工作目录
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # 测试 analyze_source_files 函数
            with patch("]analyze_coverage.Path[") as mock_path:": mock_path.return_value = test_dir[": files_data = analyze_source_files()": assert len(files_data) ==2"
                assert any(f["]]file_path["].endswith("]file1.py[") for f in files_data)" assert any(f["]file_path["].endswith("]file2.py[") for f in files_data)" finally:"""
            os.chdir(original_cwd)
    def test_file_path_parsing_edge_cases(self):
        "]""测试文件路径解析的边界情况"""
        # 测试各种路径格式
        test_cases = [
            ("/path/to/file.py[", "]file.py["),""""
            ("]src/module/file.py[", "]src/module/file.py["),""""
            ("]deep/nested/path/file.py[", "]deep/nested/path/file.py[")]": for abs_path, expected_relative in test_cases:": with patch("]analyze_coverage.Path[") as mock_path:": mock_file = Mock()": mock_file.relative_to.return_value = Path(expected_relative)": mock_path.return_value.rglob.return_value = ["]mock_file[": with patch("]analyze_coverage.count_lines_of_code[", return_value = 10)": files_data = analyze_source_files()": if files_data:  # 只有当文件不在 __pycache__ 中时:": assert files_data[0]"]file_path[" ==expected_relative[" class TestErrorHandling:"""
    "]]""测试错误处理"""
    def test_count_lines_of_code_encoding_error(self, tmp_path):
        """测试文件编码错误"""
        test_file = tmp_path / "binary_file.py[": test_file.write_bytes(b["]\x00\x01\x02\x03["])  # 二进制内容[": result = count_lines_of_code(str(test_file))"""
        # 函数将二进制内容计为一行（没有换行符）
        assert result ==1
    @patch("]]subprocess.run[")": def test_get_coverage_data_timeout_error(self, mock_run):"""
        "]""测试子进程超时错误"""
        mock_run.side_effect = Exception("TimeoutExpired[")""""
        # 由于函数没有异常处理，预期会抛出异常
        with pytest.raises(Exception, match = os.getenv("TEST_ANALYZE_COVERAGE_MATCH_217"))": get_coverage_data()": def test_analyze_source_files_permission_error(self):""
        "]""测试文件权限错误"""
        with patch("analyze_coverage.Path[") as mock_path:": mock_src_dir = Mock()": mock_path.return_value = mock_src_dir[": mock_src_dir.rglob.side_effect = PermissionError("]]Permission denied[")""""
            # 由于函数没有异常处理，预期会抛出异常
            with pytest.raises(PermissionError, match = os.getenv("TEST_ANALYZE_COVERAGE_MATCH_224"))"]": analyze_source_files()