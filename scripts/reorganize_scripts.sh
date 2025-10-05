#!/bin/bash
# Scripts 重组脚本
# 用途：将混乱的 scripts/ 目录按功能分类重组
# 作者：AI Assistant
# 日期：2025-10-05

set -e

SCRIPTS_DIR="/home/user/projects/FootballPrediction/scripts"
cd "$SCRIPTS_DIR"

echo "🚀 开始 Scripts 目录重组..."
echo "================================================"

# 1. CI/CD 相关脚本
echo "📦 1/8 移动 CI/CD 脚本..."
mv ci_guardian.py ci/guardian.py 2>/dev/null || true
mv ci_monitor.py ci/monitor.py 2>/dev/null || true
mv ci_issue_analyzer.py ci/issue_analyzer.py 2>/dev/null || true
mv auto_ci_updater.py ci/auto_updater.py 2>/dev/null || true
mv defense_validator.py ci/ 2>/dev/null || true
mv defense_generator.py ci/ 2>/dev/null || true
mv auto_bugfix_cycle.py ci/ 2>/dev/null || true
mv generate_ci_report.py ci/generate_report.py 2>/dev/null || true
mv demo_ci_guardian.py ci/demo_guardian.py 2>/dev/null || true

# 2. 测试相关脚本
echo "📦 2/8 移动测试脚本..."
mv run_tests_with_report.py testing/run_with_report.py 2>/dev/null || true
mv coverage_tracker.py testing/ 2>/dev/null || true
mv run_full_coverage.py testing/ 2>/dev/null || true
mv validate_coverage_consistency.py testing/validate_coverage.py 2>/dev/null || true
mv improve_coverage.py testing/ 2>/dev/null || true
mv generate_test_templates.py testing/generate_templates.py 2>/dev/null || true
mv coverage_bugfix_loop.py testing/ 2>/dev/null || true
mv coverage_auto_phase1.py testing/ 2>/dev/null || true
mv coverage_dashboard.py testing/ 2>/dev/null || true
mv check_todo_tests.py testing/ 2>/dev/null || true

# 3. 质量检查脚本
echo "📦 3/8 移动质量检查脚本..."
mv quality_checker.py quality/checker.py 2>/dev/null || true
mv docs_guard.py quality/ 2>/dev/null || true
mv collect_quality_trends.py quality/collect_trends.py 2>/dev/null || true
mv context_loader.py quality/ 2>/dev/null || true

# 4. 依赖管理脚本
echo "📦 4/8 移动依赖管理脚本..."
mv analyze_dependencies.py dependency/analyze.py 2>/dev/null || true
mv check_dependencies.py dependency/check.py 2>/dev/null || true
mv lock_dependencies.py dependency/lock.py 2>/dev/null || true

# 5. 部署运维脚本
echo "📦 5/8 移动部署运维脚本..."
mv env_checker.py deployment/ 2>/dev/null || true
mv setup_project.py deployment/ 2>/dev/null || true
mv end_to_end_verification.py deployment/e2e_verification.py 2>/dev/null || true
mv prepare_test_db.py deployment/ 2>/dev/null || true
mv backup.sh deployment/ 2>/dev/null || true
mv restore.sh deployment/ 2>/dev/null || true
mv deploy.sh deployment/ 2>/dev/null || true
mv deploy-production.sh deployment/ 2>/dev/null || true
mv start_production.sh deployment/ 2>/dev/null || true
mv start-production.sh deployment/ 2>/dev/null || true

# 6. 机器学习脚本
echo "📦 6/8 移动机器学习脚本..."
mv retrain_pipeline.py ml/ 2>/dev/null || true
mv run_pipeline.py ml/ 2>/dev/null || true
mv update_predictions_results.py ml/update_predictions.py 2>/dev/null || true
mv feast_init.py ml/ 2>/dev/null || true
mv refresh_materialized_views.py ml/ 2>/dev/null || true
mv materialized_views_examples.py ml/ 2>/dev/null || true
mv test_performance_migration.py ml/ 2>/dev/null || true

# 7. 分析工具脚本
echo "📦 7/8 移动分析工具脚本..."
mv kanban_next.py analysis/kanban.py 2>/dev/null || true
mv sync_issues.py analysis/ 2>/dev/null || true
mv project_template_generator.py analysis/ 2>/dev/null || true

# 8. 归档临时脚本
echo "📦 8/8 归档临时脚本..."
# Phase 相关临时脚本
mv phase4_todo_replacement.py archive/ 2>/dev/null || true
mv select_batch2_files.py archive/ 2>/dev/null || true

# 一次性修复脚本
mv fix_critical_issues.py archive/ 2>/dev/null || true
mv fix_undefined_vars.py archive/ 2>/dev/null || true
mv fix_model_integration.py archive/ 2>/dev/null || true
mv line_length_fix.py archive/ 2>/dev/null || true
mv process_orphans.py archive/ 2>/dev/null || true
mv identify_legacy_tests.py archive/ 2>/dev/null || true

# 重构相关临时脚本
mv refactor_api_tests.py archive/ 2>/dev/null || true
mv refactor_services_tests.py archive/ 2>/dev/null || true

# 生成器相关
mv generate_scaffold_dashboard.py archive/ 2>/dev/null || true
mv generate_fix_plan.py archive/ 2>/dev/null || true

# 其他临时脚本
mv cleanup_test_docs.py archive/ 2>/dev/null || true
mv cursor_runner.py archive/ 2>/dev/null || true
mv test_failure.py archive/ 2>/dev/null || true

echo ""
echo "✅ Scripts 重组完成！"
echo "================================================"
echo ""
echo "📊 重组统计："
echo "  - CI/CD: $(find ci/ -name '*.py' 2>/dev/null | wc -l) 个脚本"
echo "  - 测试: $(find testing/ -name '*.py' 2>/dev/null | wc -l) 个脚本"
echo "  - 质量: $(find quality/ -name '*.py' 2>/dev/null | wc -l) 个脚本"
echo "  - 依赖: $(find dependency/ -name '*.py' 2>/dev/null | wc -l) 个脚本"
echo "  - 部署: $(find deployment/ -type f 2>/dev/null | wc -l) 个脚本"
echo "  - ML: $(find ml/ -name '*.py' 2>/dev/null | wc -l) 个脚本"
echo "  - 分析: $(find analysis/ -name '*.py' 2>/dev/null | wc -l) 个脚本"
echo "  - 归档: $(find archive/ -name '*.py' 2>/dev/null | wc -l) 个脚本"
echo ""
echo "⚠️  请注意："
echo "  1. 需要更新 Makefile 中的脚本路径"
echo "  2. 需要更新文档中的脚本引用"
echo "  3. 运行 'git status' 查看更改"
echo ""
