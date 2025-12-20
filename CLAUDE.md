# CLAUDE.md - FootballPrediction V2.0 项目护航规范

**项目状态**: ✅ **生产就绪** | **模型准确率**: 60.00% | **版本**: V2.0 Real Scores

---

## 🚀 唯一入口 (SINGLE ENTRY POINT)

### **强制要求：所有系统操作必须通过以下入口**

#### **1. 数据收割 + 预测入口**
```bash
# 生产环境（推荐）
python src/core/main_engine_v5.py --mode full --limit 700

# 测试环境（代码修改后必须执行）
python src/core/main_engine_v5.py --mode test
```

#### **2. Docker自动化入口**
```bash
# 一键运行预测系统
./run_daily_predict.sh
```

#### **3. 模型推理入口**
```python
# 程序化调用
from core.inference_engine import get_inference_engine
engine = get_inference_engine()
prediction = engine.predict_match(home_team, away_team, features)
```

**❌ 禁止行为**:
- 禁止直接操作数据库跳过业务逻辑
- 禁绕过main_engine_v5.py直接调用API
- 禁止使用非官方脚本进行数据操作

---

## 🔗 数据库连接规范

### **统一连接方式**
```python
# 使用统一配置系统
from src.config_unified import get_settings
settings = get_settings()
db = settings.database

# 标准连接方式
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host=db.host,
    port=db.port,
    database=db.name,
    user=db.user,
    password=db.password.get_secret_value()
)
```

### **连接安全要求**
- ✅ **必须** 使用 `config_unified.py` 获取连接参数
- ✅ **必须** 使用连接池或异步连接
- ✅ **必须** 实现异常处理和资源释放
- ❌ **禁止** 硬编码连接参数
- ❌ **禁止** 使用普通游标，必须使用 `RealDictCursor`

---

## 🛡️ 代码质量强制要求

### **修改前验证 (MANDATORY)**
```bash
# 任何代码修改后，必须执行以下命令且验证率达100%
python src/core/main_engine_v5.py --mode test
```

**验证要求**:
- ✅ 连接测试：数据库连接成功
- ✅ 配置测试：所有配置项加载正常
- ✅ 模型测试：预测引擎加载成功
- ✅ API测试：外部API连接正常
- ❌ 任何一项失败，代码禁止合并

### **代码规范**
- **Python版本**: 3.11+
- **风格标准**: Black + Flake8 + MyPy
- **日志级别**: INFO (生产), DEBUG (开发)
- **错误处理**: 必须有try-catch和适当日志
- **文档**: 所有公共方法必须有docstring

---

## 📊 生产环境运行规范

### **数据流要求**
```
外部API → 数据验证 → 特征提取 → 数据库存储
     ↓
实时预测 ← 模型推理 ← 动态特征回填 ← 历史数据查询
```

### **性能监控**
- **响应时间**: 单次预测 <100ms
- **准确率**: 维持60.00%基准
- **数据完整性**: 415场黄金数据完整性100%
- **系统可用性**: 99.9%+ uptime

### **告警机制**
- 数据收集失败率 >5% → 立即告警
- 模型准确率下降 >2% → 立即告警
- 系统响应时间 >200ms → 立即告警
- 数据库连接失败 → 立即告警

---

## 🔧 开发与部署

### **环境配置**
```bash
# 生产环境变量
export ENVIRONMENT=production
export DOCKER_ENV=true
export LOG_LEVEL=INFO

# 开发环境变量
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
```

### **Docker部署**
```bash
# 构建镜像
docker build -t footballprediction:v2.0 .

# 运行服务栈
docker-compose up -d

# 健康检查
docker-compose exec db pg_isready -U football_user
```

### **依赖管理**
- 使用 `requirements.txt` 锁定版本
- 生产环境不允许使用开发依赖
- 定期更新依赖，每周安全扫描

---

## 🚨 故障处理SOP

### **数据收集故障**
1. 检查FotMob API连接
2. 验证数据库连接
3. 检查rate limiting设置
4. 查看详细错误日志

### **预测模型故障**
1. 检查模型文件完整性
2. 验证特征数据格式
3. 检查标准化器状态
4. 回滚到上一版本

### **数据库故障**
1. 检查连接池状态
2. 验证磁盘空间
3. 检查查询性能
4. 执行数据备份

---

## 📈 性能基准

### **核心指标**
| 指标 | 基准值 | 监控阈值 |
|------|--------|----------|
| 模型准确率 | 60.00% | >58.0% |
| 预测响应时间 | <100ms | <200ms |
| 数据收集成功率 | >95% | >90% |
| 系统可用性 | 99.9% | >99.0% |

### **扩容策略**
- CPU使用率 >80% → 水平扩展
- 内存使用率 >85% → 增加内存
- 数据库连接数 >80% → 增加连接池

---

## 🔄 版本控制与发布

### **分支策略**
- `main`: 生产环境分支
- `develop`: 开发环境分支
- `feature/*`: 功能开发分支

### **发布流程**
1. 代码review通过
2. 自动化测试100%通过
3. 预发布环境验证
4. 生产环境灰度发布
5. 全量发布 + 监控

### **回滚机制**
- 数据库迁移可逆
- 模型版本可切换
- 配置热更新支持

---

## 💡 最佳实践

### **代码安全**
- 输入验证与清理
- SQL注入防护
- API密钥安全存储
- 错误信息脱敏

### **性能优化**
- 查询优化与索引
- 缓存策略实施
- 异步操作使用
- 资源池管理

### **可观测性**
- 结构化日志记录
- 关键业务指标监控
- 分布式链路追踪
- 异常实时告警

---

## 🎯 核心系统架构

### **数据层**
- PostgreSQL: 主数据库，存储415场黄金数据
- Redis: 缓存层，实时预测结果缓存
- Files: 模型存储 (xgb_football_v2_real_scores.joblib)

### **服务层**
- MainEngineV5: 数据收割 + 实时预测引擎
- InferenceEngine: V2.0模型推理核心
- FotMobAPIClient: 外部数据源接口

### **模型层**
- XGBoost V2.0: 60.00%准确率，基于真实比分
- 10个专业特征: xG、控球率、赔率 + 衍生特征
- 动态特征回填: 基于过去5场比赛历史数据

---

**最后更新**: 2025-12-21
**维护团队**: Claude AI Architecture Team
**文档版本**: V2.0 Production Ready

**🚨 重要提醒**: 本规范为生产系统护航文档，任何违反规范的修改都将被自动拒绝！