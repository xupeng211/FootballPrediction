#!/usr/bin/env python3
"""
V38.0 EventBus - PostgreSQL NOTIFY/LISTEN 监听服务 (Event-Driven Architecture)

功能:
    - 监听 'matches_insert' 频道 → 触发 Layer B 哈希狩猎
    - 监听 'odds_updated' 频道 → 触发 Layer D 特征提取
    - V37.2: 启动自检 - 补偿遗漏的 NOTIFY 事件
    - V37.2: Layer C 自动触发 - URL 找到后自动采集赔率
    - V37.3: 进程安全阀 - 限制并发进程数防止进程风暴
    - V37.4: Layer D 事件驱动 - 废除轮询，使用 NOTIFY 驱动
    - V38.0: 哨兵自愈 - 后台周期任务扫描孤儿数据并重新推送 NOTIFY

架构:
    [启动自检] → NOTIFY: matches_insert → hunt_hashes → harvest_odds
                                     ↓
                             NOTIFY: odds_updated → extract_features
                                     ↓
                             [哨兵自愈] → 周期扫描孤儿数据 → 补偿 NOTIFY

使用方法:
    # 方式 1: 独立运行
    python -m src.services.event_bus

    # 方式 2: 作为服务导入
    from src.services.event_bus import EventBus
    bus = EventBus()
    bus.listen()

Author: 首席系统架构师 & 性能专家
Version: V38.0 Sentry Self-Healing
Date: 2026-01-12
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# EventBus - 极简监听服务
# ============================================================================

class EventBus:
    """
    V38.0 EventBus - PostgreSQL NOTIFY/LISTEN 监听服务 (Event-Driven Architecture)

    职责:
        1. 监听 'matches_insert' 频道 → 触发 Layer B 哈希狩猎
        2. 监听 'odds_updated' 频道 → 触发 Layer D 特征提取
        3. V37.2: 启动自检 - 补偿遗漏的 NOTIFY 事件
        4. V37.2: Layer C 自动触发 - URL 找到后自动采集赔率
        5. V37.3: 进程安全阀 - 限制并发进程数防止进程风暴
        6. V37.4: Layer D 事件驱动 - 废除轮询，使用 NOTIFY 驱动
        7. V38.0: 哨兵自愈 - 后台周期任务扫描孤儿数据并重新推送 NOTIFY
    """

    def __init__(self, poll_interval: float = 1.0, enable_self_check: bool = True,
                 enable_layer_c_trigger: bool = True, enable_layer_d_trigger: bool = True,
                 self_check_days: int = 7, max_concurrent_processes: int = 8,
                 enable_sentry: bool = True, sentry_interval_minutes: int = 30):
        """
        初始化 EventBus

        Args:
            poll_interval: 轮询间隔（秒）
            enable_self_check: 是否启用启动自检
            enable_layer_c_trigger: 是否启用 Layer C 自动触发
            enable_layer_d_trigger: 是否启用 Layer D 自动触发
            self_check_days: 启动自检扫描最近几天的数据
            max_concurrent_processes: 最大并发进程数（安全阀）
            enable_sentry: 是否启用哨兵自愈（V38.0）
            sentry_interval_minutes: 哨兵扫描间隔（分钟，默认 30）
        """
        self.poll_interval = poll_interval
        self.enable_self_check = enable_self_check
        self.enable_layer_c_trigger = enable_layer_c_trigger
        self.enable_layer_d_trigger = enable_layer_d_trigger
        self.self_check_days = self_check_days
        self.max_concurrent_processes = max_concurrent_processes
        self.settings = get_settings()
        self.conn: Optional[psycopg2.extensions.connection] = None
        self.cursor: Optional[psycopg2.extensions.cursor] = None
        self._running = False

        # V38.0: 哨兵自愈配置
        self.enable_sentry = enable_sentry
        self.sentry_interval_seconds = sentry_interval_minutes * 60
        self._sentry_thread: Optional[threading.Thread] = None
        self._last_sentry_run: Optional[datetime] = None

        # V37.3: 进程安全阀 - 使用 deque 跟踪活跃进程
        self.active_processes: deque = deque()
        self.active_processes_lock = threading.Lock()

        # V37.4: 移除 pending_layer_d 轮询队列（改用事件驱动）
        # 保留 timing_stats 用于"生产线全景视图"
        self.timing_stats: Dict[str, List[float]] = {
            'a_to_b': [],  # Layer A → B 耗时
            'b_to_c': [],  # Layer B → C 耗时
            'c_to_d': [],  # Layer C → D 耗时
        }
        self.timing_lock = threading.Lock()

        # 统计
        self.stats = {
            'started_at': None,
            'notifications_received': 0,
            'hash_hunts_triggered': 0,
            'self_check_orphans_found': 0,
            'self_check_processed': 0,
            'layer_c_triggered': 0,
            'layer_d_triggered': 0,
            'processes_throttled': 0,
            'errors': 0,
            # V37.4: 事件类型统计
            'matches_insert_count': 0,
            'odds_updated_count': 0,
            # V38.0: 哨兵自愈统计
            'sentry_runs': 0,
            'sentry_orphans_found': 0,
            'sentry_notifies_sent': 0,
        }

    def _get_active_process_count(self) -> int:
        """获取当前活跃进程数（清理已完成的进程）"""
        with self.active_processes_lock:
            # 清理已完成的进程
            while self.active_processes:
                pid, start_time = self.active_processes[0]
                try:
                    # 检查进程是否还在运行
                    if os.path.exists(f"/proc/{pid}"):
                        # 进程还在运行，检查是否超时（10分钟）
                        if time.time() - start_time < 600:
                            break
                        else:
                            # 进程超时，从队列中移除
                            self.active_processes.popleft()
                            logger.warning(f"⚠️  进程 {pid} 超时，从活跃队列中移除")
                    else:
                        # 进程已完成，从队列中移除
                        self.active_processes.popleft()
                except (IndexError, OSError):
                    self.active_processes.popleft()

            return len(self.active_processes)

    def _can_spawn_process(self) -> bool:
        """检查是否可以创建新进程（安全阀）"""
        active_count = self._get_active_process_count()
        if active_count >= self.max_concurrent_processes:
            self.stats['processes_throttled'] += 1
            logger.warning(
                f"⚠️  进程安全阀触发: 当前活跃进程 {active_count}/{self.max_concurrent_processes}，"
                f"新进程被限流"
            )
            return False
        return True

    def _register_process(self, pid: int):
        """注册新进程到活跃队列"""
        with self.active_processes_lock:
            self.active_processes.append((pid, time.time()))
            logger.info(f"📊 进程注册: PID {pid}，当前活跃进程: {len(self.active_processes)}")

    def connect(self):
        """连接数据库、启动自检并注册监听"""
        self.conn = psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value()
        )
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()

        # V37.2: 启动自检 - 补偿遗漏的 NOTIFY 事件
        if self.enable_self_check:
            self._startup_self_check()

        # 注册监听 'matches_insert' 频道（Layer B 触发）
        self.cursor.execute("LISTEN matches_insert")

        # V37.4: 注册监听 'odds_updated' 频道（Layer D 触发）
        if self.enable_layer_d_trigger:
            self.cursor.execute("LISTEN odds_updated")

        logger.info("✅ EventBus 已启动，监听频道: matches_insert, odds_updated")

    def _startup_self_check(self):
        """
        V37.2: 启动自检 - 扫描遗漏的比赛并补单

        扫描逻辑:
        - 查找 matches 表中 match_date 在最近 N 天内的记录
        - 排除已存在于 matches_mapping 表的记录
        - 对遗漏的记录执行哈希狩猎
        """
        logger.info("=" * 70)
        logger.info("🔍 V37.2 启动自检开始")
        logger.info("=" * 70)

        try:
            # 查询遗漏的比赛（最近 N 天，且不在 matches_mapping 中）
            self.cursor.execute("""
                SELECT m.match_id, m.league_name, m.home_team, m.away_team, m.match_date
                FROM matches m
                LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE mm.fotmob_id IS NULL
                  AND m.match_date >= NOW() - INTERVAL '%s days'
                  AND m.match_date <= NOW() + INTERVAL '30 days'
                ORDER BY m.match_date DESC
            """, (self.self_check_days,))

            orphaned_matches = self.cursor.fetchall()

            if not orphaned_matches:
                logger.info("✅ 启动自检完成: 未发现遗漏的比赛")
                return

            self.stats['self_check_orphans_found'] = len(orphaned_matches)
            logger.info(f"📊 发现 {len(orphaned_matches)} 场遗漏的比赛，开始补单...")

            processed = 0
            for match_id, league_name, home_team, away_team, match_date in orphaned_matches:
                try:
                    logger.info(f"   处理: {match_id} ({league_name})")
                    self._trigger_hash_hunt(match_id, league_name)
                    processed += 1

                    # 限制自检处理速度，避免过载
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"   ❌ 处理失败 {match_id}: {e}")
                    self.stats['errors'] += 1

            self.stats['self_check_processed'] = processed
            logger.info("=" * 70)
            logger.info(f"✅ 启动自检完成: 处理了 {processed}/{len(orphaned_matches)} 场比赛")
            logger.info("=" * 70)

        except Exception as e:
            logger.error(f"❌ 启动自检异常: {e}")
            self.stats['errors'] += 1

    def _trigger_layer_c_harvest(self, match_id: str, oddsportal_url: str):
        """
        V37.3: Layer C 自动触发 - 启动赔率采集（带进程安全阀）

        Args:
            match_id: 比赛 ID
            oddsportal_url: OddsPortal URL
        """
        if not self.enable_layer_c_trigger:
            logger.debug(f"Layer C 自动触发已禁用，跳过: {match_id}")
            return

        # V37.3: 进程安全阀检查
        if not self._can_spawn_process():
            logger.warning(f"⚠️  Layer C 触发被限流: {match_id}（活跃进程已满）")
            return

        try:
            logger.info(f"🚀 V37.3 Layer C 自动触发: {match_id} → {oddsportal_url}")

            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent
            harvest_script = project_root / "scripts" / "ops" / "harvest_pinnacle_concurrent.py"

            if not harvest_script.exists():
                logger.warning(f"⚠️  采集脚本不存在: {harvest_script}")
                return

            # 启动后台进程采集赔率
            cmd = [
                sys.executable,
                str(harvest_script),
                "--match-id", match_id,
                "--workers", "1",
                "--no-banner"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            # V37.3: 注册进程到活跃队列
            self._register_process(process.pid)

            self.stats['layer_c_triggered'] += 1
            logger.info(f"   ✅ Layer C 采集进程已启动: {match_id} (PID: {process.pid})")

        except Exception as e:
            logger.error(f"❌ Layer C 自动触发异常: {e}")
            self.stats['errors'] += 1

    def disconnect(self):
        """断开连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("🔌 EventBus 已断开连接")

    def _trigger_hash_hunt(self, match_id: str, league_name: str):
        """
        触发哈希狩猎（同步调用）

        Args:
            match_id: 比赛 ID
            league_name: 联赛名称
        """
        try:
            logger.info(f"🎯 触发哈希狩猎: match_id={match_id}, league={league_name}")

            # 动态导入 hunt_league_hashes 模块
            from scripts.ops.hunt_league_hashes import (
                get_missing_matches_by_league,
                insert_matches_mapping_batch
            )

            # 获取该比赛的详细信息
            matches = get_missing_matches_by_league([league_name])
            target_match = None
            for m in matches:
                if m['fotmob_id'] == match_id:
                    target_match = m
                    break

            if not target_match:
                logger.warning(f"⚠️  未找到目标比赛: {match_id}")
                return

            # 调用 OddsPortalScraper.search_match_url()
            import asyncio
            from core.scrapers.oddsportal import OddsPortalScraper

            scraper = OddsPortalScraper(config_path="config/scraper_config.yaml")

            # 在新的事件循环中运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    scraper.search_match_url(
                        home_team=target_match['home_team'],
                        away_team=target_match['away_team'],
                        league_hint=league_name,
                        headless=True
                    )
                )
            finally:
                loop.close()

            # 无论搜索成功与否，都记录到 matches_mapping 表
            if result.get('success') and result.get('url'):
                # 搜索成功
                record = {
                    'fotmob_id': match_id,
                    'home_team': target_match['home_team'],
                    'away_team': target_match['away_team'],
                    'league_name': league_name,
                    'match_date': target_match.get('match_date'),
                    'oddsportal_url': result['url'],
                    'confidence': 0.7,
                    'mapping_method': 'semantic'  # 使用允许的值
                }
                logger.info(f"✅ URL 映射成功: {match_id} → {result['url']}")

                # V37.2: Layer C 自动触发 - 当找到 URL 时立即启动采集
                self._trigger_layer_c_harvest(match_id, result['url'])
            else:
                # 搜索失败 - 仍然记录，但 URL 为 NULL
                record = {
                    'fotmob_id': match_id,
                    'home_team': target_match['home_team'],
                    'away_team': target_match['away_team'],
                    'league_name': league_name,
                    'match_date': target_match.get('match_date'),
                    'oddsportal_url': None,  # 搜索失败
                    'confidence': 0.0,
                    'mapping_method': 'semantic'  # 使用允许的值
                }
                logger.warning(f"⚠️  URL 搜索失败: {match_id} - {result.get('error', 'Unknown error')}")
                logger.info(f"   已记录到 matches_mapping 表 (URL=NULL)，证明自动化流程已触发")

            # 插入到 matches_mapping 表
            inserted = insert_matches_mapping_batch([record])
            self.stats['hash_hunts_triggered'] += 1

        except Exception as e:
            logger.error(f"❌ 哈希狩猎异常: {e}")
            self.stats['errors'] += 1

    def _process_notification(self, notification: psycopg2.extensions.Notify):
        """
        V37.4: 处理 NOTIFY 通知（支持多频道）

        Args:
            notification: psycopg2 Notify 对象
        """
        self.stats['notifications_received'] += 1

        try:
            # 解析 JSON 载荷
            payload = json.loads(notification.payload)
            match_id = payload.get('match_id')
            channel = notification.channel

            logger.info(
                f"📨 收到 NOTIFY 信号 (#{self.stats['notifications_received']}): "
                f"channel={channel}, match_id={match_id}"
            )

            # 根据频道类型分发处理
            if channel == 'matches_insert':
                # Layer B: 哈希狩猎
                self.stats['matches_insert_count'] += 1
                league_name = payload.get('league_name')
                if match_id and league_name:
                    self._trigger_hash_hunt(match_id, league_name)
                else:
                    logger.warning(f"⚠️  matches_insert 载荷格式错误: {notification.payload}")

            elif channel == 'odds_updated':
                # V37.4: Layer D: 特征提取（事件驱动）
                self.stats['odds_updated_count'] += 1
                has_odds = payload.get('has_odds')
                if match_id and has_odds:
                    self._trigger_layer_d_extraction(match_id)
                else:
                    logger.warning(f"⚠️  odds_updated 载荷格式错误: {notification.payload}")

            else:
                logger.warning(f"⚠️  未知频道: {channel}")

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 解析失败: {notification.payload} - {e}")
            self.stats['errors'] += 1
        except Exception as e:
            logger.error(f"❌ 处理通知异常: {e}")
            self.stats['errors'] += 1

    def _trigger_layer_d_extraction(self, match_id: str):
        """
        V37.4: Layer D 事件驱动触发 - 特征提取

        Args:
            match_id: 比赛 ID
        """
        if not self.enable_layer_d_trigger:
            logger.debug(f"Layer D 自动触发已禁用，跳过: {match_id}")
            return

        try:
            logger.info(f"🧪 V37.4 Layer D 事件驱动: {match_id} → l3_odds_data 已就绪")

            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent
            extract_script = project_root / "scripts" / "ml" / "extract_features_v1.py"

            if not extract_script.exists():
                logger.warning(f"⚠️  特征提取脚本不存在: {extract_script}")
                return

            # 触发特征提取
            cmd = [
                sys.executable,
                str(extract_script),
                "--match-id", match_id,
                "--limit", "1"
            ]

            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            self.stats['layer_d_triggered'] += 1
            logger.info(f"   ✅ Layer D 特征提取已触发: {match_id}")

        except Exception as e:
            logger.error(f"❌ Layer D 自动触发异常: {e}")
            self.stats['errors'] += 1

    def _sentry_scan_orphans(self):
        """
        V38.0: 哨兵自愈 - 扫描孤儿数据并重新推送 NOTIFY 信号

        孤儿数据定义:
        - matches.l3_odds_data IS NOT NULL (有赔率数据)
        - match_date < NOW() - INTERVAL '1 hour' (已过开赛时间 1 小时)
        - match_features.payout_ratio IS NULL OR 0 (无有效特征)

        自愈逻辑:
        1. 扫描符合条件的比赛
        2. 重新发送 NOTIFY odds_updated 信号
        3. 更新哨兵统计
        """
        try:
            # 使用独立数据库连接（避免阻塞主监听连接）
            sentry_conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value()
            )
            sentry_conn.autocommit = True
            sentry_cursor = sentry_conn.cursor()

            # 扫描孤儿数据
            sentry_cursor.execute("""
                SELECT m.match_id, m.league_name, m.match_date
                FROM matches m
                LEFT JOIN match_features mf ON m.match_id = mf.match_id
                WHERE m.l3_odds_data IS NOT NULL
                  AND m.match_date < NOW() - INTERVAL '1 hour'
                  AND (mf.payout_ratio IS NULL OR mf.payout_ratio = 0)
                ORDER BY m.match_date DESC
                LIMIT 100
            """)

            orphans = sentry_cursor.fetchall()
            self.stats['sentry_runs'] += 1
            self.stats['sentry_orphans_found'] += len(orphans)

            if orphans:
                logger.info(f"🛡️  哨兵扫描发现 {len(orphans)} 场孤儿数据")

                # 重新推送 NOTIFY 信号
                for match_id, league_name, match_date in orphans:
                    try:
                        payload = json.dumps({"match_id": match_id, "has_odds": True})
                        sentry_cursor.execute("NOTIFY odds_updated, %s", (payload,))
                        self.stats['sentry_notifies_sent'] += 1
                        logger.debug(f"   🔄 重推 NOTIFY: {match_id} ({league_name})")
                    except Exception as e:
                        logger.error(f"   ❌ 重推 NOTIFY 失败 {match_id}: {e}")

                logger.info(f"   ✅ 哨兵自愈: 已重推 {len(orphans)} 个 NOTIFY 信号")
            else:
                logger.debug("🛡️  哨兵扫描: 无孤儿数据")

            sentry_cursor.close()
            sentry_conn.close()
            self._last_sentry_run = datetime.now()

        except Exception as e:
            logger.error(f"❌ 哨兵扫描异常: {e}")
            self.stats['errors'] += 1

    def _sentry_worker(self):
        """
        V38.0: 哨兵后台工作线程
        """
        logger.info("🛡️  哨兵线程已启动")
        while self._running:
            try:
                time.sleep(self.sentry_interval_seconds)

                if not self._running:
                    break

                self._sentry_scan_orphans()

            except Exception as e:
                logger.error(f"❌ 哨兵线程异常: {e}")
                self.stats['errors'] += 1

        logger.info("🛡️  哨兵线程已停止")

    def listen(self, max_iterations: Optional[int] = None):
        """
        开始监听 NOTIFY 事件（阻塞模式）

        Args:
            max_iterations: 最大迭代次数（None=无限循环）
        """
        self.connect()
        self._running = True
        self.stats['started_at'] = datetime.now()

        # V38.0: 启动哨兵线程（事件驱动架构）
        if self.enable_sentry:
            self._sentry_thread = threading.Thread(
                target=self._sentry_worker,
                name="SentryWorker",
                daemon=True
            )
            self._sentry_thread.start()

        # V38.0: 更新版本号到 Sentry Self-Healing
        logger.info("=" * 70)
        logger.info("🚀 V38.0 EventBus 启动 (Sentry Self-Healing)")
        logger.info("=" * 70)
        logger.info(f"监听频道: matches_insert, odds_updated")
        logger.info(f"轮询间隔: {self.poll_interval}s")
        logger.info(f"启动自检: {'启用' if self.enable_self_check else '禁用'}")
        logger.info(f"Layer C 触发: {'启用' if self.enable_layer_c_trigger else '禁用'}")
        logger.info(f"Layer D 触发: {'启用(事件驱动)' if self.enable_layer_d_trigger else '禁用'}")
        logger.info(f"哨兵自愈: {'启用' if self.enable_sentry else '禁用'}")
        if self.enable_sentry:
            logger.info(f"哨兵间隔: {self.sentry_interval_seconds // 60} 分钟")
        logger.info(f"进程安全阀: {self.max_concurrent_processes} 并发")
        logger.info(f"启动时间: {self.stats['started_at'].isoformat()}")
        logger.info("=" * 70)

        iteration = 0
        try:
            while self._running:
                iteration += 1

                # 检查最大迭代次数
                if max_iterations and iteration > max_iterations:
                    logger.info(f"⏱️  达到最大迭代次数: {max_iterations}")
                    break

                # 轮询检查 NOTIFY 信号
                self.conn.poll()

                # 处理所有待处理的通知
                while self.conn.notifies:
                    notification = self.conn.notifies.pop()
                    self._process_notification(notification)

                # 短暂休眠
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("\n🛑 收到中断信号，正在停止...")
        except Exception as e:
            logger.error(f"❌ 监听异常: {e}")
        finally:
            self._running = False

            # V38.0: 等待哨兵线程停止
            if self._sentry_thread and self._sentry_thread.is_alive():
                logger.info("⏳ 等待哨兵线程停止...")
                self._sentry_thread.join(timeout=5)

            self.disconnect()
            self._print_summary()

    def _print_summary(self):
        """打印运行摘要"""
        elapsed = (datetime.now() - self.stats['started_at']).total_seconds()

        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 V38.0 EventBus 运行摘要 (Sentry Self-Healing)")
        logger.info("=" * 70)
        logger.info(f"运行时长: {elapsed:.1f}s")
        logger.info(f"收到通知: {self.stats['notifications_received']}")
        logger.info(f"  - matches_insert: {self.stats['matches_insert_count']}")
        logger.info(f"  - odds_updated: {self.stats['odds_updated_count']}")
        logger.info(f"触发狩猎: {self.stats['hash_hunts_triggered']}")
        logger.info(f"启动自检: 发现 {self.stats['self_check_orphans_found']} 场遗漏，处理 {self.stats['self_check_processed']} 场")
        logger.info(f"Layer C 触发: {self.stats['layer_c_triggered']} 次")
        logger.info(f"Layer D 触发: {self.stats['layer_d_triggered']} 次")
        logger.info(f"进程限流: {self.stats['processes_throttled']} 次")
        logger.info(f"当前活跃进程: {self._get_active_process_count()} 个")
        logger.info(f"错误次数: {self.stats['errors']}")
        # V38.0: 哨兵自愈统计
        if self.enable_sentry:
            logger.info(f"哨兵自愈: 运行 {self.stats['sentry_runs']} 次，发现 {self.stats['sentry_orphans_found']} 场孤儿，重推 {self.stats['sentry_notifies_sent']} 个 NOTIFY")
        logger.info("=" * 70)

    def get_production_metrics(self) -> Dict[str, Any]:
        """
        V37.4: 获取生产线指标（用于全景视图）

        Returns:
            包含成功率、平均耗时等指标的字典
        """
        with self.timing_lock:
            a_to_b_times = self.timing_stats['a_to_b'][-100:]  # 最近 100 条
            b_to_c_times = self.timing_stats['b_to_c'][-100:]
            c_to_d_times = self.timing_stats['c_to_d'][-100:]

        return {
            'a_to_b': {
                'count': len(a_to_b_times),
                'avg_time': sum(a_to_b_times) / len(a_to_b_times) if a_to_b_times else 0,
            },
            'b_to_c': {
                'count': len(b_to_c_times),
                'avg_time': sum(b_to_c_times) / len(b_to_c_times) if b_to_c_times else 0,
            },
            'c_to_d': {
                'count': len(c_to_d_times),
                'avg_time': sum(c_to_d_times) / len(c_to_d_times) if c_to_d_times else 0,
            },
        }

    def stop(self):
        """停止监听"""
        logger.info("🛑 停止 EventBus")
        self._running = False


# ============================================================================
# 独立运行入口
# ============================================================================

def main():
    """
    V37.4 独立运行 EventBus (Event-Driven Architecture)

    使用方法:
        # 基本运行（默认启用所有功能）
        python -m src.services.event_bus

        # 禁用启动自检
        python -m src.services.event_bus --no-self-check

        # 禁用 Layer C 自动触发
        python -m src.services.event_bus --no-layer-c

        # 禁用 Layer D 自动触发
        python -m src.services.event_bus --no-layer-d

        # 自定义并发进程数（安全阀）
        python -m src.services.event_bus --max-processes 4

        # 单次运行模式（用于测试）
        python -m src.services.event_bus --once

    环境变量:
        DB_NAME=football_db  # 必需
    """
    import argparse
    import os

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="V37.4 EventBus - Event-Driven Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--no-self-check',
        action='store_true',
        help='禁用启动自检功能'
    )
    parser.add_argument(
        '--no-layer-c',
        action='store_true',
        help='禁用 Layer C 自动触发功能'
    )
    parser.add_argument(
        '--no-layer-d',
        action='store_true',
        help='禁用 Layer D 自动触发功能'
    )
    parser.add_argument(
        '--self-check-days',
        type=int,
        default=7,
        help='启动自检扫描最近几天的数据 (默认: 7)'
    )
    parser.add_argument(
        '--max-processes',
        type=int,
        default=8,
        help='最大并发进程数/安全阀 (默认: 8)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='单次运行模式（处理启动自检后退出）'
    )
    parser.add_argument(
        '--poll-interval',
        type=float,
        default=1.0,
        help='轮询间隔（秒，默认: 1.0）'
    )

    args = parser.parse_args()

    # 环境校验
    db_name = os.getenv('DB_NAME', '')
    if db_name != 'football_db':
        print(f"❌ DB_NAME 必须为 'football_db'，当前: '{db_name}'")
        sys.exit(1)

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(name)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/event_bus.log'),
            logging.StreamHandler()
        ]
    )

    # 创建并启动 EventBus
    bus = EventBus(
        poll_interval=args.poll_interval,
        enable_self_check=not args.no_self_check,
        enable_layer_c_trigger=not args.no_layer_c,
        enable_layer_d_trigger=not args.no_layer_d,
        self_check_days=args.self_check_days,
        max_concurrent_processes=args.max_processes
    )

    try:
        if args.once:
            # 单次运行模式：只执行启动自检
            bus.connect()
            print("✅ 单次运行完成")
            bus.disconnect()
        else:
            # 无限循环监听
            bus.listen(max_iterations=None)
    except KeyboardInterrupt:
        bus.stop()


if __name__ == "__main__":
    main()
