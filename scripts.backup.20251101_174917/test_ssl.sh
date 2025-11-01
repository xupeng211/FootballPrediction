#!/bin/bash

# SSL连接测试脚本
set -e

DOMAIN=${1:-football-prediction.com}
PORT=${2:-443}

echo "测试SSL连接: $DOMAIN:$PORT"
echo "================================"

# 检查证书信息
echo "1. 证书信息:"
openssl s_client -connect $DOMAIN:$PORT -showcerts 2>/dev/null | \
    openssl x509 -noout -text 2>/dev/null | \
    grep -E "(Subject:|Issuer:|Not Before:|Not After:)" | head -4

echo ""
echo "2. SSL协议和加密套件:"
timeout 10 openssl s_client -connect $DOMAIN:$PORT 2>/dev/null | \
    grep -E "(Protocol|Cipher|TLS)" | head -3

echo ""
echo "3. 证书链验证:"
timeout 10 openssl s_client -connect $DOMAIN:$PORT -verify_return_error 2>/dev/null && \
    echo "✅ 证书链验证通过" || echo "❌ 证书链验证失败"

echo ""
echo "4. HTTPS访问测试:"
if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" | grep -q "200"; then
    echo "✅ HTTPS访问正常"
else
    echo "❌ HTTPS访问异常"
fi

echo ""
echo "SSL测试完成"
