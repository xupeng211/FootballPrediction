================================================================================
🏥 本地CI模拟诊断报告
================================================================================
📅 时间: 2025-12-12 02:32:06
📁 项目根目录: /home/user/projects/FootballPrediction

🔧 CI环境变量:
   FOOTBALL_PREDICTION_ML_MODE=mock
   SKIP_ML_MODEL_LOADING=true
   INFERENCE_SERVICE_MOCK=true
   PYTHONPATH=/home/user/projects/FootballPrediction
   CI=true
   GITHUB_ACTIONS=true

📦 ✅ 所有依赖满足

🚀 应用启动测试:
   ✅ 主应用导入
   ✅ 配置加载
   ✅ 日志系统
   ✅ 监控模块

🔍 代码质量检查:
   ✅ ruff
   ✅ ruff_format
   ❌ mypy
      🔴 3 个错误
   ❌ bandit
      🔴 16 个错误
      🟡 2 个警告

🎯 问题总结:
   ❌ mypy检查失败
   ❌ bandit检查失败
   ❌ 快速测试失败
   ❌ 收集测试失败

================================================================================