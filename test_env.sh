#!/bin/bash
# 测试环境变量（请根据实际情况修改）
export GITHUB_TOKEN="your_token_here"
export GITHUB_REPO="your_username/your_repo"

echo "环境变量已设置:"
echo "GITHUB_REPO=$GITHUB_REPO"
echo "GITHUB_TOKEN=${GITHUB_TOKEN:0:8}..."
