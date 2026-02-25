"""
V172 领域层 (Domain Layer)

包含核心业务逻辑和领域模型，与基础设施解耦。

架构原则：
- 领域层不依赖基础设施层
- 业务逻辑集中在 services/ 中
- 领域实体在 entities/ 中
- 仓储接口在 repositories/ 中

目录结构：
├── entities/         # 领域实体
├── services/         # 领域服务
│   ├── prediction/   # 预测服务
│   ├── harvesting/   # 收割服务
│   └── analysis/     # 分析服务
└── repositories/     # 仓储接口
"""

__version__ = "172.0.0"
