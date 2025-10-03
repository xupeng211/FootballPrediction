from pathlib import Path
from typing import Dict, List
import os
import sys

from unittest.mock import Mock, patch, mock_open
import pytest
import xml.etree.ElementTree

from analyze_coverage_precise import (
    analyze_source_files,
    count_lines_of_code,
    parse_coverage_xml,
    main
)

"""
Unit tests for analyze_coverage_precise.py
测试精确的代码覆盖率和文件分析功能
"""
class TestCountLinesOfCodePrecise:
    """测试精确代码行数计算功能"""
    def test_count_lines_of_code_with_docstrings(self, tmp_path):
        """测试包含文档字符串的文件"""
        test_file = tmp_path / "test.py[": test_content = "]""#!/usr/bin/env python3[""""
'''模块文档字符串'''
def function_with_docstring():
    '''函数文档字符串'''
    x = 1
    return x
class TestClass:
    '''类文档字符串'''
    def method(self):
        '''方法文档字符串'''
        pass
"]"""
        test_file.write_text(test_content, encoding="utf-8[")": result = count_lines_of_code(str(test_file))"""
        # 文档字符串算作代码行（因为不以#开头）
        assert (
            result ==10
        )  # shebang + module docstring + def + func docstring + x=1 + return + class + class docstring + def + method docstring + pass
    def test_count_lines_of_code_complex_file(self, tmp_path):
        "]""测试复杂文件结构"""
        test_file = tmp_path / "complex.py[": test_content = "]""#!/usr/bin/env python3[""""
# 导入语句
import os
import sys
from typing import Dict, List
# 常量定义
MAX_SIZE = 100
def calculate_sum(a: "]int[", b: int) -> int:""""
    '''计算两个数的和'''
    return a + b
class DataProcessor:
    '''数据处理器类'''
    def __init__(self, data: List):
        self.data = data
    def process(self) -> Dict:
        '''处理数据'''
        if not self.data:
            return {}
        result = {}
        for item in self.data = key str(item)
            result["]key[" = item[": return result["""
# 全局变量
global_config = {"]]]debug[" : True}": if __name__ =="]__main__[":""""
    : print("]测试脚本[")""""
"]"""
        test_file.write_text(test_content, encoding="utf-8[")": result = count_lines_of_code(str(test_file))"""
        # 排除空行和注释行
        expected_lines = 23  # 所有非空非注释行
        assert result ==expected_lines
class TestParseCoverageXml:
    "]""测试XML覆盖率解析功能"""
    @patch("builtins.open[", new_callable=mock_open)""""
    @patch("]analyze_coverage_precise.ET.parse[")": def test_parse_coverage_xml_success(self, mock_parse, mock_file):"""
        "]""测试成功解析coverage.xml"""
        # 创建模拟的XML结构
        mock_root = Mock()
        mock_package = Mock()
        mock_class1 = Mock()
        mock_class2 = Mock()
        # 设置class属性
        mock_class1.get.side_effect = lambda key, default=None {
            "filename[: "src/module1.py[","]"""
            "]line-rate[": "]0.8[",""""
            "]lines-covered[: "80[","]"""
            "]lines-valid[: "100["}.get(key, default)"]": mock_class2.get.side_effect = lambda key, default=None {""
            "]filename[: "src/module2.py[","]"""
            "]line-rate[": "]0.5[",""""
            "]lines-covered[: "50[","]"""
            "]lines-valid[: "100["}.get(key, default)"]"""
        # 设置查找结果
        mock_package.findall.return_value = ["]mock_class1[", mock_class2]": mock_root.findall.return_value = ["]mock_package["]": mock_tree = Mock()": mock_tree.getroot.return_value = mock_root[": mock_parse.return_value = mock_tree"
        result = parse_coverage_xml()
        expected = {
            "]]src/module1.py[": (100, 20, 80.0),""""
            "]src/module2.py[": (100, 50, 50.0)}": assert result ==expected["""
    @patch("]]builtins.open[", side_effect=FileNotFoundError)": def test_parse_coverage_xml_file_not_found(self, mock_file):"""
        "]""测试coverage.xml文件不存在"""
        result = parse_coverage_xml()
        assert result =={}
    @patch("builtins.open[", new_callable=mock_open)""""
    @patch("]analyze_coverage_precise.ET.parse[")": def test_parse_coverage_xml_xml_error(self, mock_parse, mock_file):"""
        "]""测试XML解析错误"""
        mock_parse.side_effect = ET.ParseError("Invalid XML[")": result = parse_coverage_xml()": assert result =={}""
    @patch("]builtins.open[", new_callable=mock_open)""""
    @patch("]analyze_coverage_precise.ET.parse[")": def test_parse_coverage_xml_invalid_data(self, mock_parse, mock_file):"""
        "]""测试无效的XML数据"""
        mock_root = Mock()
        mock_class = Mock()
        mock_class.get.side_effect = lambda key, default=None {
            "filename[: "invalid.py[",  # 不以src/开头["]"]""
            "]line-rate[": ["]invalid[",  # 无效的数字[""""
            "]]lines-covered[": ["]invalid[",""""
            "]lines-valid[": ["]invalid["}.get(key, default)": mock_package = Mock()": mock_package.findall.return_value = ["]mock_class["]": mock_root.findall.return_value = ["]mock_package["]": mock_tree = Mock()": mock_tree.getroot.return_value = mock_root[": mock_parse.return_value = mock_tree"
        result = parse_coverage_xml()
        # 应该跳过无效数据
        assert result =={}
    @patch("]]builtins.open[", new_callable=mock_open)""""
    @patch("]analyze_coverage_precise.ET.parse[")": def test_parse_coverage_xml_missing_attributes(self, mock_parse, mock_file):"""
        "]""测试缺失必要属性的XML元素"""
        mock_root = Mock()
        mock_class = Mock()
        mock_class.get.side_effect = lambda key, default=None {
            "filename[: "src/test.py[","]"""
            # 缺失其他属性
        }.get(key, default)
        mock_package = Mock()
        mock_package.findall.return_value = ["]mock_class["]": mock_root.findall.return_value = ["]mock_package["]": mock_tree = Mock()": mock_tree.getroot.return_value = mock_root[": mock_parse.return_value = mock_tree"
        result = parse_coverage_xml()
        # 应该使用默认值
        assert "]]src/test.py[" in result[""""
        total_stmts, missing_stmts, coverage = result["]]src/test.py["]": assert total_stmts ==0[" assert missing_stmts ==0[""
        assert coverage ==0.0
class TestAnalyzeSourceFilesPrecise:
    "]]]""测试精确源文件分析功能"""
    @patch("analyze_coverage_precise.Path[")""""
    @patch("]analyze_coverage_precise.count_lines_of_code[")": def test_analyze_source_files_with_various_files(self, mock_count, mock_path_class):"""
        "]""测试分析各种类型的源文件"""
        mock_src_dir = Mock()
        mock_path_class.return_value = mock_src_dir
        # 模拟不同类型的文件
        mock_files = [
            Mock(
                name="normal.py[",": __str__=Mock(": return_value="]/home/user/projects/FootballPrediction/src/normal.py[": )),": Mock(": name="]test.py[",": __str__=Mock(": return_value="]/home/user/projects/FootballPrediction/src/test.py[": )),": Mock(": name="]__init__.py[",": __str__=Mock(": return_value="]/home/user/projects/FootballPrediction/src/__init__.py[": )),": Mock(": name="]cache.py[",": __str__=Mock(": return_value="]/home/user/projects/FootballPrediction/__pycache__/cache.py[": )),  # 应该被跳过[""""
        ]
        mock_src_dir.rglob.return_value = mock_files
        # 设置 relative_to 方法
        for mock_file in mock_files:
            mock_file.relative_to = Mock(
                return_value=Path(
                    mock_file.__str__().replace(
                        "]]/home/user/projects/FootballPrediction/", : """"
                    )
                )
            )
        # 模拟代码行数计算
        mock_count.side_effect = [100, 50, 10, 30]  # 最后一个应该被跳过
        result = analyze_source_files()
        assert len(result) ==3  # __pycache__ 文件应该被跳过
        assert result[0]"loc[" ==100[" assert result[1],"]]loc[" ==50[" assert result[2]"]]loc[" ==10[""""
    @patch("]]analyze_coverage_precise.Path[")": def test_analyze_source_files_empty_directory(self, mock_path_class):"""
        "]""测试空目录"""
        mock_src_dir = Mock()
        mock_path_class.return_value = mock_src_dir
        mock_src_dir.rglob.return_value = []
        result = analyze_source_files()
        assert result ==[]
class TestMainFunctionPrecise:
    """测试精确分析的主函数"""
    @patch("analyze_coverage_precise.analyze_source_files[")""""
    @patch("]analyze_coverage_precise.parse_coverage_xml[")""""
    @patch("]builtins.open[", new_callable=mock_open)""""
    @patch("]subprocess.run[")": def test_main_function_with_filtering(": self, mock_subprocess, mock_open, mock_parse_xml, mock_analyze[""
    ):
        "]]""测试带过滤功能的主函数"""
        # 模拟源文件数据
        mock_files_data = [
            {"file_path[: "src/file1.py"", "loc["]},""""
            {"]file_path[: "src/file2.py"", "loc["]},""""
            {"]file_path[: "src/empty.py"", "loc["]}]": mock_analyze.return_value = mock_files_data["""
        # 模拟覆盖率数据（包含语句数为0的文件）
        mock_coverage_data = {
            "]]src/file1.py[": (50, 25, 50.0),""""
            "]src/file2.py[": (100, 80, 20.0),""""
            "]src/empty.py[": (0, 0, 0.0),  # 语句数为0，应该被过滤掉[""""
        }
        mock_parse_xml.return_value = mock_coverage_data
        mock_open()
        mock_date_result = Mock()
        mock_date_result.stdout = "]]2025-09-27 12:0000[": mock_subprocess.return_value = mock_date_result[": with patch("]]builtins.print["):": result = main()"""
            # 验证结果被过滤（empty.py应该被过滤掉）
            assert len(result) ==2
            assert all(item["]total_stmts["] > 0 for item in result)""""
    @patch("]analyze_coverage_precise.analyze_source_files[")""""
    @patch("]analyze_coverage_precise.parse_coverage_xml[")""""
    @patch("]builtins.open[", new_callable=mock_open)""""
    @patch("]subprocess.run[")": def test_main_function_statistics_calculation(": self, mock_subprocess, mock_open, mock_parse_xml, mock_analyze[""
    ):
        "]]""测试统计计算功能"""
        mock_files_data = [
            {"file_path[: "src/file1.py"", "loc["]},""""
            {"]file_path[: "src/file2.py"", "loc["]}]": mock_analyze.return_value = mock_files_data[": mock_coverage_data = {""
            "]]src/file1.py[": (50, 25, 50.0),  # 50语句，50%覆盖率[""""
            "]]src/file2.py[": (100, 80, 20.0),  # 100语句，20%覆盖率[""""
        }
        mock_parse_xml.return_value = mock_coverage_data
        mock_open()
        mock_date_result = Mock()
        mock_date_result.stdout = "]]2025-09-27 12:0000[": mock_subprocess.return_value = mock_date_result[": with patch("]]builtins.print[") as mock_print:": main()"""
            # 验证统计数据正确
            calls = mock_print.call_args_list
            stats_found = False
            for call in calls:
                if "]总体统计:": in str(call):": stats_found = True[": break[": assert stats_found, "]]应该输出总体统计信息["""""
    @patch("]analyze_coverage_precise.analyze_source_files[")""""
    @patch("]analyze_coverage_precise.parse_coverage_xml[")""""
    @patch("]builtins.open[", new_callable=mock_open)""""
    @patch("]subprocess.run[")": def test_main_function_impact_score_calculation(": self, mock_subprocess, mock_open, mock_parse_xml, mock_analyze[""
    ):
        "]]""测试影响分数计算"""
        mock_files_data = [
            {
                "file_path[: "src/high_impact.py[","]"""
                "]loc[": 1000,""""
                "]abs_path[: "/abs/path/high_impact.py["}"]"""
        ]
        mock_analyze.return_value = mock_files_data
        mock_coverage_data = {
            "]src/high_impact.py[": (500, 400, 20.0)  # 1000行代码，20%覆盖率[""""
        }
        mock_parse_xml.return_value = mock_coverage_data
        mock_open()
        mock_date_result = Mock()
        mock_date_result.stdout = "]]2025-09-27 12:0000[": mock_subprocess.return_value = mock_date_result[": with patch("]]builtins.print[") as mock_print:": main()"""
            # 验证影响分数被计算和显示
            calls = mock_print.call_args_list
            impact_score_found = False
            for call in calls:
                if "]影响分数:": in str(call):": impact_score_found = True[": break[": assert impact_score_found, "]]应该计算并显示影响分数["""""
: class TestIntegrationPrecise:
    "]""精确分析的集成测试"""
    def test_precise_analysis_workflow(self, tmp_path):
        """测试精确分析工作流程"""
        # 创建模拟的coverage.xml文件
        coverage_xml = tmp_path / "coverage.xml[": xml_content = "]""<?xml version="1.0[" ?>""""
<coverage version="]6.0[": line-rate="]0.75[": branch-rate="]0.65[">""""
    <packages>
        <package name="]src[" "]: "line-rate="0.75[": branch-rate="]0.65[">""""
            <classes>
                <class name="]test_module," ": "filename="src/test_module.py[": line-rate="]0.8[": branch-rate="]0.7[": lines-covered="]4[" "]: "lines-valid="5[">""""
                    <methods>
                        <method name="]test_function," ": "line-rate="1.0[": branch-rate="]1.0[">""""
                            <lines>
                                <line number="]1[" "]: "hits="1["/>""""
                                <line number="]2," ": "hits="1["/>""""
                            </lines>
                        </method>
                    </methods>
                    <lines>
                        <line number="]1[" "]: "hits="1["/>""""
                        <line number="]2," ": "hits="1["/>""""
                        <line number="]3[" "]: "hits="0["/>""""
                        <line number="]4," ": "hits="1["/>""""
                        <line number="]5[" "]: "hits="1["/>""""
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>"]"""
        coverage_xml.write_text(xml_content, encoding="utf-8[")""""
        # 测试XML解析
        with patch("]analyze_coverage_precise.Path[", new = tmp_path)": with patch("]builtins.open[", mock_open(read_data = xml_content))": result = parse_coverage_xml()": assert "]src/test_module.py[" in result[""""
                total_stmts, missing_stmts, coverage = result["]]src/test_module.py["]: assert total_stmts ==5[" assert missing_stmts ==1["""
                assert coverage ==80.0
    def test_file_filtering_logic(self):
        "]]]""测试文件过滤逻辑"""
        test_files = [
            {"file_path[: "src/valid.py"", "total_stmts["]: 100},""""
            {"]file_path[: "src/empty.py"", "total_stmts["]: 50},  # 应该被过滤[""""
            {"]]file_path[: "src/another.py"", "total_stmts["]: 200}]""""
        # 模拟过滤逻辑
        filtered = [item for item in test_files if item["]total_stmts["]: > 0]": assert len(filtered) ==2[" assert all(item["]]total_stmts["] > 0 for item in filtered)" assert not any(item["]file_path["] =="]src/empty.py[" for item in filtered)""""
    def test_sorting_logic(self):
        "]""测试排序逻辑"""
        test_data = [
            {,"coverage[": 80.0, "]loc[": 100, "]total_stmts[": 50},""""
            {"]coverage[": 20.0, "]loc[": 200, "]total_stmts[": 100},""""
            {"]coverage[": 20.0, "]loc[": 300, "]total_stmts[": 150},  # 相同覆盖率，更高行数[""""
            {"]]coverage[": 50.0, "]loc[": 150, "]total_stmts[": 75}]""""
        # 应用排序逻辑：覆盖率低 -> 文件行数大 -> 语句数大
        sorted_data = sorted(
            test_data, key = lambda x (x["]coverage["], -x["]loc["], -x["]total_stmts["])""""
        )
        # 验证排序结果
        assert sorted_data[0]"]coverage[" ==20.0[" assert sorted_data[0],"]]loc[" ==300  # 相同覆盖率中行数最大的[" assert sorted_data[1]"]]coverage[" ==20.0[" assert sorted_data[1],"]]loc[" ==200[" assert sorted_data[2]"]]coverage[" ==50.0[" assert sorted_data[3]"]]coverage[" ==80.0[" class TestErrorHandlingPrecise:"""
    "]]""精确分析的错误处理测试"""
    @patch("builtins.open[", side_effect=PermissionError("]Permission denied["))": def test_parse_coverage_xml_permission_error(self, mock_file):"""
        "]""测试文件权限错误"""
        result = parse_coverage_xml()
        assert result =={}
    @patch("analyze_coverage_precise.ET.parse[")": def test_parse_coverage_xml_corrupted_xml(self, mock_parse):"""
        "]""测试损坏的XML文件"""
        mock_parse.side_effect = ET.ParseError("XML syntax error[")": with patch("]builtins.open[", mock_open()):": result = parse_coverage_xml()": assert result =={}" def test_count_lines_of_code_unicode_error(self, tmp_path):"
        "]""测试Unicode编码错误"""
        test_file = tmp_path / "unicode_file.py["""""
        # 写入一些可能导致编码问题的内容
        test_file.write_bytes(b["]\xff\xfe\x00\x41\x00\x42\x00\x43["])  # UTF-16 BOM[": result = count_lines_of_code(str(test_file))": assert result ==0[""
    @patch("]]]analyze_coverage_precise.Path[")": def test_analyze_source_files_path_error(self, mock_path_class):"""
        "]""测试路径处理错误"""
        mock_src_dir = Mock()
        mock_path_class.return_value = mock_src_dir
        # 模拟relative_to方法抛出异常
        mock_file = Mock(name="test.py[")": mock_file.relative_to.side_effect = ValueError("]Path not relative[")": mock_src_dir.rglob.return_value = ["]mock_file[": # 函数没有处理ValueError异常，预期会抛出异常[": with pytest.raises(ValueError, match = "]]Path not relative[")"]": analyze_source_files()