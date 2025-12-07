# ⚽ 足球博彩预测系统架构可视化图表 (v4.0.0)

**项目名称**: Football Betting Prediction System
**当前版本**: v4.0.0-stable (生产就绪)
**创建时间**: 2025-12-07
**文档作者**: System Architect

本文档包含系统的核心架构图表，用于技术文档归档和团队协作。

---

## 📊 图表 A: 高层系统架构图 (C4 Container Diagram)

```mermaid
graph TD
    %% 用户层
    User[用户浏览器<br/>Browser/Mobile] --> Gateway

    %% 网关层
    Gateway[Nginx<br/>反向代理 & SSL<br/>Port: 80] --> Frontend
    Gateway --> Backend

    %% 前端服务
    Frontend[Vue 3 SPA<br/>Vite + Pinia + TypeScript<br/>Port: 5173] --> Backend

    %% 后端API服务
    Backend[FastAPI<br/>异步Web框架<br/>Port: 8000] --> InferenceService
    Backend --> DataCollectionService
    Backend --> PostgreSQL
    Backend --> Redis

    %% 核心业务服务
    InferenceService[推理服务<br/>InferenceService<br/>XGBoost模型推理] --> ModelRegistry
    DataCollectionService[数据采集服务<br/>DataCollectionService] --> FotMobAPI
    DataCollectionService --> FeatureStore

    %% 数据存储层
    PostgreSQL[(PostgreSQL<br/>业务数据库<br/>Port: 5432)] --> FeatureStore
    Redis[(Redis<br/>缓存 & 消息队列<br/>Port: 6379)] --> CeleryWorker

    %% 机器学习组件
    FeatureStore[特征存储<br/>FeatureStore] --> XGBoostTrainer
    XGBoostTrainer[XGBoost训练器<br/>ML Pipeline] --> ModelRegistry
    ModelRegistry[(模型注册表<br/>Model Artifacts)] --> InferenceService

    %% 任务调度系统
    CeleryBeat[Celery Beat<br/>定时任务调度器] --> Redis
    CeleryWorker[Celery Worker<br/>异步任务执行器] --> Redis
    CeleryWorker --> DataCollectionService
    CeleryWorker --> XGBoostTrainer

    %% 监控系统
    Prometheus[Prometheus<br/>指标收集] --> Backend
    Prometheus --> PostgreSQL
    Grafana[Grafana<br/>监控仪表板] --> Prometheus

    %% 外部API
    FotMobAPI[FotMob API<br/>外部数据源] --> DataCollectionService

    %% 样式定义
    classDef userLayer fill:#e1f5fe
    classDef gatewayLayer fill:#f3e5f5
    classDef frontendLayer fill:#e8f5e8
    classDef backendLayer fill:#fff3e0
    classDef serviceLayer fill:#fce4ec
    classDef dataLayer fill:#f1f8e9
    classDef mlLayer fill:#e0f2f1
    classDef taskLayer fill:#fff8e1
    classDef monitorLayer fill:#fce4ec
    classDef externalLayer fill:#f5f5f5

    class User userLayer
    class Gateway gatewayLayer
    class Frontend frontendLayer
    class Backend,InferenceService,DataCollectionService backendLayer
    class PostgreSQL,Redis dataLayer
    class FeatureStore,XGBoostTrainer,ModelRegistry mlLayer
    class CeleryBeat,CeleryWorker taskLayer
    class Prometheus,Grafana monitorLayer
    class FotMobAPI externalLayer
```

---

## 🔄 图表 B: 数据采集与 ML 流水线 (Data Pipeline Flow)

```mermaid
sequenceDiagram
    %% 参与者定义
    participant Scheduler as 调度器<br/>Prefect/Celery Beat
    participant Factory as 工厂模式<br/>AdapterFactory
    participant Collector as 数据采集器<br/>FotMobCollectorV2
    participant Parser as 数据解析器<br/>DataParser
    participant RawDB as 原始数据库<br/>PostgreSQL
    participant FeatureStore as 特征存储<br/>FeatureStore
    participant Trainer as 训练器<br/>XGBoostTrainer
    participant ModelRegistry as 模型注册表<br/>MLflow/Artifacts
    participant Inference as 推理服务<br/>InferenceService

    %% 数据采集流程
    Note over Scheduler: 定时触发 (每日/每小时)
    Scheduler->>+Factory: create_collector("fotmob_v2")
    Factory->>Factory: 注入 Proxy/RateLimiter
    Factory-->>-Collector: EnhancedFotMobCollector

    Note over Collector: HTTP 请求采集 (无浏览器)
    Collector->>+FotMobAPI: GET /api/matches
    FotMobAPI-->>-Collector: JSON 数据
    Collector->>+Parser: parse_match_data(raw_json)
    Parser-->>-Collector: Match Objects
    Collector->>+RawDB: save_raw_data(matches)
    RawDB-->>-Collector: 保存成功

    %% 特征工程流程
    Scheduler->>+FeatureStore: extract_features()
    FeatureStore->>RawDB: 查询原始数据
    RawDB-->>FeatureStore: 返回数据
    FeatureStore->>FeatureStore: 计算统计特征
    FeatureStore->>FeatureStore: 数据质量检查
    FeatureStore-->>-Scheduler: 特征提取完成

    %% 模型训练流程
    Note over Scheduler: 每周重训练或性能下降时
    Scheduler->>+Trainer: start_training_pipeline()
    Trainer->>FeatureStore: 获取训练特征
    FeatureStore-->>Trainer: 特征数据集
    Trainer->>Trainer: 数据预处理 & 划分
    Trainer->>Trainer: XGBoost 超参数优化
    Trainer->>+ModelRegistry: register_model(model_artifacts)
    ModelRegistry-->>-Trainer: 模型版本 v{timestamp}
    Trainer-->>-Scheduler: 训练完成

    %% 推理服务更新
    Scheduler->>+Inference: reload_model()
    Inference->>ModelRegistry: load_latest_model()
    ModelRegistry-->>Inference: 模型文件
    Inference->>Inference: 验证模型性能
    Inference-->>-Scheduler: 模型更新完成

    %% 错误处理
    alt 数据采集失败
        Collector->>Scheduler: 报告采集错误
        Scheduler->>Collector: 重试机制 (指数退避)
    end

    alt 模型训练失败
        Trainer->>ModelRegistry: 回滚到上一版本
        ModelRegistry-->>Trainer: 稳定模型
        Trainer->>Scheduler: 报告训练失败
    end
```

---

## 🐳 图表 C: 部署架构图 (Deployment View)

```mermaid
graph LR
    subgraph "Docker Compose 网络架构"
        %% 外部访问
        Internet[互联网] --> Nginx

        %% 网关层
        Nginx[Nginx<br/>Port: 80<br/>反向代理]

        %% 前端服务
        Frontend[Frontend<br/>Vue.js SPA<br/>Port: 3000<br/>Container: frontend]

        %% 后端服务
        App[Backend App<br/>FastAPI<br/>Port: 8000<br/>Container: app]

        %% 后台任务服务
        Worker[Celery Worker<br/>异步任务执行<br/>Container: worker]
        Beat[Celery Beat<br/>定时调度器<br/>Container: beat]

        %% 数据采集服务
        DataCollector1[Data Collector L1<br/>Football-Data<br/>Container: data-collector]
        DataCollector2[Data Collector L2<br/>FotMob V2<br/>Container: data-collector-l2]

        %% 数据存储
        PostgreSQL[(PostgreSQL<br/>Port: 5432<br/>Container: db)]
        Redis[(Redis<br/>Port: 6379<br/>Container: redis)]

        %% 监控服务
        Prometheus[Prometheus<br/>指标收集<br/>Port: 9090]
        Grafana[Grafana<br/>监控仪表板<br/>Port: 3001]
    end

    %% 网络连接关系
    Nginx --> Frontend
    Nginx --> App

    Frontend --> App

    App --> PostgreSQL
    App --> Redis
    App --> Worker

    Worker --> PostgreSQL
    Worker --> Redis
    Worker --> DataCollector1
    Worker --> DataCollector2

    Beat --> Redis

    DataCollector1 --> PostgreSQL
    DataCollector2 --> PostgreSQL
    DataCollector2 --> Redis

    Prometheus --> App
    Prometheus --> PostgreSQL
    Prometheus --> Redis

    Grafana --> Prometheus

    %% 容器依赖关系
    subgraph "容器依赖"
        App -.-> PostgreSQL
        App -.-> Redis
        Worker -.-> PostgreSQL
        Worker -.-> Redis
        Beat -.-> Redis
        DataCollector1 -.-> PostgreSQL
        DataCollector1 -.-> Redis
        DataCollector2 -.-> PostgreSQL
        DataCollector2 -.-> Redis
        Frontend -.-> App
        Nginx -.-> App
        Nginx -.-> Frontend
    end

    %% 样式定义
    classDef gateway fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef frontend fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef backend fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef worker fill:#fff8e1,stroke:#ffc107,stroke-width:2px
    classDef collector fill:#e0f2f1,stroke:#009688,stroke-width:2px
    classDef database fill:#f1f8e9,stroke:#8bc34a,stroke-width:3px
    classDef monitoring fill:#fce4ec,stroke:#e91e63,stroke-width:2px

    class Nginx gateway
    class Frontend frontend
    class App backend
    class Worker,Beat worker
    class DataCollector1,DataCollector2 collector
    class PostgreSQL,Redis database
    class Prometheus,Grafana monitoring
```

---

## 📋 图表说明

### 系统架构特点

1. **微服务架构**: 采用Docker容器化部署，各服务职责分离
2. **异步优先**: 全面使用async/await模式，支持高并发
3. **事件驱动**: 基于Celery的消息队列系统，实现松耦合
4. **数据驱动**: 统一的特征存储和模型注册表
5. **监控完备**: Prometheus + Grafana全方位监控

### 关键技术栈

- **前端**: Vue.js 3 + TypeScript + Vite + Pinia
- **后端**: FastAPI + SQLAlchemy 2.0 + PostgreSQL 15
- **缓存**: Redis 7.0 (缓存 + 消息队列)
- **机器学习**: XGBoost + MLflow + Optuna
- **任务调度**: Celery + Celery Beat
- **容器化**: Docker + Docker Compose
- **监控**: Prometheus + Grafana

### 部署端口映射

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| Nginx | 80 | 80 | 反向代理 |
| Frontend | 80 | 3000 | Vue.js应用 |
| Backend | 8000 | 8000 | FastAPI服务 |
| PostgreSQL | 5432 | 5432 | 数据库 |
| Redis | 6379 | 6379 | 缓存/队列 |
| Prometheus | 9090 | - | 内部监控 |
| Grafana | 3000 | 3001 | 监控面板 |

---

**文档维护**: System Architect
**最后更新**: 2025-12-07
**版本**: v4.0.0