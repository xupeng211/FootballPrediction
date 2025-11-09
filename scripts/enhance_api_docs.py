#!/usr/bin/env python3
"""
API文档完善工具
为FastAPI应用添加详细的接口说明和示例
"""

import os
import json
from pathlib import Path

def create_api_documentation_structure():
    """创建API文档的基础结构"""

    # 创建API文档目录
    api_docs_dir = Path("docs/api")
    api_docs_dir.mkdir(parents=True, exist_ok=True)

    # 创建API文档索引
    index_content = """# API文档

## 📚 概述

足球预测系统的RESTful API文档，提供完整的接口说明、示例和错误处理指南。

## 🏗️ API架构

### 基础信息
- **基础URL**: `http://localhost:8000`
- **API版本**: `v1`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON

### 核心模块
- **预测服务**: 比赛预测生成和管理
- **用户管理**: 用户认证和授权
- **数据管理**: 比赛数据和统计信息
- **性能监控**: 系统性能和健康状态

## 📋 接口分类

### 核心API端点
- [预测API](./predictions.md) - 比赛预测相关接口
- [用户API](./users.md) - 用户管理和认证
- [数据API](./data.md) - 比赛数据和统计
- [健康检查](./health.md) - 系统状态监控

### 高级功能
- [实时数据流](./realtime.md) - WebSocket实时推送
- [性能优化](./performance.md) - 性能监控和优化
- [缓存管理](./cache.md) - Redis缓存操作

## 🔐 认证和授权

### JWT Token认证
```bash
# 获取访问令牌
curl -X POST "http://localhost:8000/auth/token" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "username=your_username&password=your_password"

# 使用令牌访问API
curl -X GET "http://localhost:8000/api/predictions" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 权限级别
- **public**: 公开接口，无需认证
- **user**: 用户级别，需要基础认证
- **admin**: 管理员级别，需要管理员权限

## 📊 响应格式

### 成功响应
```json
{
  "success": true,
  "data": {
    // 响应数据
  },
  "message": "操作成功",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🚀 快速开始

### 1. 启动服务
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 访问文档
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 3. 测试API
```bash
# 健康检查
curl http://localhost:8000/health

# 获取API信息
curl http://localhost:8000/info
```

## 📖 详细文档

- [API使用指南](./guide.md) - 详细的使用说明
- [错误代码参考](./errors.md) - 完整的错误代码列表
- [示例代码](./examples.md) - 各语言的使用示例

---

**最后更新**: 2024-01-01
**版本**: v1.0.0
"""

    # 写入API文档索引
    with open(api_docs_dir / "README.md", 'w', encoding='utf-8') as f:
        f.write(index_content)

    print("✅ 创建API文档基础结构")

def enhance_openapi_configuration():
    """增强OpenAPI配置"""

    openapi_config = {
        "title": "足球预测系统 API",
        "description": "基于现代Python技术栈的足球预测RESTful API",
        "version": "1.0.0",
        "contact": {
            "name": "API支持",
            "email": "support@example.com"
        },
        "license_info": {
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "开发环境"
            },
            {
                "url": "https://api.football-prediction.com",
                "description": "生产环境"
            }
        ],
        "security": [
            {
                "BearerAuth": []
            }
        ],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT认证令牌"
                }
            },
            "schemas": {
                "StandardResponse": {
                    "type": "object",
                    "properties": {
                        "success": {
                            "type": "boolean",
                            "description": "操作是否成功"
                        },
                        "data": {
                            "type": "object",
                            "description": "响应数据"
                        },
                        "message": {
                            "type": "string",
                            "description": "响应消息"
                        },
                        "timestamp": {
                            "type": "string",
                            "format": "date-time",
                            "description": "响应时间戳"
                        }
                    }
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "success": {
                            "type": "boolean",
                            "example": False
                        },
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {
                                    "type": "string",
                                    "description": "错误代码"
                                },
                                "message": {
                                    "type": "string",
                                    "description": "错误描述"
                                },
                                "details": {
                                    "type": "object",
                                    "description": "错误详情"
                                }
                            }
                        },
                        "timestamp": {
                            "type": "string",
                            "format": "date-time"
                        }
                    }
                }
            }
        }
    }

    # 保存OpenAPI配置
    config_dir = Path("docs/api")
    config_dir.mkdir(parents=True, exist_ok=True)

    with open(config_dir / "openapi-config.json", 'w', encoding='utf-8') as f:
        json.dump(openapi_config, f, indent=2, ensure_ascii=False)

    print("✅ 创建OpenAPI配置文件")

def create_api_examples():
    """创建API使用示例"""

    examples_content = """# API使用示例

## 🔧 环境准备

### Python示例
```python
import requests
import json

# API基础配置
BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# 获取访问令牌
def get_access_token(username: str, password: str) -> str:
    """获取JWT访问令牌"""
    response = requests.post(
        f"{BASE_URL}/auth/token",
        data={
            "username": username,
            "password": password
        }
    )
    response.raise_for_status()
    return response.json()["access_token"]

# 设置认证头
def get_auth_headers(token: str) -> dict:
    """获取带认证的请求头"""
    return {
        **HEADERS,
        "Authorization": f"Bearer {token}"
    }
```

### JavaScript示例
```javascript
// API基础配置
const BASE_URL = "http://localhost:8000";

// 获取访问令牌
async function getAccessToken(username, password) {
    const response = await fetch(`${BASE_URL}/auth/token`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `username=${username}&password=${password}`
    });

    const data = await response.json();
    return data.access_token;
}

// 带认证的API请求
async function authenticatedRequest(endpoint, token, options = {}) {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            ...options.headers
        }
    });

    return response.json();
}
```

### cURL示例
```bash
#!/bin/bash

# API基础配置
BASE_URL="http://localhost:8000"

# 获取访问令牌
ACCESS_TOKEN=$(curl -s -X POST "${BASE_URL}/auth/token" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "username=your_username&password=your_password" | \\
  jq -r '.access_token')

# 带认证的API请求
curl -X GET "${BASE_URL}/api/predictions" \\
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \\
  -H "Content-Type: application/json"
```

## 📋 常用API操作

### 1. 用户认证
```python
# 用户登录
token = get_access_token("username", "password")
print(f"访问令牌: {token}")

# 获取用户信息
headers = get_auth_headers(token)
response = requests.get(f"{BASE_URL}/users/me", headers=headers)
user_info = response.json()
```

### 2. 预测管理
```python
# 创建预测
prediction_data = {
    "match_id": 123,
    "home_score_prediction": 2,
    "away_score_prediction": 1,
    "confidence_score": 0.85
}

response = requests.post(
    f"{BASE_URL}/api/predictions",
    headers=get_auth_headers(token),
    json=prediction_data
)
prediction = response.json()

# 获取预测列表
response = requests.get(
    f"{BASE_URL}/api/predictions",
    headers=get_auth_headers(token),
    params={"limit": 10, "offset": 0}
)
predictions = response.json()
```

### 3. 数据查询
```python
# 获取比赛列表
response = requests.get(
    f"{BASE_URL}/api/matches",
    params={"league_id": 1, "status": "upcoming"}
)
matches = response.json()

# 获取球队信息
response = requests.get(f"{BASE_URL}/api/teams/{team_id}")
team_info = response.json()
```

### 4. 统计信息
```python
# 获取用户统计
response = requests.get(
    f"{BASE_URL}/api/statistics/user",
    headers=get_auth_headers(token)
)
user_stats = response.json()

# 获取系统统计
response = requests.get(
    f"{BASE_URL}/api/statistics/system",
    headers=get_auth_headers(token)
)
system_stats = response.json()
```

## 🔍 错误处理

### Python错误处理
```python
try:
    response = requests.get(f"{BASE_URL}/api/data", headers=headers)
    response.raise_for_status()
    data = response.json()

    if not data.get("success"):
        error = data.get("error", {})
        print(f"API错误: {error.get('message')}")
        print(f"错误代码: {error.get('code')}")
    else:
        result = data.get("data")
        print(f"获取数据成功: {result}")

except requests.exceptions.RequestException as e:
    print(f"网络请求失败: {e}")
except json.JSONDecodeError as e:
    print(f"JSON解析失败: {e}")
```

### JavaScript错误处理
```javascript
try {
    const response = await authenticatedRequest('/api/data', token);

    if (!response.success) {
        console.error('API错误:', response.error.message);
        console.error('错误代码:', response.error.code);
    } else {
        console.log('获取数据成功:', response.data);
    }
} catch (error) {
    console.error('请求失败:', error);
}
```

## 🧪 测试示例

### 单元测试示例
```python
import pytest
import requests
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

def test_health_check():
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_prediction():
    """测试创建预测接口"""
    # 首先获取访问令牌
    token_response = client.post("/auth/token", data={
        "username": "test_user",
        "password": "test_password"
    })
    token = token_response.json()["access_token"]

    # 创建预测
    prediction_data = {
        "match_id": 123,
        "home_score_prediction": 2,
        "away_score_prediction": 1,
        "confidence_score": 0.85
    }

    response = client.post(
        "/api/predictions",
        json=prediction_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
```

---

**注意**: 请根据实际API调整示例代码中的端点和参数。
"""

    # 保存API示例
    examples_path = Path("docs/api/examples.md")
    with open(examples_path, 'w', encoding='utf-8') as f:
        f.write(examples_content)

    print("✅ 创建API使用示例")

def main():
    """主函数"""
    print("📚 API文档完善工具")
    print("=" * 40)

    print("🏗️ 创建API文档基础结构...")
    create_api_documentation_structure()

    print("⚙️ 增强OpenAPI配置...")
    enhance_openapi_configuration()

    print("📝 创建API使用示例...")
    create_api_examples()

    print("\n🎉 API文档基础框架创建完成!")
    print("\n📋 生成的文件:")
    print("  📄 docs/api/README.md - API文档索引")
    print("  ⚙️  docs/api/openapi-config.json - OpenAPI配置")
    print("  📝 docs/api/examples.md - API使用示例")

    print("\n🚀 下一步建议:")
    print("  1. 完善各模块的详细API文档")
    print("  2. 更新FastAPI应用中的OpenAPI配置")
    print("  3. 添加请求/响应模型的详细说明")
    print("  4. 创建完整的测试用例")

if __name__ == "__main__":
    main()