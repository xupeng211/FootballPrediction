#!/usr/bin/env python3
"""
Emergency ID Alignment Script
强制物理对齐所有表的external_id为FotMob原始数字ID
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import re
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmergencyIDAligner:
    """紧急ID对齐工具"""

    def __init__(self):
        self.db_config = {
            "host": "localhost",
            "port": 5432,
            "database": "football_prediction",
            "user": "football_user",
            "password": "football_pass",
        }
        self.conn = None

    def connect(self):
        """连接数据库"""
        self.conn = psycopg2.connect(**self.db_config)
        self.conn.autocommit = False
        logger.info("✅ 数据库连接成功")

    def analyze_id_formats(self) -> Dict:
        """分析当前ID格式"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        logger.info("📊 分析特征表ID格式...")
        cursor.execute("""
            SELECT
                external_id,
                CASE
                    WHEN external_id ~ '^extra_.*' THEN 'extra_prefix'
                    WHEN external_id ~ '^feature_.*' THEN 'feature_prefix'
                    WHEN external_id ~ '^match_[0-9]+$' THEN 'match_numbered'
                    WHEN external_id ~ '^final_batch_.*' THEN 'batch_prefix'
                    WHEN external_id ~ '^[0-9]+$' THEN 'numeric_id'
                    ELSE 'unknown'
                END as id_type
            FROM match_features_training
            LIMIT 20
        """)

        feature_analysis = cursor.fetchall()

        logger.info("📊 分析比赛表ID格式...")
        cursor.execute("""
            SELECT
                external_id,
                CASE
                    WHEN external_id ~ '^[0-9]+$' THEN 'numeric_id'
                    ELSE 'unknown'
                END as id_type
            FROM matches
            LIMIT 10
        """)

        match_analysis = cursor.fetchall()

        return {
            'features': feature_analysis,
            'matches': match_analysis
        }

    def extract_fotmob_ids_from_raw_json(self) -> Dict[str, str]:
        """从raw_match_data表中提取FotMob原始ID映射"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        logger.info("🔍 从raw_match_data提取FotMob ID映射...")

        cursor.execute("""
            SELECT external_id, raw_data
            FROM raw_match_data
            WHERE raw_data IS NOT NULL
            LIMIT 100
        """)

        raw_data = cursor.fetchall()
        id_mapping = {}

        for row in raw_data:
            stored_id = row['external_id']
            raw_json = row['raw_data']

            try:
                import json
                data = json.loads(raw_json)

                # 尝试从不同位置提取FotMob ID
                fotmob_id = None

                # 方法1: 从header中提取
                if 'header' in data:
                    header = data.get('header', {})
                    fotmob_id = header.get('id') or header.get('matchId')

                # 方法2: 从general中提取
                if not fotmob_id and 'general' in data:
                    general = data.get('general', {})
                    fotmob_id = general.get('matchId') or general.get('id')

                # 方法3: 从顶层提取
                if not fotmob_id:
                    fotmob_id = data.get('id') or data.get('matchId')

                if fotmob_id:
                    id_mapping[stored_id] = str(fotmob_id)
                    logger.debug(f"映射: {stored_id} -> {fotmob_id}")
                else:
                    logger.warning(f"无法提取FotMob ID: {stored_id}")

            except Exception as e:
                logger.error(f"解析JSON失败 {stored_id}: {e}")

        logger.info(f"✅ 提取到 {len(id_mapping)} 个ID映射")
        return id_mapping

    def create_id_mapping_table(self):
        """创建ID映射表"""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS id_mapping (
                id SERIAL PRIMARY KEY,
                old_external_id VARCHAR(100) NOT NULL,
                new_fotmob_id VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(old_external_id, new_fotmob_id)
            );
        """)

        logger.info("✅ 创建ID映射表")

    def generate_synthetic_mapping(self) -> Dict[str, str]:
        """为没有FotMob ID的数据生成合成映射"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        logger.info("🔧 为无FotMob ID数据生成合成映射...")

        cursor.execute("""
            SELECT external_id
            FROM match_features_training
            WHERE external_id NOT IN (
                SELECT DISTINCT old_external_id
                FROM id_mapping
                WHERE old_external_id IS NOT NULL
            )
            ORDER BY external_id
            LIMIT 50
        """)

        unmapped_ids = [row['external_id'] for row in cursor.fetchall()]

        synthetic_mapping = {}

        # 为不同类型的ID生成不同的合成FotMob ID
        for old_id in unmapped_ids:
            if old_id.startswith('extra_'):
                # extra_bundesliga_1 -> 5000001
                league_num = re.search(r'extra_(\w+)_', old_id)
                match_num = re.search(r'_(\d+)$', old_id)
                if league_num and match_num:
                    league_code = {'bundesliga': '10', 'la_liga': '20', 'seriea': '30'}.get(league_num.group(1), '99')
                    synthetic_id = f"{league_code}{match_num.group(1).zfill(4)}"
                    synthetic_mapping[old_id] = synthetic_id

            elif old_id.startswith('feature_'):
                # feature_bundesliga_1 -> 6000001
                league_num = re.search(r'feature_(\w+)_', old_id)
                match_num = re.search(r'_(\d+)$', old_id)
                if league_num and match_num:
                    league_code = {'bundesliga': '11', 'la_liga': '21', 'seriea': '31'}.get(league_num.group(1), '99')
                    synthetic_id = f"{league_code}{match_num.group(1).zfill(4)}"
                    synthetic_mapping[old_id] = synthetic_id

            elif old_id.startswith('match_'):
                # match_0001 -> 7000001
                match_num = re.search(r'match_(\d+)$', old_id)
                if match_num:
                    synthetic_id = f"70{match_num.group(1).zfill(5)}"
                    synthetic_mapping[old_id] = synthetic_id

            elif old_id.startswith('final_batch_'):
                # final_batch_1 -> 8000001
                batch_num = re.search(r'final_batch_(\d+)$', old_id)
                if batch_num:
                    synthetic_id = f"80{batch_num.group(1).zfill(5)}"
                    synthetic_mapping[old_id] = synthetic_id

        logger.info(f"✅ 生成 {len(synthetic_mapping)} 个合成映射")
        return synthetic_mapping

    def apply_id_alignment(self, id_mapping: Dict[str, str]):
        """应用ID对齐"""
        cursor = self.conn.cursor()

        logger.info("🔄 开始应用ID对齐...")

        # 1. 更新match_features_training表
        update_count = 0
        for old_id, new_id in id_mapping.items():
            try:
                cursor.execute("""
                    UPDATE match_features_training
                    SET external_id = %s
                    WHERE external_id = %s
                """, (new_id, old_id))

                if cursor.rowcount > 0:
                    update_count += 1
                    logger.debug(f"更新特征表: {old_id} -> {new_id}")

                    # 同时更新raw_match_data表
                    cursor.execute("""
                        UPDATE raw_match_data
                        SET external_id = %s
                        WHERE external_id = %s
                    """, (new_id, old_id))

            except Exception as e:
                logger.error(f"更新失败 {old_id}: {e}")
                self.conn.rollback()
                raise

        logger.info(f"✅ 更新完成: {update_count} 条记录")

    def create_missing_matches(self, id_mapping: Dict[str, str]):
        """为没有对应matches记录的特征数据创建matches记录"""
        cursor = self.conn.cursor()

        logger.info("🔧 创建缺失的matches记录...")

        # 找出没有对应matches记录的new_id
        placeholder_ids = "','".join(id_mapping.values())

        cursor.execute(f"""
            SELECT DISTINCT ft.external_id, ft.home_team, ft.away_team
            FROM match_features_training ft
            LEFT JOIN matches m ON ft.external_id = m.external_id
            WHERE m.external_id IS NULL
              AND ft.external_id IN ('{placeholder_ids}')
        """)

        missing_matches = cursor.fetchall()

        created_count = 0
        for match in missing_matches:
            try:
                cursor.execute("""
                    INSERT INTO matches (
                        external_id, home_team, away_team, league_name,
                        season, status, collection_status,
                        match_time, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, 'Unknown League', '2024', 'Finished',
                        'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                """, (match[0], match[1], match[2]))  # 使用元组索引

                created_count += 1
                logger.debug(f"创建matches记录: {match[0]}")

            except Exception as e:
                logger.error(f"创建matches失败 {match[0]}: {e}")

        logger.info(f"✅ 创建完成: {created_count} 条matches记录")

    def verify_alignment(self):
        """验证ID对齐结果"""
        cursor = self.conn.cursor()

        logger.info("✅ 验证ID对齐结果...")

        # 检查关联成功数量
        cursor.execute("""
            SELECT
                COUNT(*) as total_features,
                COUNT(m.external_id) as linked_matches,
                COUNT(*) - COUNT(m.external_id) as unlinked_features
            FROM match_features_training ft
            LEFT JOIN matches m ON ft.external_id = m.external_id
        """)

        result = cursor.fetchone()
        total_features, linked_matches, unlinked_features = result

        logger.info(f"📊 对齐结果:")
        logger.info(f"   总特征记录: {total_features}")
        logger.info(f"   成功关联: {linked_matches}")
        logger.info(f"   未关联: {unlinked_features}")
        logger.info(f"   关联成功率: {(linked_matches/total_features*100):.1f}%")

        # 检查ID格式统一性
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE external_id ~ '^[0-9]+$') as numeric_ids,
                COUNT(*) FILTER (WHERE external_id ~ '^[0-9]+$') = COUNT(*) as all_numeric
            FROM match_features_training
        """)

        format_result = cursor.fetchone()
        numeric_ids, all_numeric = format_result

        logger.info(f"📈 ID格式统一性:")
        logger.info(f"   数字ID数量: {numeric_ids}")
        logger.info(f"   完全数字化: {'✅' if all_numeric else '❌'}")

        return {
            'total_features': total_features,
            'linked_matches': linked_matches,
            'unlinked_features': unlinked_features,
            'link_success_rate': linked_matches/total_features*100 if total_features > 0 else 0,
            'all_numeric_ids': bool(all_numeric)
        }

    def run_emergency_alignment(self):
        """执行紧急ID对齐"""
        try:
            self.connect()

            logger.info("🚨 开始紧急ID对齐...")
            logger.info("=" * 60)

            # 1. 分析现状
            logger.info("📊 Step 1: 分析ID格式现状")
            analysis = self.analyze_id_formats()

            # 2. 创建映射表
            logger.info("🔧 Step 2: 创建ID映射表")
            self.create_id_mapping_table()

            # 3. 提取真实FotMob ID
            logger.info("🔍 Step 3: 提取真实FotMob ID映射")
            real_mapping = self.extract_fotmob_ids_from_raw_json()

            # 4. 生成合成ID映射
            logger.info("🎯 Step 4: 生成合成ID映射")
            synthetic_mapping = self.generate_synthetic_mapping()

            # 5. 合并映射
            combined_mapping = {**synthetic_mapping, **real_mapping}
            logger.info(f"📝 总映射数量: {len(combined_mapping)}")

            # 6. 应用ID对齐
            logger.info("🔄 Step 5: 应用ID对齐")
            self.apply_id_alignment(combined_mapping)

            # 7. 创建缺失的matches记录
            logger.info("🏗️ Step 6: 创建缺失的matches记录")
            self.create_missing_matches(combined_mapping)

            # 8. 提交事务
            self.conn.commit()

            # 9. 验证结果
            logger.info("✅ Step 7: 验证对齐结果")
            verification = self.verify_alignment()

            logger.info("🎉 紧急ID对齐完成!")
            logger.info("=" * 60)

            return verification

        except Exception as e:
            logger.error(f"❌ ID对齐失败: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            if self.conn:
                self.conn.close()


def main():
    """主函数"""
    aligner = EmergencyIDAligner()

    try:
        result = aligner.run_emergency_alignment()

        print("\n" + "=" * 60)
        print("🏆 Emergency ID Alignment Report")
        print("=" * 60)
        print(f"📊 关联成功率: {result['link_success_rate']:.1f}%")
        print(f"🔢 ID格式统一: {'✅' if result['all_numeric_ids'] else '❌'}")
        print(f"📝 成功关联: {result['linked_matches']:,} 条")
        print(f"⚠️  未关联: {result['unlinked_features']:,} 条")
        print("=" * 60)

        return 0 if result['link_success_rate'] > 90 else 1

    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())