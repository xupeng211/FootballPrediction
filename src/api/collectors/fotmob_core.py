#!/usr/bin/env python3
"""
FotMob 核心数据采集器 - V10.9 护航加固版
集成自适应解码、哨兵检查和故障熔断逻辑
"""

import json
import requests
import psycopg2
import gzip
import logging
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import brotli

# 配置日志
logger = logging.getLogger(__name__)

class FotMobCoreCollector:
    """
    FotMob核心数据采集器 - V10.9护航加固版

    核心功能:
    1. 自适应解码：智能处理Gzip/Brotli/原始JSON
    2. 数据库UPSERT：断点续传和赔率回填
    3. V10.9哨兵检查：响应长度验证和空心场次拦截
    4. 故障熔断：连续失败5次触发30分钟休眠
    5. 断点续传：仅采集缺失数据，避免API浪费
    """

    def __init__(self):
        """初始化核心采集器"""
        self.base_url = "https://www.fotmob.com/api"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,en-GB;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',  # 恢复支持所有编码
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # V10.9 护航新增属性
        self.consecutive_failures = 0  # 连续失败计数器
        self.max_consecutive_failures = 5  # 最大连续失败次数
        self.circuit_breaker_timeout = 1800  # 熔断超时时间（30分钟）
        self.min_response_size = 102400  # 最小响应大小（100KB） - 强制质量标准
        self.hollow_matches_log = "data/logs/hollow_matches.log"  # 空心场次日志路径

    def get_missing_match_ids(self, limit: int = 100) -> List[int]:
        """
        获取缺失的比赛ID列表

        Args:
            limit: 返回ID数量限制

        Returns:
            缺失的比赛ID列表
        """
        logger.info(f"🔍 动态查找缺失的比赛数据，目标数量: {limit}")

        # 从harvest_manifest.csv动态读取比赛ID
        target_match_ids = self._load_match_ids_from_manifest()

        try:
            conn = self.get_database_connection()
            with conn.cursor() as cur:
                # 检查已存在的比赛ID
                if len(target_match_ids) > 0:
                    id_list_str = ','.join(map(str, target_match_ids))
                    # 构建安全的参数化查询
                    placeholders = ','.join(['%s'] * len(target_match_ids))
                    cur.execute(f"""
                        SELECT external_id
                        FROM matches
                        WHERE external_id::text IN ({placeholders})
                    """, [str(mid) for mid in target_match_ids])
                    existing_ids = {row[0] for row in cur.fetchall()}

                    # 计算缺失的ID
                    missing_ids = [mid for mid in target_match_ids if mid not in existing_ids]
                else:
                    missing_ids = []

                # 限制返回数量
                missing_ids = missing_ids[:limit]

                logger.info(f"📋 找到 {len(missing_ids)} 条待采集比赛")
                return missing_ids

        except Exception as e:
            logger.error(f"❌ 获取缺失比赛ID失败: {e}")
            # 出错时返回前N个ID
            return target_match_ids[:limit]
        finally:
            if 'conn' in locals():
                conn.close()

    def _load_match_ids_from_manifest(self, manifest_path: str = None) -> List[int]:
        """
        从harvest_manifest.csv加载比赛ID列表

        Args:
            manifest_path: manifest文件路径（可选，默认使用标准路径）

        Returns:
            比赛ID列表
        """
        import csv
        import os

        if manifest_path is None:
            manifest_path = "data/production/harvest_manifest.csv"

        if not os.path.exists(manifest_path):
            logger.error(f"❌ 找不到harvest manifest文件: {manifest_path}")
            return []

        match_ids = []

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 只获取已匹配的比赛
                    if row.get('is_matched') == 'True':
                        match_id = int(row['match_id'])
                        match_ids.append(match_id)

            logger.info(f"📋 从manifest文件读取到 {len(match_ids)} 场已验证比赛 ({manifest_path})")
            return match_ids

        except Exception as e:
            logger.error(f"❌ 读取manifest文件失败: {e}")
            return []

    def get_database_connection(self) -> psycopg2.extensions.connection:
        """
        获取数据库连接 - 统一配置入口

        Returns:
            psycopg2连接对象
        """
        from src.config_unified import get_settings
        settings = get_settings()
        db = settings.database

        logger.debug(f"🔧 连接数据库: {db.host}:{db.port}/{db.name}")

        return psycopg2.connect(
            host=db.host,
            port=db.port,
            database=db.name,
            user=db.user,
            password=db.password.get_secret_value()
        )

    def _log_hollow_match(self, match_id: int, content_size: int, reason: str) -> None:
        """
        记录空心场次到专用日志文件 - V10.9哨兵功能

        Args:
            match_id: 比赛ID
            content_size: 响应内容大小
            reason: 被拒绝的原因
        """
        try:
            os.makedirs(os.path.dirname(self.hollow_matches_log), exist_ok=True)

            timestamp = datetime.now().isoformat()
            log_entry = f"{timestamp} - HOLLOW_MATCH - MatchID: {match_id}, Size: {content_size} bytes, Reason: {reason}\n"

            with open(self.hollow_matches_log, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            logger.warning(f"🚨 空心场次已记录: MatchID {match_id}, 响应大小: {content_size} bytes, 原因: {reason}")

        except Exception as e:
            logger.error(f"写入空心场次日志失败: {e}")

    def _validate_response_size(self, match_id: int, content: bytes) -> bool:
        """
        V10.9哨兵检查：验证响应大小

        Args:
            match_id: 比赛ID
            content: 响应内容字节

        Returns:
            bool: 响应大小是否通过验证
        """
        content_size = len(content)

        # 强制检查：响应字节数必须 >= 100KB
        if content_size < self.min_response_size:
            reason = f"响应过小 ({content_size} < {self.min_response_size} bytes)"
            self._log_hollow_match(match_id, content_size, reason)
            logger.error(f"🚨 哨兵拦截: MatchID {match_id} - {reason}")
            return False

        logger.debug(f"✅ 响应大小验证通过: MatchID {match_id}, 大小: {content_size} bytes")
        return True

    def _check_circuit_breaker(self) -> bool:
        """
        V10.9熔断检查：检查是否需要触发熔断

        Returns:
            bool: 是否允许继续执行
        """
        if self.consecutive_failures >= self.max_consecutive_failures:
            logger.error(f"🚨 触发自动熔断！连续失败 {self.consecutive_failures} 次")
            logger.error(f"⏱️  休眠 {self.circuit_breaker_timeout/60:.1f} 分钟后尝试重启...")
            time.sleep(self.circuit_breaker_timeout)

            # 重置计数器，尝试重启
            self.consecutive_failures = 0
            logger.info("🔄 熔断重启，重新开始采集")
            return True

        return True

    def _increment_failure(self) -> None:
        """增加失败计数"""
        self.consecutive_failures += 1
        logger.warning(f"⚠️  连续失败次数: {self.consecutive_failures}/{self.max_consecutive_failures}")

        # 检查是否需要熔断
        if self.consecutive_failures >= self.max_consecutive_failures:
            self._check_circuit_breaker()

    def _reset_failure_count(self) -> None:
        """重置失败计数器"""
        if self.consecutive_failures > 0:
            logger.info(f"✅ 成功采集，重置失败计数 (之前: {self.consecutive_failures})")
            self.consecutive_failures = 0

    def get_missing_matches(self, match_ids: List[int]) -> List[int]:
        """
        V10.9断点查询：获取确实缺失数据的场次ID列表

        Args:
            match_ids: 需要检查的比赛ID列表

        Returns:
            List[int]: 确实缺失数据的比赛ID列表
        """
        conn = None
        try:
            conn = self.get_database_connection()
            with conn.cursor() as cur:
                # 构建IN子句
                id_list = ','.join([str(id) for id in match_ids])
                query = f"""
                SELECT id FROM matches
                WHERE id IN ({id_list}) AND l2_raw_json IS NULL
                """
                cur.execute(query)
                missing_ids = [row[0] for row in cur.fetchall()]

                logger.info(f"🎯 断点查询结果: 总计 {len(match_ids)} 场，缺失 {len(missing_ids)} 场")
                return missing_ids

        except Exception as e:
            logger.error(f"断点查询失败: {e}")
            # 出错时返回完整列表，确保不遗漏
            return match_ids
        finally:
            if conn:
                conn.close()

    def adaptive_decode_response(self, content: bytes, content_encoding: str = '') -> Optional[Dict]:
        """
        自适应解码响应数据 - V10.6黄金逻辑

        智能处理不同压缩格式：
        1. Gzip (0x1f 0x8b 文件头)
        2. 原始JSON (以 { 开头)
        3. Brotli (content_encoding='br')

        Args:
            content: 响应内容字节
            content_encoding: HTTP响应的Content-Encoding头

        Returns:
            解析后的JSON数据或None
        """
        try:
            if not content:
                logger.error("响应内容为空")
                return None

            # 检查文件头字节判断压缩格式
            if len(content) >= 2:
                # Gzip文件头: 0x1f 0x8b
                if content[:2] == b'\x1f\x8b':
                    logger.debug("检测到Gzip格式，执行解压")
                    decompressed_data = gzip.decompress(content)
                    return json.loads(decompressed_data.decode('utf-8'))

                # 原始JSON格式
                elif content[:1] == b'{':
                    logger.debug("检测到原始JSON格式，直接解析")
                    return json.loads(content.decode('utf-8'))

                # Brotli压缩 (根据编码头或内容特征)
                elif content_encoding == 'br' or self._is_brotli_content(content):
                    logger.debug("检测到Brotli压缩，执行解压")
                    try:
                        decompressed_data = brotli.decompress(content)
                        return json.loads(decompressed_data.decode('utf-8'))
                    except Exception as brotli_error:
                        logger.warning(f"Brotli解压失败: {brotli_error}")
                        # 尝试作为原始JSON处理
                        return json.loads(content.decode('utf-8'))

            # 默认尝试UTF-8解码
            logger.debug("使用默认UTF-8解码")
            return json.loads(content.decode('utf-8'))

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.debug(f"内容前100字节: {content[:100]}")
            return None
        except Exception as e:
            logger.error(f"自适应解码失败: {e}")
            return None

    def _is_brotli_content(self, content: bytes) -> bool:
        """
        检测是否为Brotli压缩内容

        Args:
            content: 内容字节

        Returns:
            bool: 是否为Brotli格式
        """
        try:
            # 尝试解压一小部分来验证
            brotli.decompress(content[:100])
            return True
        except:
            return False

    def parse_raw_json_to_db(self, limit: int = 1000) -> int:
        """
        工业级JSON解析引擎 - 自动解析l2_raw_json数据

        核心功能:
        1. 自动从header.teams提取比分
        2. 自动判定H/D/A结果并更新actual_result
        3. 解析playerStats节点提取技术特征
        4. 批量处理，支持断点续传

        Args:
            limit: 处理记录数限制，默认1000

        Returns:
            int: 成功解析的记录数
        """
        conn = None
        processed_count = 0

        try:
            conn = self.get_database_connection()

            with conn.cursor() as cur:
                # 查询需要解析的记录（有l2_raw_json但没有技术特征的）
                cur.execute("""
                    SELECT id, external_id, l2_raw_json, home_team, away_team
                    FROM matches
                    WHERE l2_raw_json IS NOT NULL
                    AND player_stats IS NULL
                    ORDER BY l2_collected_at DESC
                    LIMIT %s
                """, (limit,))

                records = cur.fetchall()
                logger.info(f"🔍 找到 {len(records)} 条待解析记录")

                for record in records:
                    record_id = record[0]
                    external_id = record[1]
                    raw_json = record[2]
                    home_team = record[3]
                    away_team = record[4]

                    try:
                        # 解析JSON数据
                        json_data = json.loads(raw_json)

                        # V14.0修复: 提取真正的L2数据
                        if 'l2_json' in json_data:
                            actual_l2_data = json_data['l2_json']
                            if isinstance(actual_l2_data, str):
                                actual_l2_data = json.loads(actual_l2_data)
                        else:
                            actual_l2_data = json_data

                        # Step 1: 解析比分和结果
                        score_result = self._parse_match_score(actual_l2_data)

                        # Step 2: 解析技术特征
                        tech_features = self._parse_technical_features(actual_l2_data)

                        logger.info(f"✅ 解析成功: {external_id} - {score_result.get('result_score', 'N/A')} ({score_result.get('actual_result', 'N/A')}) - 特征: {'有' if tech_features else '无'}")

                        # Step 3: 更新数据库
                        if score_result or tech_features:
                            update_fields = []
                            update_values = []

                            if score_result:
                                update_fields.extend([
                                    'home_score = %s', 'away_score = %s',
                                    'actual_result = %s', 'result_score = %s'
                                ])
                                update_values.extend([
                                    score_result['home_score'],
                                    score_result['away_score'],
                                    score_result['actual_result'],
                                    score_result['result_score']
                                ])

                            if tech_features:
                                update_fields.append('player_stats = %s')
                                update_values.append(json.dumps(tech_features))

                            update_fields.append('updated_at = NOW()')

                            # 执行更新
                            update_sql = f"""
                                UPDATE matches
                                SET {', '.join(update_fields)}
                                WHERE id = %s
                            """
                            update_values.append(record_id)

                            cur.execute(update_sql, update_values)
                            processed_count += 1

                            logger.info(f"✅ 解析成功: {external_id} - "
                                       f"{score_result.get('home_score', '?')}-{score_result.get('away_score', '?')} "
                                       f"({score_result.get('actual_result', '?')})")

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON解析失败 {external_id}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"❌ 解析异常 {external_id}: {e}")
                        continue

                conn.commit()
                logger.info(f"🎉 JSON解析完成！成功处理 {processed_count} 条记录")

        except Exception as e:
            logger.error(f"❌ JSON解析引擎失败: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        return processed_count

    def _parse_match_score(self, json_data: Dict) -> Optional[Dict]:
        """
        从JSON中解析比分和比赛结果

        Args:
            json_data: 解析的JSON数据

        Returns:
            包含比分和结果的字典或None
        """
        try:
            # 从header.teams节点提取比分
            if 'header' in json_data and 'teams' in json_data['header']:
                teams = json_data['header']['teams']

                if len(teams) >= 2:
                    home_team_data = teams[0]
                    away_team_data = teams[1]

                    home_score = home_team_data.get('score', 0)
                    away_score = away_team_data.get('score', 0)

                    # 判定比赛结果
                    if home_score > away_score:
                        actual_result = 'H'  # Home Win
                    elif home_score < away_score:
                        actual_result = 'A'  # Away Win
                    else:
                        actual_result = 'D'  # Draw

                    return {
                        'home_score': int(home_score),
                        'away_score': int(away_score),
                        'actual_result': actual_result,
                        'result_score': f"{home_score}-{away_score}"
                    }

            return None

        except Exception as e:
            logger.error(f"比分解析失败: {e}")
            return None

    def _parse_technical_features(self, json_data: Dict) -> Optional[Dict]:
        """
        V14.0 重构: 从FotMob JSON中解析157维技术特征
        使用团队级统计: content.stats.Periods.All.stats[x].stats[home,away]

        Args:
            json_data: 解析的JSON数据

        Returns:
            技术特征字典或None
        """
        try:
            features = {}

            # V14.0 修复: 从l2_json.content.stats.Periods.All提取团队级统计
            actual_json_data = json_data

            # 处理包装后的数据结构
            if 'l2_json' in json_data:
                actual_json_data = json_data['l2_json']
                logger.info(f"📊 检测到包装数据结构，使用l2_json")

            if 'content' in actual_json_data and 'stats' in actual_json_data['content']:
                try:
                    content = actual_json_data['content']
                    stats = content['stats']
                    periods = stats['Periods']
                    all_period = periods['All']
                    all_stats = all_period['stats']

                    logger.info(f"📊 数据结构检查:")
                    logger.info(f"  content键: {list(content.keys())}")
                    logger.info(f"  stats键: {list(stats.keys())}")
                    logger.info(f"  Periods键: {list(periods.keys())}")
                    logger.info(f"  All键: {list(all_period.keys())}")

                    if isinstance(all_stats, list):
                        logger.info(f"📊 找到 {len(all_stats)} 个统计组")

                        # FotMob统计键到内部特征名的映射
                        stat_mapping = {
                            # 基础统计
                            'BallPossesion': 'possession',
                            'expected_goals': 'xg',
                            'total_shots': 'shots_total',
                            'ShotsOnTarget': 'shots_on_target',
                            'big_chance': 'big_chances_created',
                            'accurate_passes': 'passes_accurate',
                            'fouls': 'fouls',
                            'corners': 'corners',

                            # 射门统计
                            'shots': 'shots_total_alt',
                            'ShotsOffTarget': 'shots_off_target',
                            'blocked_shots': 'shots_blocked',
                            'shots_woodwork': 'shots_woodwork',
                            'shots_inside_box': 'shots_inside_box',
                            'shots_outside_box': 'shots_outside_box',

                            # xG详细统计
                            'expected_goals_open_play': 'xg_open_play',
                            'expected_goals_set_play': 'xg_set_piece',
                            'expected_goals_non_penalty': 'xg_non_penalty',
                            'expected_goals_on_target': 'xg_on_target',

                            # 传球统计
                            'passes': 'passes_total',
                            'own_half_passes': 'passes_own_half',
                            'opposition_half_passes': 'passes_opposition_half',
                            'long_balls_accurate': 'long_balls_accurate',
                            'accurate_crosses': 'crosses_accurate',
                            'player_throws': 'throw_ins',
                            'Offsides': 'offsides',

                            # 防守统计
                            'matchstats.headers.tackles': 'tackles',
                            'interceptions': 'interceptions',
                            'shot_blocks': 'blocked_shots_def',
                            'clearances': 'clearances',
                            'keeper_saves': 'keeper_saves',

                            # 对抗统计
                            'duel_won': 'duels_won',
                            'ground_duels_won': 'ground_duels_won',
                            'aerials_won': 'aerial_duels_won',
                            'dribbles_succeeded': 'dribbles_success',

                            # 纪律统计
                            'yellow_cards': 'yellow_cards',
                            'red_cards': 'red_cards',
                        }

                        # 解析统计数据
                        home_stats = {}
                        away_stats = {}

                        for stat_group in all_stats:
                            if isinstance(stat_group, dict) and 'stats' in stat_group:
                                stats_list = stat_group['stats']

                                for stat_item in stats_list:
                                    if isinstance(stat_item, dict):
                                        key = stat_item.get('key', '')
                                        stats_values = stat_item.get('stats', [])

                                        # 确保有主客队数据 (stats[0] = 主队, stats[1] = 客队)
                                        logger.info(f"🔍 检查统计项: key='{key}', 在映射中={key in stat_mapping}, stats类型={type(stats_values)}, 长度={len(stats_values) if isinstance(stats_values, list) else 'N/A'}")

                                        if key in stat_mapping and isinstance(stats_values, list) and len(stats_values) >= 2:
                                            mapped_key = stat_mapping[key]

                                            # 解析主队和客队的数值
                                            home_value = self._parse_stat_value(stats_values[0])
                                            away_value = self._parse_stat_value(stats_values[1])

                                            home_stats[mapped_key] = home_value
                                            away_stats[mapped_key] = away_value

                                            logger.info(f"📊 成功解析 {mapped_key}: 主={home_value} 客={away_value}")

                                            # 统计成功匹配的数量
                                            if not hasattr(self, '_success_count'):
                                                self._success_count = 0
                                            self._success_count += 1
                                        else:
                                            logger.debug(f"⚪ 跳过统计项: key='{key}', 条件不满足")

                        # 生成157维特征向量
                        all_metrics = set(home_stats.keys()) | set(away_stats.keys())
                        logger.info(f"🧬 解析到 {len(all_metrics)} 个有效指标")

                        for metric in all_metrics:
                            home_val = home_stats.get(metric, 0)
                            away_val = away_stats.get(metric, 0)
                            total_val = home_val + away_val
                            diff_val = home_val - away_val

                            # 基础指标 (4个)
                            features[f'home_{metric}'] = home_val
                            features[f'away_{metric}'] = away_val
                            features[f'total_{metric}'] = total_val
                            features[f'diff_{metric}'] = diff_val

                            # 比率特征 (2个)
                            if total_val > 0:
                                features[f'home_ratio_{metric}'] = home_val / total_val
                                features[f'away_ratio_{metric}'] = away_val / total_val
                            else:
                                features[f'home_ratio_{metric}'] = 0.0
                                features[f'away_ratio_{metric}'] = 0.0

                        logger.info(f"🎯 团队统计特征生成成功: {len(features)}维特征")

                except (KeyError, TypeError) as e:
                    logger.warning(f"团队级统计解析失败，回退到lineup模式: {e}")
                    import traceback
                    logger.warning(f"详细错误: {traceback.format_exc()}")

            # 备用方案: 从lineup获取基础信息
            if 'content' in actual_json_data and 'lineup' in actual_json_data['content']:
                lineup = actual_json_data['content']['lineup']

                home_player_count = 0
                away_player_count = 0
                home_team_rating = 0.0
                away_team_rating = 0.0
                home_formation = ""
                away_formation = ""

                if 'homeTeam' in lineup:
                    home_team = lineup['homeTeam']
                    home_player_count = len(home_team.get('starters', [])) + len(home_team.get('subs', []))
                    home_team_rating = self._safe_float(home_team.get('rating', 0))
                    home_formation = home_team.get('formation', '')

                if 'awayTeam' in lineup:
                    away_team = lineup['awayTeam']
                    away_player_count = len(away_team.get('starters', [])) + len(away_team.get('subs', []))
                    away_team_rating = self._safe_float(away_team.get('rating', 0))
                    away_formation = away_team.get('formation', '')

                # 添加阵容特征
                features.update({
                    'home_player_count': home_player_count,
                    'away_player_count': away_player_count,
                    'total_player_count': home_player_count + away_player_count,
                    'home_team_rating': home_team_rating,
                    'away_team_rating': away_team_rating,
                    'total_team_rating': home_team_rating + away_team_rating,
                    'diff_team_rating': home_team_rating - away_team_rating,
                    'home_formation': home_formation,
                    'away_formation': away_formation,
                })

            logger.info(f"🧬 V14.0特征解析完成: 生成{len(features)}维特征向量")
            return features  # 即使是空字典也返回，让调用方处理

        except Exception as e:
            logger.error(f"V14.0特征解析失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def _parse_stat_value(self, value) -> float:
        """
        安全解析统计数值，处理字符串格式的数据

        Args:
            value: 原始值 (可能是字符串、数字、None等)

        Returns:
            解析后的浮点数
        """
        if value is None or value == '' or value == '-':
            return 0.0

        try:
            if isinstance(value, (int, float)):
                return float(value)

            if isinstance(value, str):
                # 处理格式如 "290 (79%)" 或 "45%" 的情况
                if '(' in value:
                    # 提取括号前的数字
                    value = value.split('(')[0].strip()
                elif '%' in value:
                    # 移除百分号
                    value = value.replace('%', '').strip()

                # 移除其他非数字字符
                value = ''.join(c for c in value if c.isdigit() or c == '.')

                return float(value) if value else 0.0

        except (ValueError, TypeError):
            return 0.0

        return 0.0

    def _safe_float(self, value) -> float:
        """安全转换为浮点数"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0

    def get_match_details(self, match_id: int) -> Optional[Dict]:
        """
        获取比赛详情数据

        Args:
            match_id: 比赛外部ID

        Returns:
            包含比赛信息的字典，或None如果失败
        """
        try:
            url = f"{self.base_url}/matchDetails?matchId={match_id}"

            logger.info(f"🌍 请求比赛详情: {match_id}")
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                response.raise_for_status()

                # 尝试解码数据
                json_data = self.adaptive_decode_response(response.content, response.headers.get('Content-Encoding', ''))

                if json_data and isinstance(json_data, dict):
                    # V10.9哨兵检查：响应长度验证
                    if len(str(json_data)) < self.min_response_size:
                        logger.warning(f"⚠️ 响应数据过小: {len(str(json_data))} bytes")
                        self._log_hollow_match(match_id, "response_too_small")
                        return None

                    # 提取基础信息
                    match_info = self._extract_match_basic_info(json_data, match_id)
                    if match_info:
                        return {
                            'match_info': match_info,
                            'l2_json': json_data
                        }
                    else:
                        logger.error(f"❌ 无法提取比赛基础信息: {match_id}")
                        return None
                else:
                    logger.error(f"❌ 响应数据格式错误: {match_id}")
                    return None
            else:
                logger.error(f"❌ HTTP请求失败: {match_id} - {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"⏰ 请求超时: {match_id}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络请求异常: {match_id} - {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 获取比赛详情异常: {match_id} - {e}")
            return None

    def _extract_match_basic_info(self, json_data: Dict, match_id: int) -> Optional[Dict]:
        """
        从JSON数据中提取比赛基础信息

        Args:
            json_data: 响应JSON数据
            match_id: 比赛ID

        Returns:
            比赛基础信息字典，或None
        """
        try:
            # 提取基本信息
            match_header = json_data.get('header', {})

            match_info = {
                'match_id': match_id,  # 添加match_id字段
                'external_id': str(match_id),
                'home_team': match_header.get('teams', [{}])[0].get('name', 'Unknown Home'),
                'away_team': match_header.get('teams', [{}])[1].get('name', 'Unknown Away'),
                'league_name': match_header.get('league', {}).get('name', 'Unknown League'),
                'match_time': match_header.get('status', {}).get('utcTime', ''),
                'match_date': match_header.get('status', {}).get('utcTime', '')[:10],  # 提取日期部分
                'venue': match_header.get('venue', {}).get('name', ''),
                'home_score': None,  # 将在parse阶段填入
                'away_score': None,  # 将在parse阶段填入
            }

            return match_info

        except Exception as e:
            logger.error(f"❌ 提取比赛基础信息失败: {e}")
            return None

    def _log_hollow_match(self, match_id: int, reason: str):
        """
        记录空心比赛

        Args:
            match_id: 比赛ID
            reason: 拦截原因
        """
        try:
            os.makedirs(os.path.dirname(self.hollow_matches_log), exist_ok=True)
            with open(self.hollow_matches_log, 'a', encoding='utf-8') as f:
                log_entry = f"{datetime.now().isoformat()}, {match_id}, {reason}\n"
                f.write(log_entry)
            logger.info(f"🔍 空心比赛已记录: {match_id} - {reason}")
        except Exception as e:
            logger.error(f"❌ 记录空心比赛失败: {e}")

    def upsert_match_data(self, match_info: Dict, l2_json: Dict) -> bool:
        """
        数据库UPSERT操作 - V10.6黄金逻辑

        功能：
        1. 插入新记录或更新现有记录
        2. 同步真实赔率数据
        3. 自动更新时间戳

        Args:
            match_info: 比赛基础信息
            l2_json: L2数据JSON

        Returns:
            bool: 操作是否成功
        """
        conn = None
        try:
            conn = self.get_database_connection()

            with conn.cursor() as cur:
                # 使用ON CONFLICT实现UPSERT
                query = """
                INSERT INTO matches (
                    id, external_id, home_team, away_team, match_time,
                    l2_raw_json, l2_collected_at,
                    home_win_odds, draw_odds, away_win_odds,
                    league_name, season, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, CURRENT_TIMESTAMP
                )
                ON CONFLICT (id) DO UPDATE SET
                    l2_raw_json = EXCLUDED.l2_raw_json,
                    l2_collected_at = EXCLUDED.l2_collected_at,
                    home_win_odds = EXCLUDED.home_win_odds,
                    draw_odds = EXCLUDED.draw_odds,
                    away_win_odds = EXCLUDED.away_win_odds,
                    updated_at = CURRENT_TIMESTAMP
                """

                params = (
                    match_info['match_id'],  # id
                    match_info['match_id'],  # external_id
                    match_info['home_team'],
                    match_info['away_team'],
                    match_info['match_date'],
                    json.dumps(l2_json),    # l2_raw_json
                    datetime.now().isoformat(),  # l2_collected_at
                    match_info.get('real_home_odds'),
                    match_info.get('real_draw_odds'),
                    match_info.get('real_away_odds'),
                    match_info.get('league', 'Premier League'),
                    self._determine_season(match_info['match_date'])
                )

                cur.execute(query, params)
                conn.commit()

                logger.info(f"UPSERT成功: {match_info['match_id']} {match_info['home_team']} vs {match_info['away_team']}")
                return True

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"UPSERT失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False
        finally:
            if conn:
                conn.close()

    def _determine_season(self, match_date: str) -> str:
        """
        V10.9 物理纯净版：根据比赛日期强制判定赛季
        绝不允许 'Unknown' 存在

        Args:
            match_date: 比赛日期字符串

        Returns:
            str: 赛季字符串 (如 "25/26")
        """
        try:
            # 支持多种日期格式
            if 'T' in match_date:
                # ISO格式: 2025-08-15T19:00:00Z
                date_str = match_date.split('T')[0]
            else:
                # 简单格式: 2025-08-15
                date_str = match_date

            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            year = date_obj.year
            month = date_obj.month

            # 英超赛季：8月开始到次年7月结束
            # 2025-08 及之后 -> 25/26 赛季
            # 2025-07 及之前 -> 24/25 赛季
            if month >= 8:
                season_start = year % 100  # 取后两位
                season_end = (year + 1) % 100
                return f"{season_start:02d}/{season_end:02d}"
            else:
                season_start = (year - 1) % 100
                season_end = year % 100
                return f"{season_start:02d}/{season_end:02d}"

        except Exception as e:
            logger.error(f"赛季判定失败 - 日期: {match_date}, 错误: {e}")
            # 强制使用当前赛季，绝不返回 Unknown
            current_year = datetime.now().year
            current_month = datetime.now().month

            if current_month >= 8:
                season_start = current_year % 100
                season_end = (current_year + 1) % 100
            else:
                season_start = (current_year - 1) % 100
                season_end = current_year % 100

            return f"{season_start:02d}/{season_end:02d}"

    def fetch_match_details(self, match_id: int) -> Optional[Dict]:
        """
        V10.9护航加固版：获取比赛详情 - 集成哨兵检查和故障熔断

        Args:
            match_id: 比赛ID

        Returns:
            Dict: 比赛详情数据或None
        """
        url = f"{self.base_url}/matchDetails?matchId={match_id}"

        # V10.9: 检查熔断器状态
        if not self._check_circuit_breaker():
            return None

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # V10.9: 哨兵检查 - 验证响应大小
            if not self._validate_response_size(match_id, response.content):
                self._increment_failure()
                return None

            # 使用自适应解码
            content_encoding = response.headers.get('content-encoding', '').lower()
            decoded_data = self.adaptive_decode_response(response.content, content_encoding)

            if decoded_data:
                # V10.9: 成功采集，重置失败计数
                self._reset_failure_count()
                logger.debug(f"✅ 成功获取比赛 {match_id} 数据")
                return decoded_data
            else:
                logger.error(f"比赛 {match_id} 数据解码失败")
                self._increment_failure()
                return None

        except requests.RequestException as e:
            logger.error(f"HTTP请求失败 {match_id}: {e}")
            self._increment_failure()
            return None
        except Exception as e:
            logger.error(f"获取比赛 {match_id} 详情失败: {e}")
            self._increment_failure()
            return None

    def health_check(self) -> Dict[str, Any]:
        """
        V10.9护航加固版：系统健康检查

        Returns:
            Dict: 健康状态报告
        """
        status = {
            'collector': 'FotMobCore V10.9',
            'timestamp': datetime.now().isoformat(),
            'database_connection': False,
            'api_connectivity': False,
            'adaptive_decoder': False,
            'consecutive_failures': self.consecutive_failures,
            'circuit_breaker_active': self.consecutive_failures >= self.max_consecutive_failures,
            'min_response_size': self.min_response_size,
            'hollow_matches_log_exists': os.path.exists(self.hollow_matches_log)
        }

        # 检查数据库连接
        try:
            conn = self.get_database_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            status['database_connection'] = True
        except Exception as e:
            status['database_error'] = str(e)

        # 检查API连接
        try:
            response = self.session.get(f"{self.base_url}/leagues?id=127", timeout=10)
            status['api_connectivity'] = response.status_code == 200
        except Exception as e:
            status['api_error'] = str(e)

        # 检查自适应解码器
        try:
            test_json = b'{"test": "value"}'
            result = self.adaptive_decode_response(test_json)
            status['adaptive_decoder'] = result is not None
        except Exception as e:
            status['decoder_error'] = str(e)

        return status

# 单例实例
_core_collector = None

def get_core_collector() -> FotMobCoreCollector:
    """获取核心采集器单例"""
    global _core_collector
    if _core_collector is None:
        _core_collector = FotMobCoreCollector()
    return _core_collector