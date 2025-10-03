============================================================
MLflow 安全审计报告
============================================================
项目路径: .
审计时间: 3.11.9 (main, Aug  8 2025, 00:29:36) [GCC 11.4.0]

📊 统计信息
------------------------------
总文件数: 551
有问题的文件数: 9
总问题数: 32
高危问题: 5
中危问题: 27
低危问题: 0

📋 问题类型分布
------------------------------
unsafe_import: 15
unsafe_pattern_unrestricted_set_tracking_uri: 5
unsafe_model_load: 2
unsafe_model_log: 3
unsafe_pattern_direct_load_model: 3
unsafe_pattern_direct_log_model: 4

🔍 详细问题列表
------------------------------

🚨 高危问题:
  文件: src/utils/mlflow_security.py:107
  描述: 直接使用 mlflow.sklearn.load_model，存在反序列化风险
  代码: mlflow.sklearn.load_model()

  文件: src/utils/mlflow_security.py:107
  描述: 检测到不安全的模式: direct_load_model
  代码: model = mlflow.sklearn.load_model(model_uri, **kwargs)

  文件: src/models/prediction_service.py:340
  描述: 直接使用 mlflow.sklearn.load_model，存在反序列化风险
  代码: mlflow.sklearn.load_model()

  文件: src/models/prediction_service.py:340
  描述: 检测到不安全的模式: direct_load_model
  代码: model = mlflow.sklearn.load_model(model_uri)

  文件: scripts/security/mlflow_audit.py:121
  描述: 检测到不安全的模式: direct_load_model
  代码: 'code': 'mlflow.sklearn.load_model()'


⚠️ 中危问题:
  文件: src/api/health.py:382
  描述: 导入 mlflow.mlflow.tracking，建议使用安全封装
  代码: from mlflow.tracking import ...

  文件: src/api/health.py:384
  描述: 直接导入 mlflow，建议使用安全封装
  代码: import mlflow

  文件: src/api/health.py:398
  描述: 检测到不安全的模式: unrestricted_set_tracking_uri
  代码: mlflow.set_tracking_uri(tracking_uri)

  文件: src/api/models.py:19
  描述: 导入 mlflow.mlflow，建议使用安全封装
  代码: from mlflow import ...

  文件: src/utils/mlflow_security.py:91
  描述: 导入 mlflow.mlflow.exceptions，建议使用安全封装
  代码: from mlflow.exceptions import ...

  文件: src/utils/mlflow_security.py:144
  描述: 直接导入 mlflow，建议使用安全封装
  代码: import mlflow

  文件: src/utils/mlflow_security.py:169
  描述: 直接导入 mlflow，建议使用安全封装
  代码: import mlflow

  文件: src/utils/mlflow_security.py:214
  描述: 直接使用 mlflow.sklearn.log_model，可能记录敏感信息
  代码: mlflow.sklearn.log_model()

  文件: src/utils/mlflow_security.py:214
  描述: 检测到不安全的模式: direct_log_model
  代码: mlflow.sklearn.log_model(

  文件: src/monitoring/system_monitor.py:646
  描述: 直接导入 mlflow，建议使用安全封装
  代码: import mlflow

  文件: src/models/prediction_service.py:66
  描述: 导入 mlflow.mlflow.exceptions，建议使用安全封装
  代码: from mlflow.exceptions import ...

  文件: src/models/prediction_service.py:69
  描述: 直接导入 mlflow，建议使用安全封装
  代码: import mlflow

  文件: src/models/prediction_service.py:70
  描述: 导入 mlflow.mlflow，建议使用安全封装
  代码: from mlflow import ...

  文件: src/models/prediction_service.py:208
  描述: 检测到不安全的模式: unrestricted_set_tracking_uri
  代码: mlflow.set_tracking_uri(self.mlflow_tracking_uri)

  文件: src/models/model_training.py:42
  描述: 直接导入 mlflow，建议使用安全封装
  代码: import mlflow

  文件: src/models/model_training.py:43
  描述: 导入 mlflow.mlflow，建议使用安全封装
  代码: from mlflow import ...

  文件: src/models/model_training.py:512
  描述: 直接使用 mlflow.sklearn.log_model，可能记录敏感信息
  代码: mlflow.sklearn.log_model()

  文件: src/models/model_training.py:117
  描述: 检测到不安全的模式: unrestricted_set_tracking_uri
  代码: mlflow.set_tracking_uri(self.mlflow_tracking_uri)

  文件: src/models/model_training.py:512
  描述: 检测到不安全的模式: direct_log_model
  代码: mlflow.sklearn.log_model(

  文件: scripts/retrain_pipeline.py:26
  描述: 直接导入 mlflow，建议使用安全封装
  代码: import mlflow

  文件: scripts/retrain_pipeline.py:27
  描述: 导入 mlflow.mlflow，建议使用安全封装
  代码: from mlflow import ...

  文件: scripts/retrain_pipeline.py:373
  描述: 直接使用 mlflow.sklearn.log_model，可能记录敏感信息
  代码: mlflow.sklearn.log_model()

  文件: scripts/retrain_pipeline.py:40
  描述: 检测到不安全的模式: unrestricted_set_tracking_uri
  代码: mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

  文件: scripts/retrain_pipeline.py:373
  描述: 检测到不安全的模式: direct_log_model
  代码: mlflow.sklearn.log_model(

  文件: scripts/analysis/comprehensive_mcp_health_check.py:347
  描述: 直接导入 mlflow，建议使用安全封装
  代码: import mlflow

  文件: scripts/analysis/comprehensive_mcp_health_check.py:349
  描述: 检测到不安全的模式: unrestricted_set_tracking_uri
  代码: mlflow.set_tracking_uri("sqlite:///mlflow.db")

  文件: scripts/security/mlflow_audit.py:132
  描述: 检测到不安全的模式: direct_log_model
  代码: 'code': 'mlflow.sklearn.log_model()'


🔧 修复建议
------------------------------
1. 使用 src/utils/mlflow_security.py 中的安全封装
2. 在加载模型前验证模型签名
3. 在沙箱环境中执行模型操作
4. 限制模型记录的信息，避免泄露敏感数据
5. 启用 MLflow 访问控制和审计日志