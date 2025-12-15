# 数据采集配置指南

## 📋 概述

本指南详细介绍足球预测系统的数据采集架构、配置方法和最佳实践。系统采用多层架构设计，支持多种数据源的高效采集，确保数据质量和实时性。

## 🏗️ 数据采集架构

### 整体架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据采集层                                │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   外部数据源     │   采集引擎       │        数据质量               │
│  (External)     │  (Collectors)   │     (Quality)               │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ • 足球API       │ • BaseCollector  │ • 数据验证                   │
│ • 博彩API       │ • OddsCollector  │ • 异常检测                   │
│ • 实时数据源     │ • FixturesCollector│ • 数据清洗                   │
│ • 历史数据库     │ • ScoresCollector│ • 格式标准化                 │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      数据存储层                                 │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Bronze层       │   Silver层       │        Gold层                │
│   (原始数据)      │   (清洗数据)      │      (业务数据)              │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ • raw_match_data │ • matches       │ • predictions               │
│ • raw_odds_data  │ • odds          │ • features                  │
│ • raw_scores_data│ • teams         │ • analytics                 │
│ • 采集日志       │ • leagues       │ • reports                   │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

### 核心组件

| 组件 | 功能 | 技术栈 | 状态 |
|------|------|--------|------|
| **BaseCollector** | 采集器基类，提供通用功能 | Python asyncio | ✅ 运行中 |
| **OddsCollector** | 赔率数据采集器 | aiohttp, 重试机制 | ✅ 运行中 |
| **FixturesCollector** | 赛程数据采集器 | REST API调用 | ✅ 运行中 |
| **ScoresCollector** | 比分数据采集器 | WebSocket/轮询 | ✅ 运行中 |
| **DataQualityMonitor** | 数据质量监控 | 自定义验证规则 | ✅ 运行中 |

## 🚀 快速开始

### 环境要求

- **Python**: 3.11+
- **数据库**: PostgreSQL 14+
- **缓存**: Redis 6+
- **网络**: 稳定的互联网连接

### 5分钟快速配置

```bash
# 1. 配置数据源环境变量
cp .env.example .env
nano .env

# 2. 设置必要的API密钥
export FOOTBALL_API_KEY="your-football-api-key"
export ODDS_API_KEY="your-odds-api-key"

# 3. 启动数据采集服务
make data-collect-start

# 4. 验证采集状态
make data-collect-status

# 5. 查看采集日志
make data-collect-logs
```

## ⚙️ 数据源配置

### 1. 足球数据API配置

#### 环境变量设置

```bash
# .env
# 足球数据API配置
FOOTBALL_API_BASE_URL="https://api.football-data.org/v4"
FOOTBALL_API_KEY="your-football-api-key-here"
FOOTBALL_API_RATE_LIMIT="10"  # 每分钟请求限制
FOOTBALL_API_TIMEOUT="30"     # 请求超时时间（秒）

# 数据采集频率配置
FIXTURES_COLLECTION_INTERVAL="3600"  # 赛程采集间隔（秒）
LIVE_SCORES_COLLECTION_INTERVAL="60" # 实时比分采集间隔（秒）
```

#### API密钥获取

1. **football-data.org**
   - 访问 [https://www.football-data.org/login](https://www.football-data.org/login)
   - 注册账户并获取免费API密钥
   - 免费版本：每分钟10次请求

2. **TheOdds API** (可选)
   - 访问 [https://the-odds-api.com/](https://the-odds-api.com/)
   - 注册获取API密钥
   - 支持赔率数据采集

### 2. 数据库配置

#### Bronze层表结构

```sql
-- 原始比赛数据表
CREATE TABLE raw_match_data (
    id SERIAL PRIMARY KEY,
    data_source VARCHAR(100) NOT NULL,
    external_match_id VARCHAR(100) NOT NULL,
    external_league_id VARCHAR(100),
    raw_data JSONB NOT NULL,
    match_time TIMESTAMP,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    UNIQUE(data_source, external_match_id)
);

-- 原始赔率数据表
CREATE TABLE raw_odds_data (
    id SERIAL PRIMARY KEY,
    data_source VARCHAR(100) NOT NULL,
    external_match_id VARCHAR(100) NOT NULL,
    bookmaker VARCHAR(50),
    market_type VARCHAR(50),
    raw_data JSONB NOT NULL,
    odds_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    UNIQUE(data_source, external_match_id, bookmaker, market_type)
);

-- 原始比分数据表
CREATE TABLE raw_scores_data (
    id SERIAL PRIMARY KEY,
    data_source VARCHAR(100) NOT NULL,
    external_match_id VARCHAR(100) NOT NULL,
    match_status VARCHAR(50),
    home_score INTEGER,
    away_score INTEGER,
    match_minute INTEGER,
    raw_data JSONB NOT NULL,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    UNIQUE(data_source, external_match_id)
);

-- 数据采集日志表
CREATE TABLE data_collection_logs (
    id SERIAL PRIMARY KEY,
    data_source VARCHAR(100) NOT NULL,
    collection_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Redis缓存配置

```bash
# .env
# Redis配置
REDIS_URL="redis://localhost:6379/0"
REDIS_PASSWORD="your-redis-password"
REDIS_DB="0"

# 缓存策略配置
CACHE_TTL_FIXTURES="3600"     # 赛程缓存1小时
CACHE_TTL_ODDS="300"          # 赔率缓存5分钟
CACHE_TTL_SCORES="60"         # 比分缓存1分钟
```

## 🔧 采集器配置

### 1. BaseCollector 基础配置

```python
# src/data/collectors/base_collector.py 配置示例

from src.data.collectors.base_collector import DataCollector

class CustomDataCollector(DataCollector):
    def __init__(
        self,
        data_source: str = "custom_api",
        max_retries: int = 3,
        retry_delay: int = 5,
        timeout: int = 30,
    ):
        super().__init__(
            data_source=data_source,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
        )

        # 自定义配置
        self.rate_limit = 10  # 每分钟请求限制
        self.batch_size = 100  # 批处理大小

    async def collect_fixtures(self, **kwargs) -> CollectionResult:
        """实现赛程数据采集逻辑"""
        pass

    async def collect_odds(self, **kwargs) -> CollectionResult:
        """实现赔率数据采集逻辑"""
        pass

    async def collect_live_scores(self, **kwargs) -> CollectionResult:
        """实现实时比分采集逻辑"""
        pass
```

### 2. OddsCollector 赔率采集器配置

```python
# src/data/collectors/odds_collector.py 使用示例

from src.data.collectors.odds_collector import OddsCollector

# 初始化赔率采集器
odds_collector = OddsCollector(
    data_source="the_odds_api",
    api_key="your-odds-api-key",
    base_url="https://api.the-odds-api.com/v4",
    time_window_minutes=5,  # 去重时间窗口
    max_retries=3,
    retry_delay=5,
    timeout=30
)

# 采集特定比赛的赔率
result = await odds_collector.collect_odds(
    match_ids=["match_123", "match_456"],
    bookmakers=["bet365", "pinnacle", "williamhill"],
    markets=["h2h", "spreads", "totals"]
)

print(f"采集结果: {result.status}")
print(f"成功记录: {result.success_count}")
print(f"失败记录: {result.error_count}")
```

### 3. 数据采集调度器配置

```python
# src/scheduler/data_collection_scheduler.py

import asyncio
from datetime import datetime
from src.data.collectors.odds_collector import OddsCollector
from src.data.collectors.fixtures_collector import FixturesCollector
from src.data.collectors.scores_collector import ScoresCollector

class DataCollectionScheduler:
    """数据采集调度器"""

    def __init__(self):
        self.collectors = {
            'odds': OddsCollector(),
            'fixtures': FixturesCollector(),
            'scores': ScoresCollector(),
        }
        self.running = False

    async def start(self):
        """启动调度器"""
        self.running = True
        tasks = [
            asyncio.create_task(self._schedule_odds_collection()),
            asyncio.create_task(self._schedule_fixtures_collection()),
            asyncio.create_task(self._schedule_scores_collection()),
        ]

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"调度器运行出错: {e}")
        finally:
            self.running = False

    async def _schedule_odds_collection(self):
        """定时采集赔率数据"""
        while self.running:
            try:
                result = await self.collectors['odds'].collect_odds()
                self.logger.info(f"赔率采集完成: {result.status}")

                # 等待5分钟后再次采集
                await asyncio.sleep(300)

            except Exception as e:
                self.logger.error(f"赔率采集失败: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟重试

    async def _schedule_fixtures_collection(self):
        """定时采集赛程数据"""
        while self.running:
            try:
                result = await self.collectors['fixtures'].collect_fixtures()
                self.logger.info(f"赛程采集完成: {result.status}")

                # 等待1小时后再次采集
                await asyncio.sleep(3600)

            except Exception as e:
                self.logger.error(f"赛程采集失败: {e}")
                await asyncio.sleep(300)  # 出错时等待5分钟重试

    async def _schedule_scores_collection(self):
        """定时采集比分数据"""
        while self.running:
            try:
                result = await self.collectors['scores'].collect_live_scores()
                self.logger.info(f"比分采集完成: {result.status}")

                # 等待1分钟后再次采集
                await asyncio.sleep(60)

            except Exception as e:
                self.logger.error(f"比分采集失败: {e}")
                await asyncio.sleep(30)  # 出错时等待30秒重试

# 启动调度器
scheduler = DataCollectionScheduler()
await scheduler.start()
```

## 📊 数据质量管理

### 1. 数据验证规则

```python
# src/data/quality/data_validator.py

from typing import Dict, Any, List, Optional
from datetime import datetime
import re

class DataValidator:
    """数据质量验证器"""

    def __init__(self):
        self.validation_rules = {
            'match_data': self._validate_match_data,
            'odds_data': self._validate_odds_data,
            'scores_data': self._validate_scores_data,
        }

    async def validate_data(
        self,
        data_type: str,
        data: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        验证数据质量

        Returns:
            tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        if data_type not in self.validation_rules:
            return False, [f"未知的数据类型: {data_type}"]

        return await self.validation_rules[data_type](data)

    async def _validate_match_data(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证比赛数据"""
        errors = []

        # 必填字段检查
        required_fields = ['match_id', 'home_team', 'away_team', 'match_time']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"缺少必填字段: {field}")

        # 时间格式验证
        if 'match_time' in data:
            try:
                if isinstance(data['match_time'], str):
                    datetime.fromisoformat(data['match_time'].replace('Z', '+00:00'))
            except ValueError:
                errors.append("比赛时间格式无效")

        # 球队名称格式验证
        for team_field in ['home_team', 'away_team']:
            if team_field in data and data[team_field]:
                team_name = data[team_field]
                if not isinstance(team_name, str) or len(team_name) < 2:
                    errors.append(f"球队名称格式无效: {team_field}")

        return len(errors) == 0, errors

    async def _validate_odds_data(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证赔率数据"""
        errors = []

        # 必填字段检查
        required_fields = ['match_id', 'bookmaker', 'market_type', 'outcomes']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"缺少必填字段: {field}")

        # 赔率值验证
        if 'outcomes' in data and isinstance(data['outcomes'], list):
            for outcome in data['outcomes']:
                if 'price' in outcome:
                    try:
                        price = float(outcome['price'])
                        if price <= 1.0:
                            errors.append(f"赔率值必须大于1: {price}")
                    except (ValueError, TypeError):
                        errors.append(f"赔率值格式无效: {outcome.get('price')}")

        return len(errors) == 0, errors

    async def _validate_scores_data(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证比分数据"""
        errors = []

        # 必填字段检查
        required_fields = ['match_id', 'match_status']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"缺少必填字段: {field}")

        # 比分验证
        for score_field in ['home_score', 'away_score']:
            if score_field in data and data[score_field] is not None:
                try:
                    score = int(data[score_field])
                    if score < 0:
                        errors.append(f"比分不能为负数: {score_field}")
                except (ValueError, TypeError):
                    errors.append(f"比分格式无效: {score_field}")

        # 比赛分钟验证
        if 'match_minute' in data and data['match_minute'] is not None:
            try:
                minute = int(data['match_minute'])
                if minute < 0 or minute > 120:
                    errors.append(f"比赛分钟数无效: {minute}")
            except (ValueError, TypeError):
                errors.append(f"比赛分钟数格式无效: {data['match_minute']}")

        return len(errors) == 0, errors
```

### 2. 异常检测

```python
# src/data/quality/anomaly_detector.py

import numpy as np
from typing import Dict, Any, List
from datetime import datetime, timedelta

class AnomalyDetector:
    """数据异常检测器"""

    def __init__(self):
        self.odds_history = {}  # 赔率历史数据
        self.score_history = {}  # 比分历史数据

    async def detect_odds_anomaly(self, odds_data: Dict[str, Any]) -> List[str]:
        """检测赔率数据异常"""
        anomalies = []

        match_id = odds_data.get('match_id')
        bookmaker = odds_data.get('bookmaker')
        market_type = odds_data.get('market_type')

        # 构建历史键
        history_key = f"{match_id}:{bookmaker}:{market_type}"

        # 检查赔率值异常
        if 'outcomes' in odds_data:
            for outcome in odds_data['outcomes']:
                price = outcome.get('price')
                if price:
                    # 检查极端赔率
                    if price > 1000:
                        anomalies.append(f"极端赔率值: {price}")

                    # 检查历史对比异常
                    if history_key in self.odds_history:
                        last_price = self.odds_history[history_key].get(outcome.get('name'))
                        if last_price:
                            # 检查赔率变化幅度
                            change_ratio = abs(price - last_price) / last_price
                            if change_ratio > 0.5:  # 变化超过50%
                                anomalies.append(f"赔率变化异常: {last_price} -> {price}")

        # 更新历史记录
        if history_key not in self.odds_history:
            self.odds_history[history_key] = {}

        for outcome in odds_data.get('outcomes', []):
            self.odds_history[history_key][outcome.get('name')] = outcome.get('price')

        return anomalies

    async def detect_score_anomaly(self, score_data: Dict[str, Any]) -> List[str]:
        """检测比分数据异常"""
        anomalies = []

        match_id = score_data.get('match_id')
        home_score = score_data.get('home_score', 0)
        away_score = score_data.get('away_score', 0)
        match_minute = score_data.get('match_minute', 0)

        # 检查比分逻辑异常
        if match_minute > 90 and (home_score == 0 and away_score == 0):
            anomalies.append("90分钟后仍为0-0，可能是数据错误")

        # 检查比分跳跃异常
        if match_id in self.score_history:
            last_score = self.score_history[match_id]
            last_home = last_score.get('home_score', 0)
            last_away = last_score.get('away_score', 0)
            last_minute = last_score.get('match_minute', 0)

            # 检查时间倒退
            if match_minute < last_minute:
                anomalies.append(f"比赛时间倒退: {last_minute} -> {match_minute}")

            # 检查比分跳跃
            goal_diff = (home_score + away_score) - (last_home + last_away)
            if goal_diff > 3:  # 单次更新进球超过3个
                anomalies.append(f"比分跳跃异常: {last_home}-{last_away} -> {home_score}-{away_score}")

        # 更新历史记录
        self.score_history[match_id] = {
            'home_score': home_score,
            'away_score': away_score,
            'match_minute': match_minute,
            'updated_at': datetime.now()
        }

        return anomalies
```

## 🔄 数据处理流程

### 1. 数据采集流程

```python
# src/data/pipeline/collection_pipeline.py

import asyncio
from typing import Dict, Any, List
from src.data.collectors.base_collector import CollectionResult
from src.data.quality.data_validator import DataValidator
from src.data.quality.anomaly_detector import AnomalyDetector

class DataCollectionPipeline:
    """数据采集管道"""

    def __init__(self):
        self.validator = DataValidator()
        self.anomaly_detector = AnomalyDetector()

    async def process_collection_result(
        self,
        data_type: str,
        result: CollectionResult
    ) -> Dict[str, Any]:
        """处理采集结果"""

        processed_data = []
        validation_errors = []
        anomaly_alerts = []

        if result.collected_data:
            for data_item in result.collected_data:
                try:
                    # 1. 数据验证
                    is_valid, errors = await self.validator.validate_data(data_type, data_item)
                    if not is_valid:
                        validation_errors.extend(errors)
                        continue

                    # 2. 异常检测
                    anomalies = await self._detect_anomalies(data_type, data_item)
                    if anomalies:
                        anomaly_alerts.extend(anomalies)

                    # 3. 数据清洗和标准化
                    cleaned_data = await self._clean_data(data_type, data_item)
                    if cleaned_data:
                        processed_data.append(cleaned_data)

                except Exception as e:
                    self.logger.error(f"处理数据项失败: {e}")
                    continue

        # 4. 保存处理后的数据
        if processed_data:
            await self._save_processed_data(data_type, processed_data)

        # 5. 生成处理报告
        report = {
            'data_type': data_type,
            'original_count': len(result.collected_data) if result.collected_data else 0,
            'processed_count': len(processed_data),
            'validation_errors': validation_errors,
            'anomaly_alerts': anomaly_alerts,
            'processing_time': datetime.now().isoformat(),
        }

        return report

    async def _detect_anomalies(self, data_type: str, data: Dict[str, Any]) -> List[str]:
        """检测数据异常"""
        if data_type == 'odds':
            return await self.anomaly_detector.detect_odds_anomaly(data)
        elif data_type == 'scores':
            return await self.anomaly_detector.detect_score_anomaly(data)
        return []

    async def _clean_data(self, data_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """清洗和标准化数据"""
        # 实现数据清洗逻辑
        cleaned = data.copy()

        # 标准化字段名
        field_mapping = {
            'matchId': 'match_id',
            'homeTeam': 'home_team',
            'awayTeam': 'away_team',
            'matchTime': 'match_time',
        }

        for old_field, new_field in field_mapping.items():
            if old_field in cleaned:
                cleaned[new_field] = cleaned.pop(old_field)

        # 添加处理时间戳
        cleaned['processed_at'] = datetime.now().isoformat()

        return cleaned

    async def _save_processed_data(self, data_type: str, data: List[Dict[str, Any]]) -> None:
        """保存处理后的数据到Silver层"""
        # 实现数据保存逻辑
        pass
```

### 2. 数据转换规则

```python
# src/data/processing/transformation_rules.py

from typing import Dict, Any, List
from datetime import datetime
import re

class DataTransformer:
    """数据转换器"""

    def __init__(self):
        self.transformation_rules = {
            'match_data': self._transform_match_data,
            'odds_data': self._transform_odds_data,
            'scores_data': self._transform_scores_data,
        }

    async def transform_data(self, data_type: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换原始数据为标准化格式"""
        if data_type not in self.transformation_rules:
            raise ValueError(f"不支持的数据类型: {data_type}")

        return await self.transformation_rules[data_type](raw_data)

    async def _transform_match_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换比赛数据"""
        transformed = {
            'external_match_id': raw_data.get('id'),
            'external_league_id': raw_data.get('competition', {}).get('id'),
            'home_team_name': raw_data.get('homeTeam', {}).get('name'),
            'away_team_name': raw_data.get('awayTeam', {}).get('name'),
            'home_team_id': raw_data.get('homeTeam', {}).get('id'),
            'away_team_id': raw_data.get('awayTeam', {}).get('id'),
            'match_date': self._parse_datetime(raw_data.get('utcDate')),
            'match_status': raw_data.get('status'),
            'venue': raw_data.get('venue', {}).get('name'),
            'referee': raw_data.get('referees', [{}])[0].get('name') if raw_data.get('referees') else None,
            'competition_name': raw_data.get('competition', {}).get('name'),
            'season': raw_data.get('season', {}).get('startDate', '')[:4] if raw_data.get('season') else None,
            'raw_data': raw_data,
            'transformed_at': datetime.now().isoformat(),
        }

        return transformed

    async def _transform_odds_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换赔率数据"""
        outcomes = raw_data.get('outcomes', [])

        # 解析不同类型的赔率
        home_win_odds = None
        draw_odds = None
        away_win_odds = None
        over_odds = None
        under_odds = None

        for outcome in outcomes:
            name = outcome.get('name', '').lower()
            price = outcome.get('price')

            if 'home' in name or '1' in name:
                home_win_odds = price
            elif 'away' in name or '2' in name:
                away_win_odds = price
            elif 'draw' in name or 'x' in name:
                draw_odds = price
            elif 'over' in name:
                over_odds = price
            elif 'under' in name:
                under_odds = price

        transformed = {
            'external_match_id': raw_data.get('match_id'),
            'bookmaker': raw_data.get('bookmaker'),
            'market_type': raw_data.get('market_type'),
            'home_win_odds': home_win_odds,
            'draw_odds': draw_odds,
            'away_win_odds': away_win_odds,
            'over_odds': over_odds,
            'under_odds': under_odds,
            'odds_time': self._parse_datetime(raw_data.get('last_update')),
            'raw_outcomes': outcomes,
            'raw_data': raw_data,
            'transformed_at': datetime.now().isoformat(),
        }

        return transformed

    async def _transform_scores_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """转换比分数据"""
        transformed = {
            'external_match_id': raw_data.get('match_id'),
            'match_status': raw_data.get('match_status'),
            'home_score': raw_data.get('home_score'),
            'away_score': raw_data.get('away_score'),
            'match_minute': raw_data.get('match_minute'),
            'score_time': self._parse_datetime(raw_data.get('score_time')),
            'extra_time_home': raw_data.get('extra_time_home'),
            'extra_time_away': raw_data.get('extra_time_away'),
            'penalty_shootout_home': raw_data.get('penalty_shootout_home'),
            'penalty_shootout_away': raw_data.get('penalty_shootout_away'),
            'raw_data': raw_data,
            'transformed_at': datetime.now().isoformat(),
        }

        return transformed

    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """解析日期时间字符串"""
        if not datetime_str:
            return None

        try:
            # 尝试多种日期格式
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S.%fZ',
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(datetime_str, fmt)
                except ValueError:
                    continue

        except Exception:
            pass

        return None
```

## 📈 监控和告警

### 1. 采集监控指标

```python
# src/monitoring/collection_metrics.py

from prometheus_client import Counter, Histogram, Gauge
import time

class CollectionMetrics:
    """数据采集监控指标"""

    def __init__(self):
        # 计数器
        self.collection_requests_total = Counter(
            'data_collection_requests_total',
            'Total number of data collection requests',
            ['data_source', 'data_type', 'status']
        )

        self.records_collected_total = Counter(
            'data_records_collected_total',
            'Total number of records collected',
            ['data_source', 'data_type']
        )

        self.validation_errors_total = Counter(
            'data_validation_errors_total',
            'Total number of validation errors',
            ['data_type', 'error_type']
        )

        # 直方图
        self.collection_duration = Histogram(
            'data_collection_duration_seconds',
            'Time spent collecting data',
            ['data_source', 'data_type'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )

        # 仪表
        self.active_collectors = Gauge(
            'active_data_collectors',
            'Number of active data collectors'
        )

        self.collection_queue_size = Gauge(
            'data_collection_queue_size',
            'Size of data collection queue'
        )

        self.last_collection_success_time = Gauge(
            'last_collection_success_time',
            'Unix timestamp of last successful collection',
            ['data_source', 'data_type']
        )

    def record_collection_start(self, data_source: str, data_type: str):
        """记录采集开始"""
        self.active_collectors.inc()

    def record_collection_complete(
        self,
        data_source: str,
        data_type: str,
        status: str,
        records_count: int,
        duration: float
    ):
        """记录采集完成"""
        self.active_collectors.dec()
        self.collection_requests_total.labels(
            data_source=data_source,
            data_type=data_type,
            status=status
        ).inc()

        if records_count > 0:
            self.records_collected_total.labels(
                data_source=data_source,
                data_type=data_type
            ).inc(records_count)

        self.collection_duration.labels(
            data_source=data_source,
            data_type=data_type
        ).observe(duration)

        if status == 'success':
            self.last_collection_success_time.labels(
                data_source=data_source,
                data_type=data_type
            ).set(time.time())

    def record_validation_error(self, data_type: str, error_type: str):
        """记录验证错误"""
        self.validation_errors_total.labels(
            data_type=data_type,
            error_type=error_type
        ).inc()
```

### 2. 告警规则配置

```yaml
# config/monitoring/data_collection_alerts.yml

groups:
  - name: data_collection_alerts
    rules:
      - alert: DataCollectionFailure
        expr: increase(data_collection_requests_total{status="failed"}[5m]) > 0
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "数据采集失败"
          description: "数据源 {{ $labels.data_source }} 的 {{ $labels.data_type }} 数据采集在最近5分钟内失败"

      - alert: HighCollectionLatency
        expr: histogram_quantile(0.95, rate(data_collection_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "数据采集延迟过高"
          description: "95%的数据采集请求耗时超过30秒"

      - alert: NoRecentCollection
        expr: time() - last_collection_success_time > 3600
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "数据采集中断"
          description: "数据源 {{ $labels.data_source }} 的 {{ $labels.data_type }} 数据采集已超过1小时未成功"

      - alert: HighValidationErrorRate
        expr: rate(data_validation_errors_total[5m]) / rate(data_records_collected_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "数据验证错误率过高"
          description: "数据类型 {{ $labels.data_type }} 的验证错误率超过10%"

      - name: data_quality_alerts
    rules:
      - alert: DataAnomalyDetected
        expr: increase(data_anomaly_alerts_total[5m]) > 0
        for: 1m
        labels:
          severity: info
        annotations:
          summary: "检测到数据异常"
          description: "在 {{ $labels.data_type }} 数据中检测到异常: {{ $labels.anomaly_type }}"
```

## 🛠️ 运维操作

### 1. 日常运维命令

```bash
# 数据采集服务管理
make data-collect-start      # 启动数据采集服务
make data-collect-stop       # 停止数据采集服务
make data-collect-restart    # 重启数据采集服务
make data-collect-status     # 查看采集服务状态
make data-collect-logs       # 查看采集日志

# 数据质量管理
make data-quality-check      # 运行数据质量检查
make data-validation-report  # 生成数据验证报告
make data-anomaly-scan       # 扫描数据异常
make data-cleanup           # 清理过期数据

# 监控和告警
make data-metrics           # 查看采集指标
make data-alerts           # 查看告警状态
make data-dashboard        # 打开监控面板
```

### 2. 故障排查指南

#### 采集失败排查

```bash
# 1. 检查网络连接
ping api.football-data.org
curl -I https://api.football-data.org/v4/

# 2. 验证API密钥
curl -H "X-Auth-Token: YOUR_API_KEY" \
     https://api.football-data.org/v4/competitions

# 3. 检查数据库连接
docker exec -it football-prediction_db_1 psql -U football_user -d football_prediction_dev
SELECT COUNT(*) FROM data_collection_logs WHERE created_at > NOW() - INTERVAL '1 hour';

# 4. 查看详细错误日志
docker logs football-prediction_app_1 | grep "ERROR" | tail -20
```

#### 数据质量问题排查

```sql
-- 查看原始数据中的问题记录
SELECT
    data_source,
    collection_type,
    COUNT(*) as error_count,
    error_message
FROM data_collection_logs
WHERE status = 'failed'
AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY data_source, collection_type, error_message
ORDER BY error_count DESC;

-- 检查数据完整性
SELECT
    'raw_match_data' as table_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN processed THEN 1 END) as processed_records,
    COUNT(CASE WHEN NOT processed THEN 1 END) as unprocessed_records
FROM raw_match_data
UNION ALL
SELECT
    'raw_odds_data' as table_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN processed THEN 1 END) as processed_records,
    COUNT(CASE WHEN NOT processed THEN 1 END) as unprocessed_records
FROM raw_odds_data;
```

### 3. 性能优化

#### 数据库优化

```sql
-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_raw_match_data_source_time
ON raw_match_data(data_source, collected_at);

CREATE INDEX IF NOT EXISTS idx_raw_odds_match_bookmaker
ON raw_odds_data(external_match_id, bookmaker);

CREATE INDEX IF NOT EXISTS idx_collection_logs_type_status
ON data_collection_logs(collection_type, status);

-- 分区表优化（大数据量时）
CREATE TABLE raw_match_data_partitioned (
    LIKE raw_match_data INCLUDING ALL
) PARTITION BY RANGE (collected_at);

-- 创建月度分区
CREATE TABLE raw_match_data_2024_01
PARTITION OF raw_match_data_partitioned
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

#### 采集器优化

```python
# 并发采集优化
import asyncio
from asyncio import Semaphore

class OptimizedDataCollector(DataCollector):
    def __init__(self, max_concurrent_requests: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.semaphore = Semaphore(max_concurrent_requests)

    async def collect_odds_batch(self, match_ids: List[str]) -> CollectionResult:
        """批量并发采集赔率数据"""
        tasks = []

        for match_id in match_ids:
            task = self._collect_single_match_odds(match_id)
            tasks.append(task)

        # 限制并发数
        results = await asyncio.gather(
            *[self.semaphore.acquire() and task for task in tasks],
            return_exceptions=True
        )

        # 处理结果
        successful_results = []
        error_count = 0

        for result in results:
            if isinstance(result, Exception):
                error_count += 1
                self.logger.error(f"采集任务失败: {result}")
            else:
                successful_results.extend(result)

        return CollectionResult(
            data_source=self.data_source,
            collection_type="odds",
            records_collected=len(successful_results),
            success_count=len(successful_results),
            error_count=error_count,
            status="success" if error_count == 0 else "partial"
        )
```

## 📋 最佳实践

### 1. 数据采集最佳实践

1. **错误处理和重试**
   - 实现指数退避重试机制
   - 设置合理的超时时间
   - 记录详细的错误日志

2. **数据去重**
   - 使用时间窗口去重避免重复数据
   - 基于业务关键字段生成唯一键
   - 定期清理过期的去重缓存

3. **性能优化**
   - 使用异步IO提高并发性能
   - 实现批量数据处理
   - 合理设置并发请求数限制

4. **监控和告警**
   - 监控采集成功率、延迟、错误率
   - 设置合理的告警阈值
   - 建立值班响应机制

### 2. 数据质量管理

1. **数据验证**
   - 实现多层次数据验证规则
   - 验证数据格式、完整性、一致性
   - 记录验证结果和错误信息

2. **异常检测**
   - 基于历史数据检测异常值
   - 设置合理的异常阈值
   - 及时告警通知相关人员

3. **数据清洗**
   - 标准化数据格式和字段名
   - 处理缺失值和异常值
   - 保持数据的一致性和准确性

### 3. 系统可靠性

1. **容错设计**
   - 实现优雅降级机制
   - 设置熔断器防止雪崩
   - 建立备用数据源

2. **备份和恢复**
   - 定期备份原始数据
   - 建立数据恢复流程
   - 测试备份的有效性

3. **文档和运维**
   - 维护详细的配置文档
   - 建立故障处理手册
   - 定期进行系统演练

## 📚 相关文档

### 🔗 核心文档
- **数据库架构**: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - 数据库表结构和设计
- **开发指南**: [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) - 开发环境搭建和规范
- **机器学习模型**: [../ml/ML_MODEL_GUIDE.md](../ml/ML_MODEL_GUIDE.md) - ML模型开发和训练
- **监控系统**: [MONITORING_GUIDE.md](MONITORING_GUIDE.md) - 系统监控和告警
- **API文档**: [API_REFERENCE.md](API_REFERENCE.md) - REST API接口说明
- **术语表**: [glossary.md](glossary.md) - 项目术语和概念定义

### 🏗️ 架构相关
- [系统架构文档](../architecture/SYSTEM_ARCHITECTURE.md) - 整体系统架构
- [数据架构设计](../architecture/DATA_DESIGN.md) - 数据层架构详情
- [重试机制设计](../architecture/RETRY_MECHANISM_DESIGN.md) - 容错和重试机制

### 🛠️ 运维和部署
- [生产部署指南](../ops/PRODUCTION_DEPLOYMENT_GUIDE.md) - 生产环境部署
- [运维手册](../ops/runbooks/README.md) - 运维操作指南
- [Staging环境配置](../how-to/STAGING_ENVIRONMENT.md) - 测试环境配置

### 🧪 测试相关
- [测试策略文档](../testing/TESTING_STRATEGY.md) - 测试策略和方法
- [CI Guardian系统](../testing/CI_GUARDIAN_GUIDE.md) - CI/CD质量门禁
- [性能测试方案](../testing/performance_tests.md) - 性能测试指南

### 📖 快速开始
- [完整系统演示](../how-to/COMPLETE_DEMO.md) - 系统功能演示
- [快速开始工具指南](../how-to/QUICKSTART_TOOLS.md) - 开发工具使用
- [Makefile使用指南](../how-to/MAKEFILE_GUIDE.md) - 项目工具命令

---

**文档版本**: 1.0
**最后更新**: 2025-10-23
**维护者**: 开发团队
