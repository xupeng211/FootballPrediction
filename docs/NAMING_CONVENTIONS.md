# 📝 命名规范文档

## 🎯 概述

本文档定义了FootballPrediction项目的统一命名规范，确保代码、文件、目录等命名的一致性和可读性。

## 📁 目录命名规范

### 🎨 基本原则
- **使用连字符命名 (kebab-case)**
- **全小写字母**
- **避免下划线和驼峰命名**
- **名称要有意义且简洁**

### ✅ 正确示例
```bash
config/
docs/
scripts/
src/
tests/
deployment/
monitoring/
maintenance-reports/
demo-source/
full-coverage/
htmlcov-utils/
```

### ❌ 错误示例
```bash
Configs/          # 首字母大写
test_files/       # 下划线命名
srcCode/          # 驼峰命名
very_long_directory_name_for_no_reason/  # 过长
```

## 📄 文件命名规范

### 🐍 Python文件
- **使用下划线命名 (snake_case)**
- **全小写字母**
- **模块名要简短且描述性强**

#### ✅ 正确示例
```python
prediction_service.py
user_repository.py
smart_quality_fixer.py
coverage_improvement_executor.py
```

#### ❌ 错误示例
```python
PredictionService.py        # 驼峰命名
prediction-service.py       # 连字符命名
verylongmodulename.py       # 过长
```

### 📄 配置文件
- **使用点号分隔符**
- **全小写字母**

#### ✅ 正确示例
```bash
pytest.ini
pyproject.toml
alembic.ini
docker-compose.yml
.env.example
```

### 📄 文档文件
- **使用连字符命名 (kebab-case)**
- **全大写缩写词保持原样**

#### ✅ 正确示例
```bash
DIRECTORY_STRUCTURE.md
NAMING_CONVENTIONS.md
DOCKER_PRODUCTION_GUIDE.md
API_REFERENCE.md
```

## 🏗️ 代码命名规范

### 📦 包和模块
```python
# ✅ 正确
from src.domain.services import prediction_service
from src.database.repositories import user_repository
from scripts.quality import smart_quality_fixer

# ❌ 错误
from src.Domain.Services import PredictionService
from src.database.repositories import user_repository
```

### 🏛️ 类命名
```python
# ✅ 正确 - 使用帕斯卡命名 (PascalCase)
class PredictionService:
    pass

class UserRepository:
    pass

class SmartQualityFixer:
    pass

# ❌ 错误
class prediction_service:  # 小写
    pass

class user_repository:   # 小写
    pass
```

### 🔧 函数和变量
```python
# ✅ 正确 - 使用下划线命名 (snake_case)
def create_prediction(match_data: dict) -> Prediction:
    pass

def get_user_by_id(user_id: int) -> User:
    pass

user_repository = UserRepository()
prediction_result = create_prediction(match_data)

# ❌ 错误
def createPrediction(matchData: dict):  # 驼峰命名
    pass

def GetUserById(userId: int):  # 帕斯卡命名
    pass
```

### 🔄 常量
```python
# ✅ 正确 - 全大写 + 下划线
MAX_PREDICTION_COUNT = 100
DEFAULT_TIMEOUT_SECONDS = 30
API_BASE_URL = "https://api.footballprediction.com"

# ❌ 错误
maxPredictionCount = 100        # 小驼峰
MAXPREDICTIONCOUNT = 100        # 无下划线
api_base_url = "https://..."     # 小写
```

### 🏷️ 私有成员
```python
# ✅ 正确 - 单下划线前缀
class PredictionService:
    def __init__(self):
        self._repository = PredictionRepository()
        self._cache = CacheManager()

    def _validate_input(self, data: dict) -> bool:
        return True

    def __private_method(self):  # 双下划线用于真正私有
        pass

# ❌ 错误
class PredictionService:
    def __init__(self):
        self.repository = PredictionRepository()    # 缺少下划线前缀

    def validate_input(self, data: dict) -> bool:   # 缺少下划线前缀
        return True
```

## 🗄️ 数据库命名规范

### 📊 表名
```sql
-- ✅ 正确 - 使用下划线命名，复数形式
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
);

-- ❌ 错误
CREATE TABLE Prediction (     -- 单数形式
    id SERIAL PRIMARY KEY
);

CREATE TABLE user-data (      -- 连字符命名
    id SERIAL PRIMARY KEY
);
```

### 📋 列名
```sql
-- ✅ 正确 - 使用下划线命名
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    prediction_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ❌ 错误
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    userID INTEGER NOT NULL,        -- 驼峰命名
    matchID INTEGER NOT NULL,       -- 驼峰命名
    prediction-data JSONB,          -- 连字符命名
    createdAt TIMESTAMP DEFAULT NOW()  -- 驼峰命名
);
```

## 🏷️ API命名规范

### 🛣️ 端点路径
```python
# ✅ 正确 - 使用连字符命名，复数形式
@app.post("/api/v1/predictions")
async def create_prediction(prediction_data: PredictionCreate):
    pass

@app.get("/api/v1/predictions/{prediction_id}")
async def get_prediction(prediction_id: int):
    pass

@app.get("/api/v1/users/{user_id}/predictions")
async def get_user_predictions(user_id: int):
    pass

# ❌ 错误
@app.post("/api/v1/prediction")    # 单数形式
@app.post("/api/v1/predictions")   # 缺少版本号
@app.post("/api/v1/createPrediction")  # 动词在路径中
```

### 📊 查询参数
```python
# ✅ 正确 - 使用下划线命名
@app.get("/api/v1/predictions")
async def get_predictions(
    page: int = 1,
    page_size: int = 20,
    user_id: Optional[int] = None,
    created_after: Optional[datetime] = None
):
    pass

# ❌ 错误
@app.get("/api/v1/predictions")
async def get_predictions(
    Page: int = 1,              # 大写字母
    pageSize: int = 20,         # 驼峰命名
    userID: Optional[int] = None  # 驼峰命名
):
    pass
```

## 🐳 Docker命名规范

### 📦 镜像名称
```bash
# ✅ 正确 - 小写 + 连字符
footballprediction/api:latest
footballprediction/worker:v1.2.0
footballprediction/nginx:production

# ❌ 错误
FootballPrediction/API:latest    # 大写字母
football-prediction/api:latest   # 过长
footballprediction_api:latest     # 下划线
```

### 🏷️ 容器名称
```bash
# ✅ 正确 - 项目名 + 服务名
footballprediction-api-1
footballprediction-worker-1
footballprediction-nginx-1

# ❌ 错误
api_container_1                # 缺少项目名
footballprediction_api_1       # 下划线
FP-API-1                      # 缩写 + 大写
```

## 📝 环境变量命名规范

```bash
# ✅ 正确 - 项目前缀 + 下划线
FOOTBALLPREDICTION_DATABASE_URL=postgresql://...
FOOTBALLPREDICTION_REDIS_URL=redis://...
FOOTBALLPREDICTION_API_SECRET_KEY=your-secret-key
FOOTBALLPREDICTION_LOG_LEVEL=INFO

# ❌ 错误
DATABASE_URL=postgresql://...           # 缺少项目前缀
footballprediction_redis_url=...       # 小写
FOOTBALLPREDICTION-database-url=...    # 连字符
```

## 🏷️ Git命名规范

### 🌿 分支命名
```bash
# ✅ 正确 - 类型/描述格式
feature/prediction-service
fix/user-authentication-bug
refactor/database-connection-pool
docs/api-documentation-update
release/v1.2.0

# ❌ 错误
predictionServiceFeature           # 驼峰命名
fix_bug                           # 描述不够具体
new-feature                       # 缺少类型前缀
feature/very_long_branch_name_for_no_reason  # 过长
```

### 📋 提交信息
```bash
# ✅ 正确 - 类型(范围): 描述
feat(api): add prediction endpoint
fix(database): resolve connection timeout issue
docs(readme): update installation guide
style(code): fix linting errors
refactor(services): improve prediction service architecture

# ❌ 错误
add new feature                   # 缺少类型和范围
Fixed bug                        # 首字母大写
feat: add feature                # 描述不够具体
fix: fix bug                    # 重复描述
```

## 🎯 特殊命名规范

### 🧪 测试文件
```python
# ✅ 正确 - test_ + 被测试模块名
test_prediction_service.py
test_user_repository.py
test_api_endpoints.py
test_database_models.py

# ❌ 错误
PredictionServiceTest.py         # 帕斯卡命名
test-prediction-service.py       # 连字符命名
test_predictionservice.py        # 缺少下划线
```

### 📊 报告文件
```bash
# ✅ 正确 - 类型_时间戳
quality_report_20251103_094000.json
coverage_report_20251103_095000.json
performance_report_20251103_100000.json

# ❌ 错误
quality-report-20251103-094000.json  # 连字符命名
QualityReport_20251103_094000.json   # 帕斯卡命名
qr_20251103_094000.json               # 缩写
```

## 📋 命名检查清单

在创建新文件、目录或变量时，请使用以下检查清单：

### 📁 目录命名
- [ ] 使用连字符命名 (kebab-case)
- [ ] 全小写字母
- [ ] 名称有意义且简洁
- [ ] 避免过长的名称

### 📄 文件命名
- [ ] Python文件使用下划线命名
- [ ] 配置文件使用标准扩展名
- [ ] 文档文件使用连字符命名
- [ ] 名称描述文件内容

### 🐍 代码命名
- [ ] 类使用帕斯卡命名
- [ ] 函数和变量使用下划线命名
- [ ] 常量使用全大写 + 下划线
- [ ] 私有成员使用下划线前缀

### 🏷️ 其他命名
- [ ] 遵循相关领域的命名规范
- [ ] 保持一致性
- [ ] 避免缩写（除非是广泛接受的）

## 🔄 工具和自动化

### 🔍 命名检查工具
```bash
# 使用脚本检查命名规范
python3 scripts/utils/naming_convention_checker.py

# 检查目录命名
find . -type d -name "*_*" -exec echo "目录使用下划线命名: {}" \;

# 检查Python文件命名
find . -name "*.py" -name "*-*" -exec echo "Python文件使用连字符命名: {}" \;
```

### ⚙️ 自动化修复
```bash
# 自动修复常见命名问题
python3 scripts/utils/auto_fix_naming.py --target directories
python3 scripts/utils/auto_fix_naming.py --target python_files
python3 scripts/utils/auto_fix_naming.py --target documentation
```

---

**文档版本**: v1.0
**最后更新**: 2025-11-03
**维护者**: Claude AI Assistant
**相关文档**: [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) | [MAINTENANCE_GUIDE.md](MAINTENANCE_GUIDE.md)
