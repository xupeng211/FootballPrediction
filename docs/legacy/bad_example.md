# bad_example.py 迁移说明

早期仓库曾保留 `src/bad_example.py` 作为故意破坏 lint 的示例文件，用于验证工具链对格式和超长行的检查。随着质量检查流程稳定，为避免影响默认的 `flake8`/`mypy` 结果，该示例文件已迁移至文档中。

```python
# 示意代码：避免在源码目录中保留此类示例

def badly_formatted_function(x, y, z):
    if x > 0:
        return x + y + z
    return None

very_long_line = (
    "这是一个故意写得很长的行，超过了88个字符的限制，用来测试flake8的检查功能，应"  # noqa: E501
    "该会报错"
)
```

如需手动验证 lint 或格式化工具效果，可临时将上述代码复制到实验文件中，并在验证后删除。
