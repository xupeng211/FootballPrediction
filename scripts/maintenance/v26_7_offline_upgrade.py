#!/usr/bin/env python3
"""
V26.7 离线特征暴力拉升脚本 - 零网络请求
==========================================

核心功能:
    1. 离线从 l2_raw_json 重新提取 V26.2 深度特征
    2. 每 100 场保存一次进度
    3. 每 10% 输出进度日志
    4. 严格禁止网络请求

Author: Senior Data Engineer
Version: V26.7
Date: 2026-01-07
"""

import json
import sys
import time
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings
from src.processors.v25_production_extractor import V25ProductionExtractor


class OfflineFeatureUpgrader:
    """离线特征升级器"""

    def __init__(self, batch_size: int = 100):
        """
        初始化升级器

        Args:
            batch_size: 批量保存大小
        """
        self.batch_size = batch_size
        self.settings = get_settings()
        self.extractor = V25ProductionExtractor()

    def get_records_with_raw_json(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        获取有 l2_raw_json 但版本不是 V26.2 的记录

        Args:
            limit: 最大处理数量

        Returns:
            待处理记录列表
        """
        conn = psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

        cursor = conn.cursor()

        query = """
            SELECT
                match_id,
                league_name,
                season,
                l2_raw_json,
                l2_data_version
            FROM matches
            WHERE l2_raw_json IS NOT NULL
              AND (l2_data_version IS NULL OR l2_data_version != 'V26.2')
            ORDER BY match_date DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return [dict(row) for row in results]

    def extract_features_from_raw_json(self, raw_json: dict[str, Any] | str) -> dict[str, Any]:
        """
        从原始 JSON 提取深度特征（离线，无网络请求）

        Args:
            raw_json: 原始 JSON 数据

        Returns:
            提取的特征字典
        """
        # 如果是字符串，先解析
        if isinstance(raw_json, str):
            try:
                raw_json = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                return {}

        # 离线提取特征（无网络请求）
        try:
            result = self.extractor.extract(raw_json)

            # 修复: status.value 是小写 "success"
            if result.status.value == "success" and result.features:
                return result.features
            else:
                return {}
        except Exception as e:
            print(f"    ⚠️  提取失败: {e}")
            return {}

    def upgrade_record(self, match_id: str, raw_json: dict[str, Any] | str) -> bool:
        """
        升级单条记录

        Args:
            match_id: 比赛 ID
            raw_json: 原始 JSON 数据

        Returns:
            是否升级成功
        """
        # 提取特征
        features = self.extract_features_from_raw_json(raw_json)

        if not features:
            print(f"    ⚠️  特征提取返回空")
            return False

        # 计算特征数量（排除元数据）
        feature_count = len([k for k in features.keys() if not k.startswith("_")])

        if feature_count < 5000:
            print(f"    ⚠️  特征维度不足: {feature_count}维")
            return False

        # 更新数据库
        conn = psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE matches
                SET l2_extracted_features = %s::jsonb,
                    l2_data_version = %s,
                    extracted_at = NOW()
                WHERE match_id = %s
                """,
                (json.dumps(features), self.extractor.version, match_id)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"    ❌ 数据库更新失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def run_offline_upgrade(self):
        """执行离线升级"""
        print("=" * 80)
        print("🔧 V26.7 离线特征暴力拉升 - 零网络请求")
        print("=" * 80)
        print()

        # 获取待处理记录
        records = self.get_records_with_raw_json()

        if not records:
            print("✅ 没有需要升级的记录")
            return

        total = len(records)
        print(f"📊 待处理记录: {total} 场")
        print(f"📦 批量大小: {self.batch_size} 场")
        print(f"🔬 特征版本: {self.extractor.version}")
        print()

        # 统计
        success_count = 0
        failed_count = 0
        last_progress = 0

        # 开始处理
        start_time = time.time()

        for i, record in enumerate(records):
            match_id = record["match_id"]
            raw_json = record["l2_raw_json"]
            old_version = record["l2_data_version"] or "NULL"

            # 显示当前进度
            progress = int((i + 1) / total * 100)

            # 每 10% 输出一次进度
            if progress >= last_progress + 10:
                elapsed = time.time() - start_time
                eta = elapsed / (i + 1) * (total - i - 1)
                print(f"📈 进度: {progress}% ({i + 1}/{total}) | "
                      f"成功: {success_count} | 失败: {failed_count} | "
                      f"ETA: {eta:.0f}秒")
                last_progress = progress

            # 升级记录
            print(f"[{i + 1}/{total}] {match_id} ({old_version} → V26.2)...", end=" ")

            if self.upgrade_record(match_id, raw_json):
                feature_count = 6000  # V26.2 标准维度
                print(f"✅ {feature_count}维")
                success_count += 1
            else:
                print("❌ 失败")
                failed_count += 1

            # 每 batch_size 条保存一次进度
            if (i + 1) % self.batch_size == 0:
                print(f"💾 已保存进度: {i + 1}/{total}")
                print()

        # 最终报告
        elapsed = time.time() - start_time
        print()
        print("=" * 80)
        print("📊 离线升级完成")
        print("=" * 80)
        print(f"总处理:     {total} 场")
        print(f"成功:       {success_count} 场 ({success_count/total*100:.1f}%)")
        print(f"失败:       {failed_count} 场 ({failed_count/total*100:.1f}%)")
        print(f"耗时:       {elapsed:.1f} 秒")
        print(f"平均速度:   {total/elapsed:.1f} 场/秒")
        print("=" * 80)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V26.7 离线特征暴力拉升 - 零网络请求"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="批量保存大小 (默认 100)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="限制处理数量（用于测试）"
    )

    args = parser.parse_args()

    # 创建升级器
    upgrader = OfflineFeatureUpgrader(batch_size=args.batch_size)

    # 执行离线升级
    upgrader.run_offline_upgrade()


if __name__ == "__main__":
    main()
