#!/bin/bash
# 快速修复命令

echo "使用Python编译器检查语法错误..."

echo "文件: src/adapters/factory_simple.py"
echo "  第93行: invalid syntax (<unknown>, line 93)"
python -m py_compile "src/adapters/factory_simple.py" 2>&1 | head -20
echo "---"
echo "文件: src/adapters/factory.py"
echo "  第30行: illegal target for annotation (<unknown>, line 30)"
python -m py_compile "src/adapters/factory.py" 2>&1 | head -20
echo "---"
echo "文件: src/adapters/registry.py"
echo "  第261行: illegal target for annotation (<unknown>, line 261)"
python -m py_compile "src/adapters/registry.py" 2>&1 | head -20
echo "---"
echo "文件: src/adapters/football.py"
echo "  第37行: illegal target for annotation (<unknown>, line 37)"
python -m py_compile "src/adapters/football.py" 2>&1 | head -20
echo "---"
echo "文件: src/config/openapi_config.py"
echo "  第473行: closing parenthesis '}' does not match opening parenthesis '[' on line 454 (<unknown>, line 473)"
python -m py_compile "src/config/openapi_config.py" 2>&1 | head -20
echo "---"
echo "文件: src/api/schemas.py"
echo "  第16行: illegal target for annotation (<unknown>, line 16)"
python -m py_compile "src/api/schemas.py" 2>&1 | head -20
echo "---"
echo "文件: src/api/cqrs.py"
echo "  第25行: illegal target for annotation (<unknown>, line 25)"
python -m py_compile "src/api/cqrs.py" 2>&1 | head -20
echo "---"
echo "文件: src/api/buggy_api.py"
echo "  第11行: invalid syntax (<unknown>, line 11)"
python -m py_compile "src/api/buggy_api.py" 2>&1 | head -20
echo "---"
echo "文件: src/api/dependencies.py"
echo "  第37行: invalid syntax (<unknown>, line 37)"
python -m py_compile "src/api/dependencies.py" 2>&1 | head -20
echo "---"
echo "文件: src/api/data_router.py"
echo "  第33行: illegal target for annotation (<unknown>, line 33)"
python -m py_compile "src/api/data_router.py" 2>&1 | head -20
echo "---"
