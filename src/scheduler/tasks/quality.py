"""
质量检查任务
Quality Check Tasks

包含数据质量检查任务。
"""




logger = logging.getLogger(__name__)


async def _check_data_integrity(session, monitor):
    """检查数据完整性"""
    checks_performed = 0
    issues_found = 0

    logger.info("检查数据完整性...")
    integrity_checks = [
        ("matches", "检查比赛数据完整性"),
        ("teams", "检查球队数据完整性"),
        ("leagues", "检查联赛数据完整性"),
        ("raw_match_data", "检查原始比赛数据完整性"),
        ("raw_odds_data", "检查原始赔率数据完整性"),
    ]

    for table_name, description in integrity_checks:
        try:
            result = await monitor.check_data_integrity(session, table_name)
            checks_performed += 1
            if not result.get("passed", True):
                issues_found += result.get("issues_count", 1)
                logger.warning(f"{description} 发现问题: {result.get('issues', [])}")
            else:
                logger.info(f"{description} 通过")
        except Exception as e:
            logger.error(f"{description} 检查失败: {str(e)}")
            issues_found += 1

    return checks_performed, issues_found


async def _check_data_consistency(session, monitor):
    """检查数据一致性"""
    checks_performed = 0
    issues_found = 0

    logger.info("检查数据一致性...")
    consistency_checks = [
        ("check_match_team_consistency", "检查比赛与球队数据一致性"),
        ("check_odds_match_consistency", "检查赔率与比赛数据一致性"),
        ("check_league_team_consistency", "检查联赛与球队数据一致性"),
    ]

    for check_name, description in consistency_checks:
        try:
            result = await monitor.check_data_consistency(session, check_name)
            checks_performed += 1
            if not result.get("passed", True):
                issues_found += result.get("issues_count", 1)
                logger.warning(f"{description} 发现问题: {result.get('issues', [])}")
            else:
                logger.info(f"{description} 通过")
        except Exception as e:
            logger.error(f"{description} 检查失败: {str(e)}")
            issues_found += 1

    return checks_performed, issues_found


async def _check_data_freshness(session, monitor):
    """检查数据新鲜度"""
    checks_performed = 0
    issues_found = 0

    logger.info("检查数据新鲜度...")
    freshness_checks = [
        ("matches", "检查比赛数据新鲜度", 24),  # 24小时
        ("raw_match_data", "检查原始比赛数据新鲜度", 6),  # 6小时
        ("raw_odds_data", "检查原始赔率数据新鲜度", 12),  # 12小时
    ]

    for table_name, description, hours_threshold in freshness_checks:
        try:
            result = await monitor.check_data_freshness(
                session, table_name, hours_threshold
            )
            checks_performed += 1
            if not result.get("passed", True):
                issues_found += result.get("issues_count", 1)
                logger.warning(f"{description} 发现问题: {result.get('issues', [])}")
            else:
                logger.info(f"{description} 通过")
        except Exception as e:
            logger.error(f"{description} 检查失败: {str(e)}")
            issues_found += 1

    return checks_performed, issues_found


async def _generate_quality_report(session, monitor):
    """生成质量报告"""
    checks_performed = 0
    issues_found = 0

    logger.info("生成数据质量报告...")
    try:
        report_result = await monitor.generate_quality_report(session)
        if report_result.get("status") == "success":
            logger.info("数据质量报告生成成功")
            checks_performed += 1
        else:
            logger.error(
                f"数据质量报告生成失败: {report_result.get('error', 'Unknown error')}"
            )
            issues_found += 1
    except Exception as e:
        logger.error(f"生成数据质量报告时出错: {str(e)}")
        issues_found += 1

    return checks_performed, issues_found


@app.task(base=BaseDataTask)
def run_quality_checks():
    """运行数据质量检查任务"""
    try:
        logger.info("开始执行数据质量检查任务")

        async def _run_checks():
            """异步运行质量检查"""
            async with get_async_session() as session:
                # 初始化数据质量监控器
                monitor = DataQualityMonitor()

                # 1. 检查数据完整性
                integrity_checks, integrity_issues = await _check_data_integrity(
                    session, monitor


                )

                # 2. 检查数据一致性
                consistency_checks, consistency_issues = await _check_data_consistency(
                    session, monitor
                )

                # 3. 检查数据新鲜度
                freshness_checks, freshness_issues = await _check_data_freshness(
                    session, monitor
                )

                # 4. 生成质量报告
                report_checks, report_issues = await _generate_quality_report(
                    session, monitor
                )

                total_checks = (
                    integrity_checks
                    + consistency_checks
                    + freshness_checks
                    + report_checks
                )
                total_issues = (
                    integrity_issues
                    + consistency_issues
                    + freshness_issues
                    + report_issues
                )

                return total_checks, total_issues

        # 运行异步质量检查
        checks_performed, issues_found = asyncio.run(_run_checks())

        logger.info(
            f"数据质量检查任务完成: 执行了 {checks_performed} 项检查，发现 {issues_found} 个问题"
        )

        return {
            "status": "success",
            "checks_performed": checks_performed,
            "issues_found": issues_found,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"数据质量检查任务失败: {str(exc)}")
        raise