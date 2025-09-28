#!/usr/bin/env python3
"""
持续学习与反馈存储 - 存储 AI 修复历史并提供查询 API
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

@dataclass
class FeedbackDBConfig:
    """反馈数据库配置"""
    # 存储配置
    storage_path: str = "docs/_reports/feedback"
    max_records: int = 10000  # 最大记录数
    deduplication_enabled: bool = True

    # 数据保留策略
    retain_days: int = 90  # 保留90天数据
    cleanup_on_startup: bool = True

    # 索引配置
    enable_indexing: bool = True
    index_fields: List[str] = None

    def __post_init__(self):
        if self.index_fields is None:
            self.index_fields = ["file_path", "error_type", "fix_type", "validation_result"]

class FeedbackRecord:
    """反馈记录"""

    def __init__(self, record_id: str, timestamp: datetime, data: Dict[str, Any]):
        self.id = record_id
        self.timestamp = timestamp
        self.data = data
        self._hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """计算记录哈希值用于去重"""
        content = json.dumps(self.data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "hash": self._hash,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackRecord':
        """从字典创建记录"""
        timestamp = datetime.fromisoformat(data["timestamp"])
        return cls(data["id"], timestamp, data["data"])

class FeedbackDatabase:
    """反馈数据库"""

    def __init__(self, config: Optional[FeedbackDBConfig] = None):
        self.config = config or FeedbackDBConfig()
        self.storage_path = Path(self.config.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 数据文件
        self.data_file = self.storage_path / "feedback_data.json"
        self.index_file = self.storage_path / "feedback_index.json"

        # 索引
        self.indexes = {}
        self.records = []

        # 启动时清理旧数据
        if self.config.cleanup_on_startup:
            self._cleanup_old_data()

        # 加载数据
        self._load_data()

    def _load_data(self):
        """加载数据和索引"""
        try:
            # 加载主数据
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.records = [FeedbackRecord.from_dict(record) for record in data]

            # 加载索引
            if self.config.enable_indexing and self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.indexes = json.load(f)

            # 重建索引（如果需要）
            if self.config.enable_indexing and not self.indexes:
                self._rebuild_indexes()

        except Exception as e:
            logger.error(f"Failed to load feedback data: {e}")
            self.records = []
            self.indexes = {}

    def _cleanup_old_data(self):
        """清理旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.retain_days)

            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 过滤旧记录
                filtered_data = []
                for record in data:
                    record_date = datetime.fromisoformat(record["timestamp"])
                    if record_date > cutoff_date:
                        filtered_data.append(record)

                # 保存过滤后的数据
                if len(filtered_data) != len(data):
                    with open(self.data_file, 'w', encoding='utf-8') as f:
                        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
                    logger.info(f"Cleaned up {len(data) - len(filtered_data)} old feedback records")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")

    def add_fix_attempt(self, fix_info: Dict[str, Any]) -> str:
        """
        添加修复尝试记录

        Args:
            fix_info: 修复信息

        Returns:
            记录ID
        """
        try:
            record_id = self._generate_record_id()
            timestamp = datetime.now()

            # 标准化修复信息
            standardized_fix = self._standardize_fix_info(fix_info)

            # 去重检查
            if self.config.deduplication_enabled:
                existing_record = self._find_duplicate(standardized_fix)
                if existing_record:
                    logger.info(f"Duplicate fix attempt detected: {existing_record.id}")
                    return existing_record.id

            # 创建记录
            record = FeedbackRecord(record_id, timestamp, {
                "type": "fix_attempt",
                "fix_info": standardized_fix,
                "status": "pending_validation"
            })

            self.records.append(record)
            self._save_data()

            logger.info(f"Added fix attempt record: {record_id}")
            return record_id

        except Exception as e:
            logger.error(f"Failed to add fix attempt: {e}")
            return ""

    def add_validation_result(self, fix_id: str, validation_result: Dict[str, Any]) -> bool:
        """
        添加验证结果

        Args:
            fix_id: 修复记录ID
            validation_result: 验证结果

        Returns:
            是否成功
        """
        try:
            # 查找对应的修复记录
            fix_record = self._find_record_by_id(fix_id)
            if not fix_record:
                logger.warning(f"Fix record not found: {fix_id}")
                return False

            # 更新记录状态
            fix_record.data["validation_result"] = validation_result
            fix_record.data["status"] = "validated"
            fix_record.data["validated_at"] = datetime.now().isoformat()

            self._save_data()

            logger.info(f"Added validation result for fix: {fix_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add validation result: {e}")
            return False

    def add_test_generation(self, file_path: str, generation_result: Dict[str, Any]) -> str:
        """
        添加测试生成记录

        Args:
            file_path: 目标文件路径
            generation_result: 生成结果

        Returns:
            记录ID
        """
        try:
            record_id = self._generate_record_id()
            timestamp = datetime.now()

            record = FeedbackRecord(record_id, timestamp, {
                "type": "test_generation",
                "file_path": file_path,
                "generation_result": generation_result,
                "status": "completed"
            })

            self.records.append(record)
            self._save_data()

            logger.info(f"Added test generation record: {record_id}")
            return record_id

        except Exception as e:
            logger.error(f"Failed to add test generation record: {e}")
            return ""

    def add_improvement_suggestion(self, original_fix_id: str, suggestion: Dict[str, Any]) -> str:
        """
        添加改进建议

        Args:
            original_fix_id: 原始修复ID
            suggestion: 改进建议

        Returns:
            记录ID
        """
        try:
            record_id = self._generate_record_id()
            timestamp = datetime.now()

            record = FeedbackRecord(record_id, timestamp, {
                "type": "improvement_suggestion",
                "original_fix_id": original_fix_id,
                "suggestion": suggestion,
                "status": "pending"
            })

            self.records.append(record)
            self._save_data()

            logger.info(f"Added improvement suggestion: {record_id}")
            return record_id

        except Exception as e:
            logger.error(f"Failed to add improvement suggestion: {e}")
            return ""

    def query_similar_fixes(self, file_path: str, error_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        查询相似的修复案例

        Args:
            file_path: 文件路径
            error_type: 错误类型
            limit: 返回结果限制

        Returns:
            相似的修复案例列表
        """
        try:
            similar_fixes = []

            for record in self.records:
                if record.data.get("type") != "fix_attempt":
                    continue

                fix_info = record.data.get("fix_info", {})
                validation_result = record.data.get("validation_result", {})

                # 匹配条件
                file_match = file_path in fix_info.get("file_path", "")
                error_match = error_type in fix_info.get("error_type", "")

                if file_match or error_match:
                    similar_fixes.append({
                        "id": record.id,
                        "timestamp": record.timestamp.isoformat(),
                        "fix_info": fix_info,
                        "validation_result": validation_result,
                        "similarity_score": self._calculate_similarity(fix_info, {"file_path": file_path, "error_type": error_type})
                    })

            # 按相似度排序并限制结果数量
            similar_fixes.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar_fixes[:limit]

        except Exception as e:
            logger.error(f"Failed to query similar fixes: {e}")
            return []

    def query_fix_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        查询修复统计信息

        Args:
            days: 统计天数

        Returns:
            统计信息
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            stats = {
                "total_fix_attempts": 0,
                "successful_fixes": 0,
                "failed_fixes": 0,
                "average_quality_score": 0,
                "top_error_types": {},
                "top_file_paths": {},
                "validation_results": {
                    "excellent": 0,
                    "good": 0,
                    "acceptable": 0,
                    "needs_improvement": 0,
                    "poor": 0
                }
            }

            quality_scores = []

            for record in self.records:
                if record.timestamp < cutoff_date:
                    continue

                if record.data.get("type") == "fix_attempt":
                    stats["total_fix_attempts"] += 1

                    validation_result = record.data.get("validation_result", {})
                    quality_score = validation_result.get("quality_score", 0)
                    overall_result = validation_result.get("overall_result", "unknown")

                    if quality_score > 0:
                        quality_scores.append(quality_score)

                    # 统计验证结果
                    if overall_result in stats["validation_results"]:
                        stats["validation_results"][overall_result] += 1

                    # 统计成功/失败
                    if overall_result in ["excellent", "good", "acceptable"]:
                        stats["successful_fixes"] += 1
                    else:
                        stats["failed_fixes"] += 1

                    # 统计错误类型
                    fix_info = record.data.get("fix_info", {})
                    error_type = fix_info.get("error_type", "unknown")
                    stats["top_error_types"][error_type] = stats["top_error_types"].get(error_type, 0) + 1

                    # 统计文件路径
                    file_path = fix_info.get("file_path", "unknown")
                    stats["top_file_paths"][file_path] = stats["top_file_paths"].get(file_path, 0) + 1

            # 计算平均质量分数
            if quality_scores:
                stats["average_quality_score"] = sum(quality_scores) / len(quality_scores)

            # 排序top统计
            stats["top_error_types"] = dict(sorted(stats["top_error_types"].items(), key=lambda x: x[1], reverse=True)[:10])
            stats["top_file_paths"] = dict(sorted(stats["top_file_paths"].items(), key=lambda x: x[1], reverse=True)[:10])

            return stats

        except Exception as e:
            logger.error(f"Failed to query fix statistics: {e}")
            return {}

    def get_learning_patterns(self) -> Dict[str, Any]:
        """获取学习模式"""
        try:
            patterns = {
                "common_fix_patterns": {},
                "effective_strategies": {},
                "problematic_approaches": {},
                "success_factors": []
            }

            # 分析成功和失败的修复模式
            successful_fixes = []
            failed_fixes = []

            for record in self.records:
                if record.data.get("type") != "fix_attempt":
                    continue

                validation_result = record.data.get("validation_result", {})
                overall_result = validation_result.get("overall_result", "unknown")

                fix_info = record.data.get("fix_info", {})
                fix_pattern = self._extract_fix_pattern(fix_info)

                if overall_result in ["excellent", "good"]:
                    successful_fixes.append(fix_pattern)
                elif overall_result in ["poor", "needs_improvement"]:
                    failed_fixes.append(fix_pattern)

            # 分析共同模式
            patterns["common_fix_patterns"] = self._find_common_patterns(successful_fixes + failed_fixes)
            patterns["effective_strategies"] = self._find_common_patterns(successful_fixes)
            patterns["problematic_approaches"] = self._find_common_patterns(failed_fixes)

            # 分析成功因素
            patterns["success_factors"] = self._analyze_success_factors(successful_fixes, failed_fixes)

            return patterns

        except Exception as e:
            logger.error(f"Failed to get learning patterns: {e}")
            return {}

    def _generate_record_id(self) -> str:
        """生成记录ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
        return f"fb_{timestamp}_{random_suffix}"

    def _standardize_fix_info(self, fix_info: Dict[str, Any]) -> Dict[str, Any]:
        """标准化修复信息"""
        standardized = {
            "file_path": fix_info.get("file_path", ""),
            "error_type": fix_info.get("error_type", "unknown"),
            "fix_type": fix_info.get("fix_type", "unknown"),
            "description": fix_info.get("description", ""),
            "changes": fix_info.get("changes", []),
            "timestamp": datetime.now().isoformat()
        }

        return standardized

    def _find_duplicate(self, fix_info: Dict[str, Any]) -> Optional[FeedbackRecord]:
        """查找重复记录"""
        content = json.dumps(fix_info, sort_keys=True)
        new_hash = hashlib.md5(content.encode()).hexdigest()

        for record in self.records:
            if record._hash == new_hash:
                return record

        return None

    def _find_record_by_id(self, record_id: str) -> Optional[FeedbackRecord]:
        """根据ID查找记录"""
        for record in self.records:
            if record.id == record_id:
                return record
        return None

    def _calculate_similarity(self, fix1: Dict[str, Any], fix2: Dict[str, Any]) -> float:
        """计算两个修复的相似度"""
        similarity = 0.0

        # 文件路径相似度
        if fix1.get("file_path") == fix2.get("file_path"):
            similarity += 0.4

        # 错误类型相似度
        if fix1.get("error_type") == fix2.get("error_type"):
            similarity += 0.3

        # 修复类型相似度
        if fix1.get("fix_type") == fix2.get("fix_type"):
            similarity += 0.3

        return similarity

    def _extract_fix_pattern(self, fix_info: Dict[str, Any]) -> Dict[str, Any]:
        """提取修复模式"""
        return {
            "file_path": fix_info.get("file_path", ""),
            "error_type": fix_info.get("error_type", ""),
            "fix_type": fix_info.get("fix_type", ""),
            "change_count": len(fix_info.get("changes", []))
        }

    def _find_common_patterns(self, fix_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """查找共同模式"""
        patterns = {}

        for fix in fix_list:
            key = f"{fix['file_path']}_{fix['error_type']}_{fix['fix_type']}"
            patterns[key] = patterns.get(key, 0) + 1

        return dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:10])

    def _analyze_success_factors(self, successful_fixes: List[Dict[str, Any]], failed_fixes: List[Dict[str, Any]]) -> List[str]:
        """分析成功因素"""
        factors = []

        # 分析成功修复的共同特征
        if successful_fixes:
            success_files = set(fix["file_path"] for fix in successful_fixes)
            factors.append(f"常见修复文件: {', '.join(list(success_files)[:3])}")

        # 分析失败修复的避免模式
        if failed_fixes:
            failure_patterns = self._find_common_patterns(failed_fixes)
            if failure_patterns:
                factors.append(f"应避免的模式: {list(failure_patterns.keys())[0]}")

        return factors

    def _rebuild_indexes(self):
        """重建索引"""
        if not self.config.enable_indexing:
            return

        self.indexes = {}

        for field in self.config.index_fields:
            self.indexes[field] = {}

        for record in self.records:
            for field in self.config.index_fields:
                value = record.data.get(field, "")
                if value:
                    if value not in self.indexes[field]:
                        self.indexes[field][value] = []
                    self.indexes[field][value].append(record.id)

        self._save_indexes()

    def _save_data(self):
        """保存数据和索引"""
        try:
            # 限制记录数量
            if len(self.records) > self.config.max_records:
                self.records = self.records[-self.config.max_records:]

            # 保存主数据
            data = [record.to_dict() for record in self.records]
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 保存索引
            if self.config.enable_indexing:
                self._save_indexes()

        except Exception as e:
            logger.error(f"Failed to save feedback data: {e}")

    def _save_indexes(self):
        """保存索引"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.indexes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save indexes: {e}")

    def export_data(self, output_path: str) -> bool:
        """导出数据"""
        try:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_records": len(self.records),
                "records": [record.to_dict() for record in self.records],
                "indexes": self.indexes
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported feedback data to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        return {
            "total_records": len(self.records),
            "storage_path": str(self.storage_path),
            "config": asdict(self.config),
            "indexed_fields": list(self.indexes.keys()) if self.indexes else [],
            "oldest_record": min(record.timestamp for record in self.records).isoformat() if self.records else None,
            "newest_record": max(record.timestamp for record in self.records).isoformat() if self.records else None
        }


def main():
    """主函数 - 用于测试"""
    import argparse

    parser = argparse.ArgumentParser(description="Feedback Database")
    parser.add_argument("--info", action="store_true", help="Show database info")
    parser.add_argument("--stats", type=int, help="Show statistics for N days")
    parser.add_argument("--patterns", action="store_true", help="Show learning patterns")
    parser.add_argument("--export", type=str, help="Export data to file")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old data")

    args = parser.parse_args()

    db = FeedbackDatabase()

    if args.info:
        info = db.get_database_info()
        print(json.dumps(info, indent=2))
    elif args.stats:
        stats = db.query_fix_statistics(args.stats)
        print(json.dumps(stats, indent=2))
    elif args.patterns:
        patterns = db.get_learning_patterns()
        print(json.dumps(patterns, indent=2))
    elif args.export:
        success = db.export_data(args.export)
        print(f"Export {'successful' if success else 'failed'}")
    elif args.cleanup:
        db._cleanup_old_data()
        print("Cleanup completed")
    else:
        print("Please specify an action (--info, --stats, --patterns, --export, --cleanup)")


if __name__ == "__main__":
    main()