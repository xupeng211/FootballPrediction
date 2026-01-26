#!/bin/bash
# V108.100 测试执行包装脚本
# 用于在 WSL2 环境下正确连接数据库

export DB_HOST=172.25.16.1
export DB_PORT=5432
export DB_NAME=football_db
export DB_USER=football_user
export DB_PASSWORD=football_pass

cd /home/user/projects/FootballPrediction/scripts/ops
node v108_100_reliability_test.js
