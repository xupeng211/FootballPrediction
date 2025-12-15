#!/bin/bash
# Playwright 环境安装脚本

echo "🚀 开始安装 Playwright 依赖..."

# 安装 Python 包
echo "📦 安装 Python 包..."
pip install playwright beautifulsoup4 lxml

# 安装 Playwright 浏览器
echo "🌐 安装 Playwright 浏览器..."
playwright install chromium

# 验证安装
echo "✅ 验证安装..."
python -c "
try:
    from playwright.async_api import async_playwright
    from bs4 import BeautifulSoup
    print('✅ 所有依赖安装成功！')
    print('🎯 现在可以运行: python scripts/test_playwright_titan.py')
except ImportError as e:
    print(f'❌ 安装失败: {e}')
    exit(1)
"

echo "🎉 Playwright 环境安装完成！"