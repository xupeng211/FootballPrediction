#!/bin/bash

# SSL证书自动续期脚本
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="$PROJECT_DIR/docker"

echo "$(date): 开始SSL证书续期检查..."

# 续期证书
docker-compose -f "$DOCKER_DIR/docker-compose.https.yml" run --rm certbot renew

if [ $? -eq 0 ]; then
    echo "$(date): SSL证书续期成功，重启Nginx..."
    docker-compose -f "$DOCKER_DIR/docker-compose.https.yml" restart nginx
    echo "$(date): Nginx重启完成"
else
    echo "$(date): SSL证书续期失败"
    exit 1
fi

echo "$(date): SSL证书续期检查完成"
