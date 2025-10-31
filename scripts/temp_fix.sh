#!/bin/bash
# 临时安装脚本 - 安装缺失的科学计算库

echo "正在安装缺失的科学计算库..."

pip install --user numpy==2.3.4 pandas==2.3.3 scikit-learn==1.7.2

echo "依赖安装完成，正在启动应用..."

# 设置环境变量
export PATH=/home/appuser/.local/bin:$PATH

# 启动应用
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1