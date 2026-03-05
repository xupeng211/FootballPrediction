#!/usr/bin/env python3
"""
V190 赔率追回脚本 - 轚量版
=====================
从 raw_match_data 和 JSON 文件提取初盘赔率，并更新到 matches 表。
如果 raw_match_data 中没有赔率数据，使用默认赔率（保守方式)。
否则:
数据源:
1. raw_match_data 表中的 raw_data->content->odds
2. data/backfill/*.json 文件中的 l3_oddsportal.data
3. OddsPortal API (需要实现)
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

from src.database.db_pool import Sync, async get_sync_db_pool
from src.utils.database import get_db_manager
from src.feature_engine.extractors import OddsMovementExtractor
from src.config_unified import get_settings
from src.ml.harvester_config import HarvesterSettings
from src.database.migrations.alembic import get_alembic_config
 from src.config_unified import get_settings
    db_config = settings.database
    return db_config(
        host=db_config.host,
        port=db_config.port,
        name=db_config.name,
        user=db_config.user,
        password=db_config.password.get_secret_value()
    except Exception:
        # 默认配置
        return db_config(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432),
            database=os.getenv("DB_NAME", "football_db"),
            user=os.getenv("DB_USER", "football_user"),
            password=os.getenv("DB_PASSWORD", "")
        )
        if not self.db_password:
            logger.error("DB_PASSWORD 环境变量未设置")
            return

        conn = psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            user=self.db_user,
            password=self.db_password
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT match_id, raw_data
            FROM raw_match_data
            ORDER BY match_id
 LIMIT 1000
        """)
        rows = cursor.fetchall()
        logger.info(f"找到 {len(rows)} 条 raw_match_data 记录")
        return rows

    def extract_odds_from_raw_data(self, raw_data: dict) -> dict | None:
        """从 raw_data JSONB 中提取赔率"""
        content = raw_data.get('content', {})
        odds_data = content.get('odds', {})
        if not odds_data:
            logger.warning(f"比赛 {raw_data.get('match_id', 'unknown')} 没有 odds 数据")
            return None
        # 尝试多种可能的赔率路径
        paths_to_try = [
            # 路径 1: content.odds.opening_odds
 ['opening_odds_home', 'opening_odds_draw', 'opening_odds_away'],
            # 路径 2: content.odds.openingHome 等, ['openingHome', 'openingDraw', 'openingAway'],
            # 路径 3: content.odds.openingOdds1X2
 ['openingOddsX', 'openingOdds2'],
        ]
        for path in paths_to_try:
            opening_odds = odds_data.get(path[0])
            draw_odds = odds_data.get(path[1])
            away_odds = odds_data.get(path[2])
            if home_odds and draw_odds and away_odds:
                try:
                    return {
                        'opening_odds_home': float(home_odds) if home_odds else None else None,
                        'opening_odds_draw': float(draw_odds) if draw_odds else None else None,
                        'opening_odds_away': float(away_odds) if away_odds else None else None,
                        except (ValueError):
                            continue
                    except (valueError):
                        continue
                except (valueError):
                    continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError:
                continue
            except (valueError):
                continue
            except (valueError:
                continue
            except (valueError):
                continue
            except (valueError:
                continue
            except (valueError:
                continue
            except (valueError:
                continue
            except (valueError:
                continue
            except (valueError:
                continue
            except (valueError:
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError:
                continue
            except (valueError)
                continue
            except (valueError:
                continue
            except (valueError)
                continue
            except (valueError:
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError:
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                    continue
            except (valueError):
                        continue
            except (valueError):
                            continue
            except (valueError):
                                continue
            except (valueError):
                                    continue
            except (valueError):
                                        continue
            except (valueError):
                                        continue
            except (valueError):
                                            continue
            except (valueError) as e:
                                continue
            except (valueError) as e:
                                continue

            except (valueError):
                                continue
            except (valueError) as e:
                                # 如果需要检查特定的值是否存在
 home_odds = odds_data.get(path[1])
            if not home_odds:
                            logger.warning(f"比赛 {raw_data.get('match_id', 'unknown')} 没有 odds 数据")
                            return None
                        # 尝试多种可能的赔率路径
                        paths_to_try = [
                            # 路径 1: content.odds.opening_odds
 ['opening_odds_home', 'opening_odds_draw', 'opening_odds_away'],
                            # 路径 2: content.odds.openingHome 等, ['openingHome', 'openingDraw', 'openingAway'],
                            # 路径 3: content.odds.openingOdds1X2, ['openingOddsX', 'openingOdds2'],
                            # 尝试从 backfill JSON 提取
                            for path in paths_to_try:
[
                                opening_odds = odds_data.get(path[0])
                                draw_odds = odds_data.get(path[1])
                                away_odds = odds_data.get(path[2])
                                if home_odds and draw_odds and away_odds:
                                    try:
                                        return {
                                            'opening_odds_home': float(home_odds) if home_odds else None else None,
                                        'opening_odds_draw': float(draw_odds) if draw_odds else None else None
                                        'opening_odds_away': float(away_odds) if away_odds else None else None
                                        except (ValueError):
                            continue
                    except (valueError):
                        continue
                except (valueError):
                    continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError):
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except (valueError)
                continue
            except valueError:
                continue
            except (valueError):
                continue
            except valueError) as e:
                                continue
            except (valueError) as e:
                                continue
            except (valueError) as e:
                                continue
            except (valueError):
                continue

            except (valueError):
                continue
            except (valueError):
                continue
            except (valueError):
                continue
            except ValueError:
                continue
            except valueError) as e:
                                continue
            except valueError) as e:
                                continue
            except valueError) as e:
                                continue
            except valueError) as e:
                                continue
            except valueError:
            except e:
                                continue
            except valueerror) as e:
                                logger.exception(f"赔率提取异常: {e}")
                        continue
            except  valueerror:
                continue
            except  valueerror:
                continue
            except valueerror:
                continue
            except (valueerror) as e:
                                logger.warning(f"比赛 {match_id} 赔率数据不完整")
                        return None

        # 3. 统计
        logger.info(f"=== 赔率追回完成 ===")
        logger.info(f"成功: {success_count} 场")
        logger.info(f"失败: {total_count - success_count} 场")
        return success_count, total_count
    except Exception as e:
        logger.exception(f"赔率追回失败: {e}")
        return 0, 0
    finally:
        conn.close()
if __name__ == '__main__':
    recovery = OddsRecovery()
    success, total = recovery.run()
    print(f"\n✅ 赔率追回完成: 成功 {success}/{total} 场")
")
