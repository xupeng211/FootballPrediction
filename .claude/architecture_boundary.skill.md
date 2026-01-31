# Architecture Boundary Skill - 架构边界约束

**约束等级**: 🔴 RED（必须遵守）

## 层次职责边界

### 1. Adapters/Collectors 层（数据适配层）
**位置**: `src/api/collectors/`, `scripts/collectors/`

**职责边界**:
- ✅ 外部 API 数据获取（FotMob 等）
- ✅ 协议转换和数据标准化
- ✅ L1/L2 分层数据采集
- ❌ 禁止包含业务规则判断
- ❌ 禁止直接调用 Services 层

**依赖规则**:
- 依赖: 外部 API、配置系统
- 输出: 数据库层（matches, raw_match_data 表）

### 2. Services 层（业务逻辑层）
**位置**: `src/services/`

**职责边界**:
- ✅ 核心业务逻辑编排
- ✅ 依赖注入和 IoC 管理
- ✅ 服务生命周期管理
- ✅ 业务规则验证
- ❌ 禁止直接依赖 Adapters 具体实现
- ❌ 禁止包含数据转换逻辑

**依赖规则**:
- 依赖: Domain/Models 层、ML/Inference 层、Database 层
- 输出: API 层、Tasks/Pipelines 层

### 3. Domain/Models 层（核心领域层）
**位置**: `src/ml/models/`, `src/ml/inference/`

**职责边界**:
- ✅ ML 模型定义和管理（XGBoost）
- ✅ 核心预测逻辑
- ✅ 特征工程算法
- ✅ 金融级精度计算（Decimal）
- ❌ 禁止依赖外部资源
- ❌ 禁止包含数据库操作

**依赖规则**:
- 依赖: ML/Data 层、业务常量
- 输出: Services 层

### 4. Data Access 层（数据访问层）
**位置**: `src/ml/data/`, `src/database/`

**职责边界**:
- ✅ 数据库连接管理
- ✅ 数据加载抽象
- ✅ 异步连接池
- ❌ 禁止包含业务逻辑
- ❌ 禁止直接暴露数据库细节

**依赖规则**:
- 依赖: Database 层（PostgreSQL）
- 输出: Domain/Models 层

### 5. Tasks/Pipelines 层（编排层）
**位置**: Celery tasks、训练流水线

**职责边界**:
- ✅ 任务调度和编排
- ✅ ML 流水线管理
- ✅ 系统维护自动化
- ❌ 禁止写具体业务判断
- ❌ 禁止直接操作外部 API

**依赖规则**:
- 依赖: Services 层、ML 层
- 输出: Infrastructure 层

## 严禁的跨层操作

### 严重违规 ❌
1. Services 直接调用 Adapters 实现
   ```python
   # 错误示例
   from scripts.collectors.fotmob_collector import FotMobCollector
   class InferenceService:
       def __init__(self):
           self.collector = FotMobCollector()  # 违规！
   ```

2. Models 层包含数据库操作
   ```python
   # 错误示例
   class XGBoostModel:
       def predict(self):
           async with get_db() as db:  # 违规！
               pass
   ```

3. Collectors 层包含业务逻辑
   ```python
   # 错误示例
   class FotMobCollector:
       def collect(self):
           if probability > 0.7:  # 业务判断，违规！
               pass
   ```

### 允许的跨层交互 ✅
1. 通过接口抽象
   ```python
   # 正确示例
   from abc import ABC, abstractclass

   class DataCollectorInterface(ABC):
       @abstractmethod
       async def collect_match_data(self, match_id: str): ...

   class Service:
       def __init__(self, collector: DataCollectorInterface): ...
   ```

2. 通过依赖注入
   ```python
   # 正确示例
   class InferenceService:
       def __init__(self,
                    model: ModelInterface,
                    data_loader: DataLoaderInterface): ...
   ```

## 架构违规检测

### 自动检测规则
1. Import 检查
   - Services 层导入 Collectors → 🚨 违规
   - Models 层导入 database → 🚨 违规
   - Collectors 层导入 services → 🚨 违规

2. 调用链检查
   - 检查是否存在跨层直接调用
   - 检查是否绕过中间层

3. 数据流检查
   - 检查数据是否按层次流动
   - 检查是否存在反向依赖

### 违规处理流程
1. 检测到违规 → 立即停止生成
2. 输出警告: "⚠️ 架构违规风险：[具体违规描述]"
3. 提供修正建议
4. 等待人工确认

## 实施准则

### 新增代码时
1. 明确所属层次
2. 检查依赖关系
3. 确保不跨边界

### 修改现有代码时
1. 保持原有层次结构
2. 不引入新的跨层依赖
3. 必要时通过接口解耦

### 重构时
1. 必须保持层次完整性
2. 每次只能重构一个层次
3. 需要完整的回归测试