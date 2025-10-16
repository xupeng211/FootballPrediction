#!/bin/bash

# 类型安全修复快速启动脚本
# 一键启动批次修复

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}"
    echo "██╗    ██╗███████╗██████╗ ██████╗ ███████╗██████╗ "
    echo "██║    ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██╔══██╗"
    echo "██║ █╗ ██║█████╗  ██████╔╝██████╔╝█████╗  ██████╔╝"
    echo "██║███╗██║██╔══╝  ██╔══██╗██╔══██╗██╔══╝  ██╔══██╗"
    echo "╚███╔███╔╝███████╗██║  ██║██████╔╝███████╗██║  ██║"
    echo " ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝"
    echo "                                              "
    echo "          类型安全修复工具 v1.0"
    echo -e "${NC}"
}

print_menu() {
    echo -e "${BLUE}请选择操作：${NC}"
    echo ""
    echo "  ${YELLOW}1.${NC} 📊 查看当前错误状态"
    echo "  ${YELLOW}2.${NC} 🔧 修复 ANN401 类型注解错误"
    echo "  ${YELLOW}3.${NC} 🏗️  修复 MyPy 类型错误"
    echo "  ${YELLOW}4.${NC} 📈 查看修复进度"
    echo "  ${YELLOW}5.${NC} 🎯 快速修复（最常见错误）"
    echo "  ${YELLOW}6.${NC} 📝 生成修复报告"
    echo "  ${YELLOW}7.${NC} 🔍 高级选项"
    echo "  ${YELLOW}0.${NC} 退出"
    echo ""
}

show_status() {
    echo -e "${BLUE}📊 检查当前错误状态...${NC}"
    python scripts/track_type_fixes.py
    echo ""
}

fix_ann401() {
    echo -e "${YELLOW}🔧 ANN401 类型注解修复${NC}"
    echo ""
    echo "请选择修复范围："
    echo "  1. API 层 (src/api/) - 推荐"
    echo "  2. 服务层 (src/services/)"
    echo "  3. 模型层 (src/models/)"
    echo "  4. 监控层 (src/monitoring/)"
    echo "  5. 自定义目录"
    echo ""
    read -p "选择 [1-5]: " choice

    case $choice in
        1) TARGET_DIR="src/api/" ;;
        2) TARGET_DIR="src/services/" ;;
        3) TARGET_DIR="src/models/" ;;
        4) TARGET_DIR="src/monitoring/" ;;
        5)
            read -p "输入目录路径: " TARGET_DIR
            TARGET_DIR="${TARGET_DIR%/}/"
            ;;
        *)
            echo -e "${RED}无效选择${NC}"
            return
            ;;
    esac

    read -p "批次大小 (默认50): " BATCH_SIZE
    BATCH_SIZE=${BATCH_SIZE:-50}

    echo -e "${BLUE}开始处理 $TARGET_DIR (批次大小: $BATCH_SIZE)${NC}"

    # 运行批次脚本
    ./scripts/fix_ann401_batch.sh "$TARGET_DIR" "$BATCH_SIZE"

    # 检查是否生成了批次
    LATEST_BATCH=$(ls -t ann401_batches/ 2>/dev/null | head -1)
    if [ -n "$LATEST_BATCH" ]; then
        echo ""
        read -p "是否立即处理第一批? [Y/n]: " process_first
        if [[ "$process_first" != "n" ]]; then
            BATCH_FILE="ann401_batches/$LATEST_BATCH/batch_1.txt"
            if [ -f "$BATCH_FILE" ]; then
                python scripts/process_ann401_batch.py "$BATCH_FILE"
            fi
        fi
    fi
}

fix_mypy() {
    echo -e "${YELLOW}🏗️ MyPy 类型错误修复${NC}"
    echo ""
    echo "请选择错误类型："
    echo "  1. attr-defined - 属性未定义 (最常见)"
    echo "  2. return-value - 返回值类型错误"
    echo "  3. arg-type - 参数类型错误"
    echo "  4. call-arg - 调用参数错误"
    echo "  5. assignment - 赋值类型错误"
    echo "  6. 所有错误 (除了 ANN401)"
    echo ""
    read -p "选择 [1-6]: " choice

    case $choice in
        1) ERROR_TYPE="attr-defined" ;;
        2) ERROR_TYPE="return-value" ;;
        3) ERROR_TYPE="arg-type" ;;
        4) ERROR_TYPE="call-arg" ;;
        5) ERROR_TYPE="assignment" ;;
        6) ERROR_TYPE="all" ;;
        *)
            echo -e "${RED}无效选择${NC}"
            return
            ;;
    esac

    read -p "目标目录 (默认 src/): " TARGET_DIR
    TARGET_DIR=${TARGET_DIR:-"src/"}

    read -p "批次大小 (默认30): " BATCH_SIZE
    BATCH_SIZE=${BATCH_SIZE:-30}

    echo -e "${BLUE}开始处理 $ERROR_TYPE 错误 in $TARGET_DIR${NC}"

    # 运行批次脚本
    ./scripts/fix_mypy_batch.sh "$ERROR_TYPE" "$TARGET_DIR" "$BATCH_SIZE"
}

quick_fix() {
    echo -e "${PURPLE}🎯 快速修复最常见的错误${NC}"
    echo ""
    echo "将按优先级顺序修复以下错误："
    echo "  1. API 层的 ANN401 错误"
    echo "  2. attr-defined 错误"
    echo "  3. 返回值类型错误"
    echo ""
    read -p "继续? [Y/n]: " confirm

    if [[ "$confirm" != "n" ]]; then
        # 1. 修复 API 层 ANN401
        echo -e "${BLUE}步骤 1: 修复 API 层 ANN401${NC}"
        ./scripts/fix_ann401_batch.sh "src/api/" 20

        # 等待用户处理
        echo ""
        read -p "完成第一批后按 Enter 继续..."

        # 2. 修复 attr-defined
        echo -e "${BLUE}步骤 2: 修复属性未定义错误${NC}"
        ./scripts/fix_mypy_batch.sh "attr-defined" "src/" 20

        echo ""
        echo -e "${GREEN}快速修复完成！请查看上述输出处理批次。${NC}"
    fi
}

advanced_options() {
    echo -e "${PURPLE}🔍 高级选项${NC}"
    echo ""
    echo "  1. 设置 MyPy 配置"
    echo "  2. 批量替换特定模式"
    echo "  3. 查看错误最多的文件"
    echo "  4. 清理缓存和临时文件"
    echo "  5. 重置进度跟踪"
    echo "  6. 导出错误列表"
    echo ""
    read -p "选择 [1-6]: " choice

    case $choice in
        1)
            echo -e "${BLUE}当前 MyPy 配置：${NC}"
            if [ -f "pyproject.toml" ]; then
                grep -A 20 "\[tool.mypy\]" pyproject.toml || echo "未找到 MyPy 配置"
            fi
            ;;
        2)
            echo "批量替换功能开发中..."
            ;;
        3)
            echo -e "${BLUE}错误最多的文件：${NC}"
            python -c "
import subprocess
result = subprocess.run(['mypy', 'src/', '--show-error-codes'], capture_output=True, text=True)
errors = {}
for line in result.stderr.split('\n'):
    if ':' in line and 'src/' in line:
        file = line.split(':')[0]
        errors[file] = errors.get(file, 0) + 1
for file, count in sorted(errors.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f'{file}: {count} 个错误')
"
            ;;
        4)
            echo -e "${BLUE}清理缓存...${NC}"
            find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
            find . -type f -name "*.pyc" -delete 2>/dev/null || true
            find . -type f -name "*.pyo" -delete 2>/dev/null || true
            find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
            echo -e "${GREEN}缓存清理完成${NC}"
            ;;
        5)
            read -p "确定要重置进度跟踪吗? [y/N]: " confirm
            if [[ "$confirm" == "y" ]]; then
                python scripts/track_type_fixes.py --reset
                echo -e "${GREEN}进度已重置${NC}"
            fi
            ;;
        6)
            TIMESTAMP=$(date +%Y%m%d_%H%M%S)
            mypy src/ --show-error-codes 2> "errors_${TIMESTAMP}.txt"
            echo -e "${GREEN}错误列表已导出到 errors_${TIMESTAMP}.txt${NC}"
            ;;
    esac
}

# 主循环
main() {
    # 检查脚本是否存在
    for script in scripts/fix_ann401_batch.sh scripts/fix_mypy_batch.sh scripts/track_type_fixes.py; do
        if [ ! -f "$script" ]; then
            echo -e "${RED}错误: 缺少脚本 $script${NC}"
            exit 1
        fi
    done

    while true; do
        clear
        print_header
        print_menu

        read -p "请选择 [0-7]: " choice
        echo ""

        case $choice in
            1)
                show_status
                read -p "按 Enter 继续..."
                ;;
            2)
                fix_ann401
                read -p "按 Enter 继续..."
                ;;
            3)
                fix_mypy
                read -p "按 Enter 继续..."
                ;;
            4)
                python scripts/track_type_fixes.py
                read -p "按 Enter 继续..."
                ;;
            5)
                quick_fix
                read -p "按 Enter 继续..."
                ;;
            6)
                python scripts/track_type_fixes.py --report
                echo "报告已生成: type_fix_report.md"
                read -p "按 Enter 继续..."
                ;;
            7)
                advanced_options
                read -p "按 Enter 继续..."
                ;;
            0)
                echo -e "${GREEN}再见！${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}无效选择，请重试${NC}"
                sleep 1
                ;;
        esac
    done
}

# 检查是否直接运行了脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
