#!/usr/bin/env python3
"""
简化API文档设置工具
"""

import json
from pathlib import Path


def setup_api_docs():
    """设置API文档基础结构"""

    # 创建API文档目录
    api_docs_dir = Path("docs/api")
    api_docs_dir.mkdir(parents=True, exist_ok=True)

    # 创建基础README
    readme_content = """# API文档

## 📚 足球预测系统API

### 🏗️ 基础信息
- **基础URL**: http://localhost:8000
- **API版本**: v1
- **认证方式**: JWT Bearer Token

### 📋 核心端点
- **预测API**: /api/predictions
- **用户API**: /api/users
- **比赛数据**: /api/matches
- **健康检查**: /health

### 🔐 认证示例
```bash
# 获取访问令牌
curl -X POST "http://localhost:8000/auth/token" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "username=your_username&password=your_password"

# 使用令牌访问API
curl -X GET "http://localhost:8000/api/predictions" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 📖 在线文档
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

*文档由Phase 8.1 API文档完善工具生成*
"""

    # 写入README
    with open(api_docs_dir / "README.md", 'w', encoding='utf-8') as f:
        f.write(readme_content)

    # 创建OpenAPI配置
    openapi_config = {
        "title": "足球预测系统 API",
        "description": "基于现代Python技术栈的足球预测RESTful API",
        "version": "1.0.0",
        "contact": {
            "name": "API支持",
            "email": "support@example.com"
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "开发环境"
            }
        ]
    }

    with open(api_docs_dir / "openapi-config.json", 'w', encoding='utf-8') as f:
        json.dump(openapi_config, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    setup_api_docs()
