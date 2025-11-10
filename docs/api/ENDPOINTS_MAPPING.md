# API端点映射文档

## 📊 实际API端点 vs 文档覆盖率分析

### ✅ 已在文档中的核心端点
- 预测服务: `/api/predictions/*`
- 健康检查: `/health/*`
- 用户管理: `/api/users/*`
- 数据服务: `/api/data/*`

### 🔍 发现的新端点（需要补充到文档）

#### 观察者系统 (`src/api/observers.py`)
```
GET /observers/                    # 观察者系统根路径
GET /observers/status              # 获取观察者系统状态
GET /observers/metrics             # 获取所有指标
GET /observers/observers           # 获取所有观察者
GET /observers/subjects            # 获取所有被观察者
GET /observers/alerts              # 获取告警历史
POST /observers/alerts             # 手动触发告警
GET /observers/alerts/rules        # 获取告警规则
POST /observers/metrics/update     # 更新指标
GET /observers/predictions         # 获取预测统计
POST /observers/predictions/record # 记录预测事件
GET /observers/cache               # 获取缓存统计
POST /observers/cache/hit          # 记录缓存命中
POST /observers/cache/miss         # 记录缓存未命中
GET /observers/performance         # 获取性能指标
POST /observers/system/collect     # 触发系统指标收集
POST /observers/system/check       # 触发性能检查
GET /observers/event-types         # 获取所有事件类型
POST /observers/observer/{name}/enable  # 启用观察者
POST /observers/observer/{name}/disable # 禁用观察者
```

#### 租户管理 (`src/api/tenant_management.py`)
```
POST /tenant-management/                     # 创建租户
GET /tenant-management/{tenant_id}           # 获取租户信息
PUT /tenant-management/{tenant_id}           # 更新租户信息
POST /tenant-management/{tenant_id}/suspend  # 暂停租户
POST /tenant-management/{tenant_id}/activate # 激活租户
GET /tenant-management/{tenant_id}/statistics # 租户统计
POST /tenant-management/{tenant_id}/users/{user_id}/roles # 分配角色
DELETE /tenant-management/{tenant_id}/users/{user_id}/roles/{role_code} # 移除角色
POST /tenant-management/{tenant_id}/permissions/check # 权限检查
GET /tenant-management/                      # 获取所有租户
GET /tenant-management/health               # 租户管理健康检查
```

#### 投注服务 (`src/api/betting_api.py`)
```
GET /betting/matches                        # 获取比赛投注信息
POST /betting/predictions                   # 创建投注预测
GET /betting/odds                          # 获取赔率信息
POST /betting/analysis                     # 投注分析
```

#### 事件系统 (`src/api/events.py`)
```
GET /events/health                         # 事件系统健康检查
GET /events/stats                          # 获取事件统计
GET /events/types                          # 获取所有事件类型
GET /events/subscribers                    # 获取订阅者信息
POST /events/restart                       # 重启事件系统
GET /events/metrics                        # 获取详细指标
GET /events/predictions/recent             # 获取最近的预测统计
GET /events/users/activity                 # 获取用户活动统计
```

#### 性能管理 (`src/api/performance_management.py`)
```
GET /performance/metrics                   # 获取性能指标
GET /performance/dashboard                 # 性能仪表板
GET /performance/alerts                    # 获取性能告警
POST /performance/database/optimize         # 数据库优化
GET /performance/database/analysis         # 数据库分析
POST /performance/cache/manage             # 缓存管理
GET /performance/cache/statistics          # 缓存统计
POST /performance/api/optimize             # API优化
```

## 📈 文档完整性评估

### 当前状态
- ✅ **基础API模块**: 已完整覆盖
- ⚠️ **高级功能模块**: 需要补充
- ⚠️ **内部管理API**: 需要文档化

### 建议的文档更新优先级

#### P1: 高优先级（用户直接使用）
1. **观察者系统** - 监控和性能分析的核心
2. **事件系统** - 系统事件和通知
3. **性能管理** - 性能优化和监控

#### P2: 中等优先级（管理和运维）
1. **租户管理** - 多租户系统管理
2. **投注服务** - 投注相关功能

#### P3: 低优先级（内部工具）
1. **数据集成工具** - 内部数据管理
2. **高级预测API** - 高级分析功能

## 🎯 文档深化建议

### 1. 结构化改进
- 为每个API模块创建独立的文档文件
- 统一错误代码和响应格式
- 添加更多实际使用示例

### 2. 内容增强
- 补充所有新发现的端点
- 添加请求/响应模型说明
- 增加认证和权限说明

### 3. 开发者友好
- 创建API使用流程图
- 添加常见问题解答
- 提供调试和故障排除指南