"""

"""





    """

    """

        """初始化导出管理器 / Initialize Export Manager"""


            "encoding": "utf-8",

        """


        """




            return json.dumps(error_data).encode(self.export_config["encoding"])

        """


        """


        """


        """




        return json_str.encode(self.export_config["encoding"])

        """


        """






        return csv_str.encode(self.export_config["encoding"])

        """


        """

    <meta charset="{self.export_config['encoding']}">
"""

""".format(datetime.now().isoformat())



        return html_content.encode(self.export_config["encoding"])

        """


        """




        return text_content.encode(self.export_config["encoding"])

        """


        """

        xml_content = f"""<?xml version="1.0" encoding="{self.export_config['encoding']}"?>
"""

"""



        return xml_content.encode(self.export_config["encoding"])

        """


        """




        """


        """




        """


        """




        """


        """





        """


        """


        """


        """




        """

        """

        """


        """





        """

        """

        """

        """




from datetime import datetime
import json
import csv
import io
from src.core.logging import get_logger

导出管理器
Export Manager
管理审计报告的导出功能。
logger = get_logger(__name__)
class ExportManager:
    导出管理器 / Export Manager
    提供多种格式的报告导出功能。
    Provides report export functionality in multiple formats.
    def __init__(self):
        self.logger = get_logger(f"audit.{self.__class__.__name__}")
        # 支持的导出格式
        self.supported_formats = {
            "json": "JSON格式",
            "csv": "CSV格式",
            "html": "HTML格式",
            "txt": "纯文本格式",
            "xml": "XML格式",
        }
        # 导出配置
        self.export_config = {
            "default_format": "json",
            "include_metadata": True,
            "pretty_print": True,
        }
    def export(
        self,
        report_data: Dict[str, Any],
        format: str = "json",
        **kwargs
    ) -> bytes:
        导出报告 / Export Report
        Args:
            report_data: 报告数据 / Report data
            format: 导出格式 / Export format
            **kwargs: 其他参数 / Other parameters
        Returns:
            bytes: 导出的数据 / Exported data
        try:
            # 验证格式
            if format not in self.supported_formats:
                raise ValueError(f"不支持的导出格式: {format}")
            # 获取导出器
            exporter = self._get_exporter(format)
            if not exporter:
                raise ValueError(f"无法找到 {format} 格式的导出器")
            # 执行导出
            exported_data = exporter(report_data, **kwargs)
            self.logger.info(f"报告已导出为 {format} 格式")
            return exported_data
        except Exception as e:
            self.logger.error(f"导出报告失败: {e}")
            # 返回错误信息
            error_data = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "format": format,
            }
    def _get_exporter(self, format: str):
        获取导出器 / Get Exporter
        Args:
            format: 格式 / Format
        Returns:
            Callable: 导出函数 / Export function
        exporters = {
            "json": self._export_json,
            "csv": self._export_csv,
            "html": self._export_html,
            "txt": self._export_text,
            "xml": self._export_xml,
        }
        return exporters.get(format)
    def _export_json(self, data: Dict[str, Any], **kwargs) -> bytes:
        导出为JSON / Export as JSON
        Args:
            data: 数据 / Data
            **kwargs: 其他参数 / Other parameters
        Returns:
            bytes: JSON数据 / JSON data
        pretty_print = kwargs.get("pretty_print", self.export_config["pretty_print"])
        include_metadata = kwargs.get("include_metadata", self.export_config["include_metadata"])
        # 准备导出数据
        export_data = data.copy()
        if include_metadata:
            export_data["export_metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "format": "json",
                "version": "1.0",
            }
        # 转换为JSON
        if pretty_print:
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
        else:
            json_str = json.dumps(export_data, ensure_ascii=False, default=str)
    def _export_csv(self, data: Dict[str, Any], **kwargs) -> bytes:
        导出为CSV / Export as CSV
        Args:
            data: 数据 / Data
            **kwargs: 其他参数 / Other parameters
        Returns:
            bytes: CSV数据 / CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        # 提取扁平化的数据
        flattened_data = self._flatten_dict(data)
        # 写入标题行
        headers = list(flattened_data.keys())
        writer.writerow(headers)
        # 写入数据行
        row = [flattened_data.get(header, "") for header in headers]
        writer.writerow(row)
        # 如果数据包含列表，需要处理多行
        if "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                if isinstance(item, dict):
                    item_flat = self._flatten_dict(item)
                    item_row = [item_flat.get(header, "") for header in headers]
                    writer.writerow(item_row)
        csv_str = output.getvalue()
        output.close()
    def _export_html(self, data: Dict[str, Any], **kwargs) -> bytes:
        导出为HTML / Export as HTML
        Args:
            data: 数据 / Data
            **kwargs: 其他参数 / Other parameters
        Returns:
            bytes: HTML数据 / HTML data
        title = kwargs.get("title", data.get("title", "审计报告"))
        include_metadata = kwargs.get("include_metadata", self.export_config["include_metadata"])
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            line-height: 1.6;
        }}
        .header {{
            background-color: #f4f4f4;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #007acc;
            padding-bottom: 5px;
        }}
        .metadata {{
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            font-size: 0.9em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        .json-content {{
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            white-space: pre-wrap;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
        # 添加元数据
        if include_metadata:
            html_content += """
    <div class="section metadata">
        <h2>导出信息</h2>
        <p>格式: HTML</p>
        <p>版本: 1.0</p>
        <p>导出时间: {}</p>
    </div>
        # 添加内容
        html_content += self._convert_dict_to_html(data)
        html_content += """
</body>
</html>"""
    def _export_text(self, data: Dict[str, Any], **kwargs) -> bytes:
        导出为纯文本 / Export as Text
        Args:
            data: 数据 / Data
            **kwargs: 其他参数 / Other parameters
        Returns:
            bytes: 文本数据 / Text data
        title = kwargs.get("title", data.get("title", "审计报告"))
        include_metadata = kwargs.get("include_metadata", self.export_config["include_metadata"])
        text_content = f"{title}\n"
        text_content += "=" * len(title) + "\n\n"
        text_content += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        if include_metadata:
            text_content += "导出信息:\n"
            text_content += "格式: 纯文本\n"
            text_content += "版本: 1.0\n"
            text_content += f"导出时间: {datetime.now().isoformat()}\n\n"
        # 添加内容
        text_content += self._convert_dict_to_text(data)
    def _export_xml(self, data: Dict[str, Any], **kwargs) -> bytes:
        导出为XML / Export as XML
        Args:
            data: 数据 / Data
            **kwargs: 其他参数 / Other parameters
        Returns:
            bytes: XML数据 / XML data
        root_tag = kwargs.get("root_tag", "audit_report")
        include_metadata = kwargs.get("include_metadata", self.export_config["include_metadata"])
<{root_tag}>
        if include_metadata:
            xml_content += f"""    <metadata>
        <exported_at>{datetime.now().isoformat()}</exported_at>
        <format>xml</format>
        <version>1.0</version>
    </metadata>
        # 添加内容
        xml_content += self._convert_dict_to_xml(data, indent=1)
        xml_content += f"</{root_tag}>"
    def _flatten_dict(self, data: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
        扁平化字典 / Flatten Dictionary
        Args:
            data: 数据字典 / Data dictionary
            parent_key: 父键名 / Parent key name
            sep: 分隔符 / Separator
        Returns:
            Dict[str, Any]: 扁平化的字典 / Flattened dictionary
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, sep=sep).items())
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        items.extend(self._flatten_dict(item, f"{new_key}{sep}{i}", sep=sep).items())
                    else:
                        items.append((f"{new_key}{sep}{i}", item))
            else:
                items.append((new_key, value))
        return dict(items)
    def _convert_dict_to_html(self, data: Dict[str, Any], level: int = 0) -> str:
        将字典转换为HTML / Convert Dictionary to HTML
        Args:
            data: 数据字典 / Data dictionary
            level: 嵌套级别 / Nesting level
        Returns:
            str: HTML内容 / HTML content
        html = ""
        for key, value in data.items():
            if key == "export_metadata":
                continue
            if isinstance(value, dict):
                heading_level = min(level + 2, 6)
                html += '<div class="section">\n'
                html += f'<h{heading_level}>{key}</h{heading_level}>\n'
                html += self._convert_dict_to_html(value, level + 1)
                html += '</div>\n'
            elif isinstance(value, list):
                html += '<div class="section">\n'
                html += f'<h{min(level + 2, 6)}>{key}</h{min(level + 2, 6)}>\n'
                html += '<ul>\n'
                for item in value:
                    if isinstance(item, dict):
                        html += '<li>' + self._convert_dict_to_html(item, level + 1) + '</li>\n'
                    else:
                        html += f'<li>{str(item)}</li>\n'
                html += '</ul>\n'
                html += '</div>\n'
            else:
                html += f'<p><strong>{key}:</strong> {str(value)}</p>\n'
        return html
    def _convert_dict_to_text(self, data: Dict[str, Any], level: int = 0) -> str:
        将字典转换为文本 / Convert Dictionary to Text
        Args:
            data: 数据字典 / Data dictionary
            level: 嵌套级别 / Nesting level
        Returns:
            str: 文本内容 / Text content
        text = ""
        indent = "  " * level
        for key, value in data.items():
            if key == "export_metadata":
                continue
            if isinstance(value, dict):
                text += f"\n{indent}{key}:\n"
                text += self._convert_dict_to_text(value, level + 1)
            elif isinstance(value, list):
                text += f"\n{indent}{key}:\n"
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        text += f"{indent}  [{i+1}]:\n"
                        text += self._convert_dict_to_text(item, level + 2)
                    else:
                        text += f"{indent}  - {str(item)}\n"
            else:
                text += f"{indent}{key}: {str(value)}\n"
        return text
    def _convert_dict_to_xml(self, data: Dict[str, Any], indent: int = 0) -> str:
        将字典转换为XML / Convert Dictionary to XML
        Args:
            data: 数据字典 / Data dictionary
            indent: 缩进级别 / Indent level
        Returns:
            str: XML内容 / XML content
        xml = ""
        indent_str = "    " * indent
        for key, value in data.items():
            if key == "export_metadata":
                continue
            # 清理键名，确保是有效的XML标签
            clean_key = str(key).replace(" ", "_").replace("-", "_")
            if not clean_key.isalnum() and "_" not in clean_key:
                clean_key = f"item_{clean_key}"
            if isinstance(value, dict):
                xml += f"{indent_str}<{clean_key}>\n"
                xml += self._convert_dict_to_xml(value, indent + 1)
                xml += f"{indent_str}</{clean_key}>\n"
            elif isinstance(value, list):
                xml += f"{indent_str}<{clean_key}>\n"
                for item in value:
                    if isinstance(item, dict):
                        xml += f"{indent_str}    <item>\n"
                        xml += self._convert_dict_to_xml(item, indent + 2)
                        xml += f"{indent_str}    </item>\n"
                    else:
                        xml += f"{indent_str}    <item>{self._escape_xml(str(item))}</item>\n"
                xml += f"{indent_str}</{clean_key}>\n"
            else:
                xml += f"{indent_str}<{clean_key}>{self._escape_xml(str(value))}</{clean_key}>\n"
        return xml
    def _escape_xml(self, text: str) -> str:
        转义XML特殊字符 / Escape XML Special Characters
        Args:
            text: 文本 / Text
        Returns:
            str: 转义后的文本 / Escaped text
        escape_table = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&apos;",
        }
        return "".join(escape_table.get(char, char) for char in text)
    def export_to_file(
        self,
        report_data: Dict[str, Any],
        filename: str,
        format: str = "json",
        **kwargs
    ) -> bool:
        导出到文件 / Export to File
        Args:
            report_data: 报告数据 / Report data
            filename: 文件名 / Filename
            format: 导出格式 / Export format
            **kwargs: 其他参数 / Other parameters
        Returns:
            bool: 是否成功 / Whether successful
        try:
            # 导出数据
            exported_data = self.export(report_data, format, **kwargs)
            # 写入文件
            with open(filename, 'wb') as f:
                f.write(exported_data)
            self.logger.info(f"报告已导出到文件: {filename}")
            return True
        except Exception as e:
            self.logger.error(f"导出到文件失败: {e}")
            return False
    def get_supported_formats(self) -> Dict[str, str]:
        获取支持的格式 / Get Supported Formats
        Returns:
            Dict[str, str]: 支持的格式字典 / Supported formats dictionary
        return self.supported_formats.copy()
    def validate_export_params(
        self,
        report_data: Dict[str, Any],
        format: str,
        **kwargs
    ) -> List[str]:
        验证导出参数 / Validate Export Parameters
        Args:
            report_data: 报告数据 / Report data
            format: 格式 / Format
            **kwargs: 其他参数 / Other parameters
        Returns:
            List[str]: 验证错误列表 / Validation errors list
        errors = []
        # 验证数据
        if not isinstance(report_data, dict):
            errors.append("报告数据必须是字典类型")
        # 验证格式
        if format not in self.supported_formats:
            errors.append(f"不支持的导出格式: {format}")
        # 验证文件名（如果提供）
        filename = kwargs.get("filename")
        if filename:
            if not isinstance(filename, str):
                errors.append("文件名必须是字符串类型")
            elif not filename.strip():
                errors.append("文件名不能为空")
        return errors
    def update_config(self, config: Dict[str, Any]) -> None:
        更新配置 / Update Configuration
        Args:
            config: 配置字典 / Configuration dictionary
        try:
            self.export_config.update(config)
            self.logger.info("导出配置已更新")
        except Exception as e:
            self.logger.error(f"更新导出配置失败: {e}")
    def get_config(self) -> Dict[str, Any]:
        获取配置 / Get Configuration
        Returns:
            Dict[str, Any]: 配置字典 / Configuration dictionary
        return self.export_config.copy()