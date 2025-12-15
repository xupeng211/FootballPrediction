# FootballPrediction 标准化脚本集合

## 🚀 官方入口点脚本

### 数据采集与更新
- **`run_l2_update.py`** - L2数据官方更新脚本
  ```bash
  python scripts/run_l2_update.py --batch-size 50 --delay 3
  ```

### 监控与审计
- **`monitor_fixed.py`** - L2数据进度监控面板
  ```bash
  python scripts/monitor_fixed.py
  ```

- **`audit_data.py`** - 数据质量审计工具
  ```bash
  python scripts/audit_data.py
  ```

## 📋 数据采集脚本

### L1 数据采集
- **`collect_l1_data.py`** - 基础赛程数据采集
- **`collect_l2_data.py`** - L2详情数据采集
- **`collect_odds_data.py`** - 赔率数据采集

### 特殊用途脚本
- **`collect_l2_enhanced.py`** - 增强版L2数据采集
- **`collect_odds_data_simple.py`** - 简化版赔率采集

## 🛠️ 系统工具

### 数据库管理
- **`setup_database.py`** - 数据库初始化
- **`reset_db.py`** - 数据库重置工具

### 开发工具
- **`generate_nowgoal_cookie.py`** - Cookie生成工具
- **`install_playwright.sh`** - Playwright安装脚本

## 🧪 测试脚本

### 冒烟测试
- **`real_l2_smoke_test.py`** - L2数据冒烟测试
- **`smoke_test_l2_enhanced.py`** - 增强版L2冒烟测试

### 性能测试
- **`simple_load_test.py`** - 简单负载测试

## ⚙️ CI/CD 脚本

- **`ci_critical_tests.sh`** - CI关键测试
- **`ci-minimal-test.py`** - 最小化CI测试

---

## 📖 使用指南

### 标准工作流
1. **启动开发环境**: `cd FootballPrediction && make dev`
2. **运行L2更新**: `python scripts/run_l2_update.py`
3. **监控进度**: `python scripts/monitor_fixed.py`
4. **审计质量**: `python scripts/audit_data.py`

### 开发规范
- ✅ 使用官方入口点脚本
- ✅ 遵循ARCHITECTURE.md中的标准化指南
- ❌ 不要创建新的collector类
- ✅ 扩展现有功能时继承标准类

### 更多信息
参考 `../ARCHITECTURE.md` 了解完整的系统架构和开发规范。