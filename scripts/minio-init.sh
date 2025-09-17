#!/bin/bash
# MinIO 初始化脚本
# 创建足球预测系统所需的存储桶和设置权限

set -e

echo "开始初始化 MinIO..."

# 等待 MinIO 服务启动
while ! curl -f http://localhost:9000/minio/health/live >/dev/null 2>&1; do
    echo "等待 MinIO 启动..."
    sleep 2
done

echo "MinIO 服务已启动，开始创建桶..."

# 配置 MinIO 客户端
mc config host add local http://localhost:9000 "${MINIO_ROOT_USER:-minioadmin}" "${MINIO_ROOT_PASSWORD:-change_me}"

# 创建数据湖桶
echo "创建数据湖存储桶..."
mc mb --ignore-existing local/football-lake-bronze
mc mb --ignore-existing local/football-lake-silver
mc mb --ignore-existing local/football-lake-gold
mc mb --ignore-existing local/football-lake-archive

# 设置桶策略（开发环境为公共读取，生产环境应更严格）
echo "设置桶访问策略..."
cat > /tmp/public-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": ["*"]
      },
      "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::football-lake-*"]
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": ["*"]
      },
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": ["arn:aws:s3:::football-lake-*/*"]
    }
  ]
}
EOF

mc policy set-json /tmp/public-policy.json local/football-lake-bronze
mc policy set-json /tmp/public-policy.json local/football-lake-silver
mc policy set-json /tmp/public-policy.json local/football-lake-gold

# 创建生命周期策略（自动归档旧数据）
echo "设置数据生命周期策略..."
cat > /tmp/lifecycle-policy.json << 'EOF'
{
  "Rules": [
    {
      "ID": "ArchiveOldData",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
EOF

mc ilm import local/football-lake-bronze < /tmp/lifecycle-policy.json
mc ilm import local/football-lake-silver < /tmp/lifecycle-policy.json

echo "MinIO 初始化完成！"
echo "管理界面: http://localhost:9001"
echo "用户名: ${MINIO_ROOT_USER:-minioadmin}"
echo "密码: ${MINIO_ROOT_PASSWORD:-change_me}"
