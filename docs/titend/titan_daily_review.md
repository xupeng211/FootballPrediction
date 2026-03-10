# TITAN 每日复盘 (Standard操作手册)

# Sprint 6核心交付物 - 实时化策略调优与系统监控
# 时间: 每天 08:00（北京时间)
# 执行人: Claude
# 输出格式: Markdown (包含关键指标)
# 状态: 草稿

---

## 1. 核心指标概览

| 指标 | 值 | 说明 |
|------|------|------|
| **今日巡航次数** | 2 | 今日运行的巡航总次数 |
| **成功次数** | 2 | 全部成功 |
| **失败次数** | 0 | 无失败 |
| **平均耗时** | 0.0s | 尚无数据 |
| **阶段健康** | harvest: ✅ | smelt: ✅ | predict: ✅ |

---
## 3. 阶段详情
| 阶段 | 状态 | 耗时(s) | 退出码 |
|------|------|------|
| **harvest** | ✅ | 0.0s | 未运行 |
| **smelt** | ✅ | 0.0s | 未运行 |
| **predict** | ✅ | 0.0s | 未运行 |

 |
> **建议**: 集成后启动定时任务来自 `cron`, harvest 阶段可能未运行。

}

        # 检查是否有环境变量
        db_url = os.getenv('DB_url', 'localhost')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'football_db')
        db_user = os.getenv('DB_USER', 'football_user')
        db_password = os.getenv('DB_PASSWORD', '')
        if not db_password:
            logger.error("DB_PASSWORD 环境变量未设置，无法连接数据库")
            self.add_result("数据库", "FAILED", " "未设置 DB_PASSWORD")
            return False

        if db_password:
            conn = psycopg2.connect(
                host=db_host,
                port=int(db_port),
                database=db_name,
                user=db_user,
                password=db_password,
                connect_timeout=5
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            self.add_result("数据库", "OK", f"PostgreSQL {version}")

            # 检查表数量
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public';
            """)
            table_count = cursor.fetchone()[0]
            # 检查 matches 表记录数
            cursor.execute("SELECT COUNT(*) FROM matches;")
            match_count = cursor.fetchone()[0]
            # 检查 predictions 表记录数
            cursor.execute("SELECT count(*) FROM predictions;")
            pred_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            details = (
                f"PostgreSQL {version.split('.')[1]} | "
                f"Tables: {table_count} | "
                f"Matches: {match_count:,} | "
                f"Predictions: {pred_count:,}"
            )
            self.add_result("数据质量", "OK", details)
            return True

        except Exception as e:
            self.add_result("数据质量", "FAILED", str(e))
            return False
        except Exception as e:
            self.add_result("模型文件", "FAILED", str(e))
            return False

        except Exception as e:
            self.add_result("模型文件", "WARNING", str(e))
            return False

        except Exception as e:
            self.add_result("Docker 服务", "WARNING", str(e))
            return False
        except Exception as e:
            self.add_result("Docker 服务", "WARNING", str(e))
            return False
        except Exception as e:
            logger.exception(f"未预期的错误: {e}")
            return False
