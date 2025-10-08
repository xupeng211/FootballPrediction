#!/bin/bash

# 批量修复 MyPy 类型错误脚本
# 使用方法: ./scripts/fix_mypy_batch.sh [错误类型] [目录] [批次大小]

set -e

# 默认参数
ERROR_TYPE=${1:-"attr-defined"}  # 可选: attr-defined, return-value, arg-type, call-arg
TARGET_DIR=${2:-"src/"}
BATCH_SIZE=${3:-30}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="mypy_batches/$TIMESTAMP"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    local status=$1
    local message=$2
    case $status in
        "info")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
        "success")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "error")
            echo -e "${RED}❌ $message${NC}"
            ;;
    esac
}

# 支持的错误类型
print_error_types() {
    echo "支持的错误类型："
    echo "  attr-defined    - 属性未定义错误（最常见）"
    echo "  return-value   - 返回值类型错误"
    echo "  arg-type       - 参数类型错误"
    echo "  call-arg       - 调用参数错误"
    echo "  assignment     - 赋值类型错误"
    echo "  all            - 所有错误（不包括 ANN401）"
}

# 检查 mypy 是否安装
if ! command -v mypy &> /dev/null; then
    print_status "error" "mypy 未安装，请先安装: pip install mypy"
    exit 1
fi

# 参数验证
if [[ "$ERROR_TYPE" == "--help" || "$ERROR_TYPE" == "-h" ]]; then
    echo "用法: $0 [错误类型] [目录] [批次大小]"
    echo ""
    print_error_types
    exit 0
fi

print_status "info" "开始修复 $TARGET_DIR 的 MyPy $ERROR_TYPE 错误..."
print_status "info" "批次大小: $BATCH_SIZE"
print_status "info" "输出目录: $OUTPUT_DIR"

# 构建过滤条件
if [[ "$ERROR_TYPE" == "all" ]]; then
    FILTER_PATTERN="error"
    OUTPUT_PREFIX="all_mypy"
else
    FILTER_PATTERN="$ERROR_TYPE"
    OUTPUT_PREFIX="mypy_${ERROR_TYPE}"
fi

# 获取所有目标错误
print_status "info" "正在扫描类型错误..."
if [[ "$ERROR_TYPE" == "all" ]]; then
    # 排除 ANN401
    mypy "$TARGET_DIR" --show-error-codes --no-error-summary 2>&1 | grep -v "ANN401" | grep "error" > "$OUTPUT_DIR/all_errors.txt"
else
    mypy "$TARGET_DIR" --show-error-codes --no-error-summary 2>&1 | grep "$FILTER_PATTERN" > "$OUTPUT_DIR/all_errors.txt"
fi

# 统计总数
TOTAL=$(wc -l < "$OUTPUT_DIR/all_errors.txt" | tr -d ' ')

if [ "$TOTAL" -eq 0 ]; then
    print_status "success" "太好了！没有发现 $ERROR_TYPE 错误"
    exit 0
fi

print_status "info" "发现 $TOTAL 个 $ERROR_TYPE 错误"

# 分析错误模式
print_status "info" "分析错误模式..."
python3 << 'EOF' > /tmp/error_patterns.py
import sys
import re
from collections import Counter

def analyze_errors(error_file, output_file):
    patterns = Counter()
    with open(error_file) as f:
        for line in f:
            # 提取错误消息
            if "]" in line:
                msg = line.split("]")[-1].strip()
                # 提取关键模式
                if "has no attribute" in msg:
                    patterns["no_attribute"] += 1
                elif "incompatible" in msg and "return" in msg:
                    patterns["incompatible_return"] += 1
                elif "incompatible" in msg and "argument" in msg:
                    patterns["incompatible_argument"] += 1
                elif "has no item" in msg:
                    patterns["no_item"] += 1
                elif "does not support" in msg:
                    patterns["unsupported_operation"] += 1
                else:
                    patterns["other"] += 1

    # 输出结果
    with open(output_file, 'w') as f:
        f.write("# 错误模式分析\n\n")
        for pattern, count in patterns.most_common():
            f.write(f"{pattern}: {count}\n")

if __name__ == "__main__":
    analyze_errors(sys.argv[1], sys.argv[2])
EOF

python3 /tmp/error_patterns.py "$OUTPUT_DIR/all_errors.txt" "$OUTPUT_DIR/error_patterns.txt"

print_status "info" "主要错误模式："
head -5 "$OUTPUT_DIR/error_patterns.txt" | grep -v "^#"

# 按文件分组错误
print_status "info" "按文件汇总错误..."
awk -F: '{print $1}' "$OUTPUT_DIR/all_errors.txt" | sort | uniq -c | sort -rn > "$OUTPUT_DIR/errors_by_file.txt"

# 显示前10个错误最多的文件
print_status "info" "错误最多的文件："
head -10 "$OUTPUT_DIR/errors_by_file.txt" | while read count file; do
    echo "  $file: $count 个错误"
done

# 分批处理
BATCH_COUNT=1
CURRENT_LINE=1

while [ $CURRENT_LINE -le $TOTAL ]; do
    BATCH_END=$((CURRENT_LINE + BATCH_SIZE - 1))
    if [ $BATCH_END -gt $TOTAL ]; then
        BATCH_END=$TOTAL
    fi

    BATCH_FILE="$OUTPUT_DIR/batch_${BATCH_COUNT}.txt"
    STATUS_FILE="$OUTPUT_DIR/batch_${BATCH_COUNT}_status.json"

    # 提取当前批次的错误
    sed -n "${CURRENT_LINE},${BATCH_END}p" "$OUTPUT_DIR/all_errors.txt" > "$BATCH_FILE"

    # 创建批次状态文件
    cat > "$STATUS_FILE" << EOF
{
    "batch_number": $BATCH_COUNT,
    "start_line": $CURRENT_LINE,
    "end_line": $BATCH_END,
    "error_count": $((BATCH_END - CURRENT_LINE + 1)),
    "error_type": "$ERROR_TYPE",
    "status": "pending",
    "created_at": "$(date -Iseconds)"
}
EOF

    # 提取涉及的文件列表
    awk -F: '{print $1}' "$BATCH_FILE" | sort | uniq > "$OUTPUT_DIR/batch_${BATCH_COUNT}_files.txt"

    CURRENT_LINE=$((BATCH_END + 1))
    BATCH_COUNT=$((BATCH_COUNT + 1))
done

print_status "success" "已创建 $((BATCH_COUNT - 1)) 个批次文件"

# 生成处理脚本
cat > "$OUTPUT_DIR/process_all.py" << 'EOF'
#!/usr/bin/env python3
"""批量处理所有 MyPy 错误批次的脚本"""

import subprocess
import sys
from pathlib import Path

def main():
    output_dir = Path(__file__).parent

    # 找到所有批次文件
    batch_files = sorted(output_dir.glob("batch_*.txt"))

    print(f"找到 {len(batch_files)} 个批次文件")

    for batch_file in batch_files:
        print(f"\n处理批次: {batch_file.name}")

        # 调用处理脚本
        result = subprocess.run([
            "python", "scripts/process_mypy_batch.py",
            str(batch_file)
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"错误: {result.stderr}")

        # 询问是否继续
        response = input("继续下一个批次? [Y/n] ").strip().lower()
        if response == 'n':
            break

if __name__ == "__main__":
    main()
EOF

chmod +x "$OUTPUT_DIR/process_all.py"

# 生成提示
print_status "info" "使用以下命令处理批次："
echo "  # 处理单个批次"
echo "  python scripts/process_mypy_batch.py $OUTPUT_DIR/batch_1.txt"
echo ""
echo "  # 批量处理所有批次"
echo "  $OUTPUT_DIR/process_all.py"

# 创建快捷命令
cat > "$OUTPUT_DIR/quick_fix.sh" << EOF
#!/bin/bash
# 快捷修复脚本

echo "MyPy 错误快速修复"
echo "=================="
echo "1. 查看进度"
echo "2. 处理下一个批次"
echo "3. 查看错误最多的文件"
echo "4. 重新统计"
echo ""
read -p "选择操作 [1-4]: " choice

case \$choice in
    1)
        cat "$OUTPUT_DIR/track_progress.sh"
        ;;
    2)
        # 找到下一个待处理的批次
        NEXT_BATCH=\$(ls "$OUTPUT_DIR"/batch_*.txt | head -1)
        if [ -n "\$NEXT_BATCH" ]; then
            python scripts/process_mypy_batch.py "\$NEXT_BATCH"
        else
            echo "没有待处理的批次"
        fi
        ;;
    3)
        echo "错误最多的文件："
        head -5 "$OUTPUT_DIR/errors_by_file.txt"
        ;;
    4)
        TOTAL=\$(wc -l < "$OUTPUT_DIR/all_errors.txt" | tr -d ' ')
        COMPLETED=\$(find "$OUTPUT_DIR" -name "*_status.json" -exec grep -l '"status": "completed"' {} \; | wc -l | tr -d ' ')
        echo "总数: \$TOTAL, 已完成: \$COMPLETED"
        ;;
esac
EOF

chmod +x "$OUTPUT_DIR/quick_fix.sh"

print_status "success" "所有批次文件已准备完成！"
print_status "info" "快捷命令: $OUTPUT_DIR/quick_fix.sh"