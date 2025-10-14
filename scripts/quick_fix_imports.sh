#!/bin/bash

echo "🔧 快速修复导入语法错误..."

# 修复所有重复的 Any 导入
find src -name "*.py" -type f -exec sed -i 's/from typing import Any,.*?, Any/from typing import Any/g' {} \;

# 修复常见的重复导入
find src -name "*.py" -type f -exec sed -i 's/from typing import Any, Dict\[str, Any\], Any/from typing import Any, Dict/' {} \;
find src -name "*.py" -type f -exec sed -i 's/from typing import Any,  Any/from typing import Any/' {} \;
find src -name "*.py" -type f -exec sed -i 's/from typing import Dict\[str, Any\], Any/from typing import Any, Dict/' {} \;

# 修复括号问题
find src -name "*.py" -type f -exec sed -i 's/Dict\[str, Any\]\[str, Any\]/Dict[str, Any]/g' {} \;
find src -name "*.py" -type f -exec sed -i 's/List\[Any\]\[str\]/List[str]/g' {} \;
find src -name "*.py" -type f -exec sed -i 's/List\[Any\]\[Dict\[str, Any\]\]/List[Dict[str, Any]]/g' {} \;

echo "✅ 修复完成！"
