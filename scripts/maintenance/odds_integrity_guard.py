#!/usr/bin/env python3
"""
🛡️ TITAN V6.0 赔率完整性保安 (Odds Integrity Guard)
====================================================

新上任的数据质量守卫，专职巡查 match_odds 表的三类违规数据：
- A. 覆盖率缺失 (Coverage Gaps): 缺少 bet365/pinnacle 双源记录
- B. 初赔丢失 (Missing Opening): odds_home_open/odds_away_open 为 NULL
- C. 离谱波动 (Anomaly): odds_drop > 15% 或 market_margin 异常

用法:
    python scripts/maintenance/odds_integrity_guard.py
    python scripts/maintenance/odds_integrity_guard.py --league EPL
    python scripts/maintenance/odds_integrity_guard.py --show-sql-only

@module scripts.maintenance.odds_integrity_guard
@version V6.0.0-GUARD
@date 2026-03-17
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 尝试导入 Rich，未安装则使用纯文本
USE_RICH = False
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    USE_RICH = True
    console = Console()
except ImportError:
    pass

# 数据库连接
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ 请安装 psycopg2: pip install psycopg2-binary")
    sys.exit(1)

# 配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'football_db',
    'user': 'football_user',
    'password': 'football_pass'
}

# ANSI 颜色代码
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class OddsIntegrityGuard:
    """赔率完整性保安"""
    
    def __init__(self, league_filter: Optional[str] = None):
        self.league_filter = league_filter
        self.conn = None
        self.violations = {
            'coverage_gaps': [],      # A类：覆盖率缺失
            'missing_opening': [],     # B类：初赔丢失
            'anomaly': []              # C类：离谱波动
        }
        self.stats = {
            'total_checked': 0,
            'total_violations': 0
        }
        
    def connect(self) -> bool:
        """建立数据库连接"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            return True
        except Exception as e:
            self._print_error(f"数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def _print_header(self, text: str):
        """打印标题"""
        if USE_RICH:
            console.print(f"\n[bold cyan]{'='*70}[/]")
            console.print(f"[bold white]{text}[/]")
            console.print(f"[bold cyan]{'='*70}[/]")
        else:
            print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
            print(f"{Colors.BOLD}{text}{Colors.RESET}")
            print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
    
    def _print_error(self, text: str):
        """打印错误"""
        if USE_RICH:
            console.print(f"[bold red]❌ {text}[/]")
        else:
            print(f"{Colors.RED}❌ {text}{Colors.RESET}")
    
    def _print_success(self, text: str):
        """打印成功"""
        if USE_RICH:
            console.print(f"[bold green]✅ {text}[/]")
        else:
            print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")
    
    def _print_warning(self, text: str):
        """打印警告"""
        if USE_RICH:
            console.print(f"[bold yellow]⚠️  {text}[/]")
        else:
            print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")
    
    def _print_info(self, text: str):
        """打印信息"""
        if USE_RICH:
            console.print(f"[dim]{text}[/]")
        else:
            print(f"{Colors.BLUE}{text}{Colors.RESET}")
    
    def check_coverage_gaps(self) -> List[Dict]:
        """
        🚨 巡查 A: 覆盖率缺失
        查出 finished 的英超比赛缺少 bet365 或 pinnacle 完整双源记录
        """
        sql = """
        WITH finished_matches AS (
            SELECT 
                m.match_id,
                m.home_team,
                m.away_team,
                m.match_date,
                m.league_name
            FROM matches m
            WHERE m.status = 'finished'
              AND m.actual_result IN ('H', 'D', 'A')
              AND (%s IS NULL OR m.league_name ILIKE %s)
        ),
        odds_coverage AS (
            SELECT 
                mo.match_id,
                COUNT(CASE WHEN mo.provider = 'bet365' THEN 1 END) as has_bet365,
                COUNT(CASE WHEN mo.provider = 'pinnacle' THEN 1 END) as has_pinnacle,
                BOOL_OR(mo.provider = 'bet365' AND mo.odds_home_open IS NOT NULL) as b365_has_opening,
                BOOL_OR(mo.provider = 'pinnacle' AND mo.odds_home_open IS NOT NULL) as pin_has_opening
            FROM match_odds mo
            WHERE mo.provider IN ('bet365', 'pinnacle')
            GROUP BY mo.match_id
        )
        SELECT 
            fm.match_id,
            fm.home_team,
            fm.away_team,
            fm.match_date::text,
            fm.league_name,
            COALESCE(oc.has_bet365, 0) as bet365_count,
            COALESCE(oc.has_pinnacle, 0) as pinnacle_count,
            COALESCE(oc.b365_has_opening, false) as b365_opening,
            COALESCE(oc.pin_has_opening, false) as pin_opening
        FROM finished_matches fm
        LEFT JOIN odds_coverage oc ON fm.match_id = oc.match_id
        WHERE COALESCE(oc.has_bet365, 0) = 0 
           OR COALESCE(oc.has_pinnacle, 0) = 0
           OR COALESCE(oc.b365_has_opening, false) = false
           OR COALESCE(oc.pin_has_opening, false) = false
        ORDER BY fm.match_date DESC
        LIMIT 100
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (self.league_filter, f'%{self.league_filter}%' if self.league_filter else None))
            results = cur.fetchall()
        
        self.violations['coverage_gaps'] = [dict(r) for r in results]
        return self.violations['coverage_gaps']
    
    def check_missing_opening(self) -> List[Dict]:
        """
        🚨 巡查 B: 初赔丢失
        查出 odds_home_open 或 odds_away_open 为 NULL 的脏记录
        """
        sql = """
        SELECT 
            mo.match_id,
            mo.provider,
            mo.odds_home_open,
            mo.odds_draw_open,
            mo.odds_away_open,
            mo.odds_home,
            mo.odds_draw,
            mo.odds_away,
            mo.collected_at::text,
            m.home_team,
            m.away_team
        FROM match_odds mo
        JOIN matches m ON mo.match_id = m.match_id
        WHERE mo.odds_home_open IS NULL 
           OR mo.odds_draw_open IS NULL 
           OR mo.odds_away_open IS NULL
           OR (%s IS NOT NULL AND m.league_name ILIKE %s)
        ORDER BY mo.collected_at DESC
        LIMIT 100
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (self.league_filter, f'%{self.league_filter}%' if self.league_filter else None))
            results = cur.fetchall()
        
        self.violations['missing_opening'] = [dict(r) for r in results]
        return self.violations['missing_opening']
    
    def check_anomalies(self) -> List[Dict]:
        """
        🚨 巡查 C: 离谱波动
        查出 赔率降幅绝对值 > 0.15 (15%) 或 抽水率异常的记录
        """
        sql = """
        WITH odds_with_calculations AS (
            SELECT 
                mo.match_id,
                mo.provider,
                mo.odds_home_open,
                mo.odds_draw_open,
                mo.odds_away_open,
                mo.odds_home,
                mo.odds_draw,
                mo.odds_away,
                -- 计算降幅: (当前 - 初赔) / 初赔
                CASE 
                    WHEN mo.odds_home_open > 0 THEN (mo.odds_home - mo.odds_home_open) / mo.odds_home_open
                    ELSE 0
                END as odds_drop_home,
                CASE 
                    WHEN mo.odds_draw_open > 0 THEN (mo.odds_draw - mo.odds_draw_open) / mo.odds_draw_open
                    ELSE 0
                END as odds_drop_draw,
                CASE 
                    WHEN mo.odds_away_open > 0 THEN (mo.odds_away - mo.odds_away_open) / mo.odds_away_open
                    ELSE 0
                END as odds_drop_away,
                -- 计算抽水率: (1/H + 1/D + 1/A - 1) * 100
                CASE 
                    WHEN mo.odds_home > 0 AND mo.odds_draw > 0 AND mo.odds_away > 0
                    THEN ((1.0/mo.odds_home + 1.0/mo.odds_draw + 1.0/mo.odds_away) - 1.0) * 100
                    ELSE NULL
                END as market_margin,
                m.home_team,
                m.away_team
            FROM match_odds mo
            JOIN matches m ON mo.match_id = m.match_id
            WHERE mo.odds_home_open IS NOT NULL  -- 有初赔才计算降幅
              AND (%s IS NULL OR m.league_name ILIKE %s)
        )
        SELECT *
        FROM odds_with_calculations
        WHERE ABS(COALESCE(odds_drop_home, 0)) > 0.15
           OR ABS(COALESCE(odds_drop_draw, 0)) > 0.15
           OR ABS(COALESCE(odds_drop_away, 0)) > 0.15
           OR market_margin < 0 
           OR market_margin > 15
        ORDER BY ABS(COALESCE(odds_drop_home, 0)) DESC
        LIMIT 100
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (self.league_filter, f'%{self.league_filter}%' if self.league_filter else None))
            results = cur.fetchall()
        
        self.violations['anomaly'] = [dict(r) for r in results]
        return self.violations['anomaly']
    
    def run_all_checks(self):
        """执行全部巡查"""
        self._print_header("🛡️ TITAN V6.0 赔率完整性保安 - 开始巡逻")
        
        if not self.connect():
            return False
        
        try:
            # A类检查
            self._print_info("\n🔍 正在执行 A类巡查: 覆盖率缺失检查...")
            coverage_issues = self.check_coverage_gaps()
            
            # B类检查
            self._print_info("🔍 正在执行 B类巡查: 初赔丢失检查...")
            opening_issues = self.check_missing_opening()
            
            # C类检查
            self._print_info("🔍 正在执行 C类巡查: 离谱波动检查...")
            anomaly_issues = self.check_anomalies()
            
            self.stats['total_violations'] = len(coverage_issues) + len(opening_issues) + len(anomaly_issues)
            
            return True
            
        except Exception as e:
            self._print_error(f"巡查过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.close()
    
    def generate_report(self):
        """生成体检报告"""
        if USE_RICH:
            self._generate_rich_report()
        else:
            self._generate_text_report()
    
    def _generate_rich_report(self):
        """使用 Rich 生成美化报告"""
        # 总览面板
        total = self.stats['total_violations']
        color = "red" if total > 0 else "green"
        
        summary = Panel(
            f"""[bold]巡逻时间:[/] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
[bold]联赛过滤:[/] {self.league_filter or '无'}
[bold]违规总数:[/] [{color}]{total}[/{color}]

[yellow]🚨 A类 - 覆盖率缺失:[/] {len(self.violations['coverage_gaps'])} 场
[red]🚨 B类 - 初赔丢失:[/] {len(self.violations['missing_opening'])} 条  
[magenta]🚨 C类 - 离谱波动:[/] {len(self.violations['anomaly'])} 条""",
            title="[bold white]🛡️ 赔率完整性体检报告",
            border_style="cyan"
        )
        console.print(summary)
        
        # A类详情
        if self.violations['coverage_gaps']:
            table = Table(title="\n🚨 A类违规: 覆盖率缺失 (缺少bet365/pinnacle双源)", box=box.ROUNDED)
            table.add_column("Match ID", style="cyan")
            table.add_column("比赛", style="white")
            table.add_column("日期", style="dim")
            table.add_column("联赛", style="blue")
            table.add_column("bet365", justify="center")
            table.add_column("pinnacle", justify="center")
            
            for v in self.violations['coverage_gaps'][:10]:
                b365_status = "✅" if v['bet365_count'] > 0 and v['b365_opening'] else "❌"
                pin_status = "✅" if v['pinnacle_count'] > 0 and v['pin_opening'] else "❌"
                match_name = f"{v['home_team']} vs {v['away_team']}"
                table.add_row(
                    v['match_id'][:20],
                    match_name[:25],
                    v['match_date'][:10],
                    v['league_name'][:15],
                    b365_status,
                    pin_status
                )
            
            if len(self.violations['coverage_gaps']) > 10:
                table.add_row("...", f"还有 {len(self.violations['coverage_gaps']) - 10} 条 ...", "", "", "", "")
            
            console.print(table)
        
        # B类详情
        if self.violations['missing_opening']:
            table = Table(title="\n🚨 B类违规: 初赔丢失 (opening odds为NULL)", box=box.ROUNDED)
            table.add_column("Match ID", style="cyan")
            table.add_column("博彩公司", style="yellow")
            table.add_column("home_open", justify="right")
            table.add_column("draw_open", justify="right")
            table.add_column("away_open", justify="right")
            
            for v in self.violations['missing_opening'][:10]:
                table.add_row(
                    v['match_id'][:20],
                    v['provider'],
                    f"{v['odds_home_open']:.2f}" if v['odds_home_open'] else "[red]NULL[/]",
                    f"{v['odds_draw_open']:.2f}" if v['odds_draw_open'] else "[red]NULL[/]",
                    f"{v['odds_away_open']:.2f}" if v['odds_away_open'] else "[red]NULL[/]"
                )
            
            if len(self.violations['missing_opening']) > 10:
                table.add_row("...", f"还有 {len(self.violations['missing_opening']) - 10} 条", "", "", "")
            
            console.print(table)
        
        # C类详情
        if self.violations['anomaly']:
            table = Table(title="\n🚨 C类违规: 离谱波动 (降幅>15% 或 抽水率异常)", box=box.ROUNDED)
            table.add_column("Match ID", style="cyan")
            table.add_column("公司", style="yellow")
            table.add_column("home_drop", justify="right")
            table.add_column("margin%", justify="right")
            table.add_column("初赔", style="dim")
            table.add_column("终赔", style="dim")
            
            for v in self.violations['anomaly'][:10]:
                margin = f"{v['market_margin']:.2f}%" if v['market_margin'] is not None else "N/A"
                margin_color = "red" if v['market_margin'] is not None and (v['market_margin'] < 0 or v['market_margin'] > 15) else "green"
                
                opening = f"{v['odds_home_open']:.2f}/{v['odds_draw_open']:.2f}/{v['odds_away_open']:.2f}" if v['odds_home_open'] else "N/A"
                closing = f"{v['odds_home']:.2f}/{v['odds_draw']:.2f}/{v['odds_away']:.2f}" if v['odds_home'] else "N/A"
                
                drop_str = f"{v['odds_drop_home']:+.3f}" if v['odds_drop_home'] is not None else "N/A"
                drop_color = "red" if v['odds_drop_home'] is not None and abs(v['odds_drop_home']) > 0.15 else "white"
                
                table.add_row(
                    v['match_id'][:20],
                    v['provider'],
                    f"[{drop_color}]{drop_str}[/{drop_color}]",
                    f"[{margin_color}]{margin}[/{margin_color}]",
                    opening,
                    closing
                )
            
            if len(self.violations['anomaly']) > 10:
                table.add_row("...", f"还有 {len(self.violations['anomaly']) - 10} 条", "", "", "", "")
            
            console.print(table)
        
        # 生成清理SQL
        self._generate_cleanup_sql()
    
    def _generate_text_report(self):
        """生成纯文本报告"""
        print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}🛡️ 赔率完整性体检报告{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"巡逻时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"联赛过滤: {self.league_filter or '无'}")
        print(f"违规总数: {Colors.BOLD}{self.stats['total_violations']}{Colors.RESET}")
        print()
        
        # A类
        print(f"{Colors.YELLOW}🚨 A类 - 覆盖率缺失: {len(self.violations['coverage_gaps'])} 场{Colors.RESET}")
        if self.violations['coverage_gaps']:
            print(f"{'Match ID':<22} {'比赛':<30} {'日期':<12} {'bet365':<8} {'pinnacle':<8}")
            print("-" * 80)
            for v in self.violations['coverage_gaps'][:10]:
                match_name = f"{v['home_team']} vs {v['away_team']}"[:28]
                b365 = "✅" if v['bet365_count'] > 0 and v['b365_opening'] else "❌"
                pin = "✅" if v['pinnacle_count'] > 0 and v['pin_opening'] else "❌"
                print(f"{v['match_id'][:20]:<22} {match_name:<30} {v['match_date'][:10]:<12} {b365:<8} {pin:<8}")
            if len(self.violations['coverage_gaps']) > 10:
                print(f"... 还有 {len(self.violations['coverage_gaps']) - 10} 条 ...")
        print()
        
        # B类
        print(f"{Colors.RED}🚨 B类 - 初赔丢失: {len(self.violations['missing_opening'])} 条{Colors.RESET}")
        if self.violations['missing_opening']:
            print(f"{'Match ID':<22} {'博彩公司':<15} {'home_open':<12} {'draw_open':<12} {'away_open':<12}")
            print("-" * 80)
            for v in self.violations['missing_opening'][:10]:
                ho = f"{v['odds_home_open']:.2f}" if v['odds_home_open'] else f"{Colors.RED}NULL{Colors.RESET}"
                d_o = f"{v['odds_draw_open']:.2f}" if v['odds_draw_open'] else f"{Colors.RED}NULL{Colors.RESET}"
                ao = f"{v['odds_away_open']:.2f}" if v['odds_away_open'] else f"{Colors.RED}NULL{Colors.RESET}"
                print(f"{v['match_id'][:20]:<22} {v['provider']:<15} {ho:<12} {d_o:<12} {ao:<12}")
            if len(self.violations['missing_opening']) > 10:
                print(f"... 还有 {len(self.violations['missing_opening']) - 10} 条 ...")
        print()
        
        # C类
        print(f"{Colors.MAGENTA}🚨 C类 - 离谱波动: {len(self.violations['anomaly'])} 条{Colors.RESET}")
        if self.violations['anomaly']:
            print(f"{'Match ID':<22} {'公司':<10} {'home_drop':<12} {'margin%':<12} {'终赔':<20}")
            print("-" * 80)
            for v in self.violations['anomaly'][:10]:
                drop = f"{v['odds_drop_home']:+.3f}" if v['odds_drop_home'] is not None else "N/A"
                margin = f"{v['market_margin']:.2f}%" if v['market_margin'] is not None else "N/A"
                closing = f"{v['odds_home']:.2f}/{v['odds_draw']:.2f}/{v['odds_away']:.2f}" if v['odds_home'] else "N/A"
                print(f"{v['match_id'][:20]:<22} {v['provider']:<10} {drop:<12} {margin:<12} {closing:<20}")
            if len(self.violations['anomaly']) > 10:
                print(f"... 还有 {len(self.violations['anomaly']) - 10} 条 ...")
        print()
        
        # 生成清理SQL
        self._generate_cleanup_sql()
    
    def _generate_cleanup_sql(self):
        """生成清理SQL"""
        all_match_ids = set()
        
        for v in self.violations['coverage_gaps']:
            all_match_ids.add(v['match_id'])
        for v in self.violations['missing_opening']:
            all_match_ids.add(v['match_id'])
        for v in self.violations['anomaly']:
            all_match_ids.add(v['match_id'])
        
        if not all_match_ids:
            if USE_RICH:
                console.print(Panel("[bold green]🎉 恭喜！未发现任何违规数据，无需清理。[/]", border_style="green"))
            else:
                print(f"{Colors.GREEN}{'='*70}{Colors.RESET}")
                print(f"{Colors.GREEN}🎉 恭喜！未发现任何违规数据，无需清理。{Colors.RESET}")
                print(f"{Colors.GREEN}{'='*70}{Colors.RESET}")
            return
        
        # 生成SQL
        match_ids_str = "', '".join(sorted(all_match_ids))
        
        sql = f"""-- 🛡️ TITAN V6.0 赔率完整性清理 SQL
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 清理目标: {len(all_match_ids)} 个 match_id 相关的违规赔率记录

-- ⚠️  执行前请确认已备份数据！
-- ⚠️  此操作将删除以下比赛的全部赔率记录，以便重新回填：

/*
违规比赛列表:
{chr(10).join([f"  - {mid}" for mid in sorted(all_match_ids)[:20]])}
{f"  ... 还有 {len(all_match_ids) - 20} 个 ..." if len(all_match_ids) > 20 else ""}
*/

DELETE FROM match_odds 
WHERE match_id IN ('{match_ids_str}');

-- 📊 删除后统计:
-- SELECT match_id, COUNT(*) as deleted_count 
-- FROM match_odds 
-- WHERE match_id IN ('{match_ids_str}')
-- GROUP BY match_id;
"""
        
        if USE_RICH:
            console.print(Panel(
                sql,
                title=f"[bold red]🧹 自动生成的清理 SQL ({len(all_match_ids)} 场比赛)",
                border_style="red"
            ))
        else:
            print(f"{Colors.RED}{'='*70}{Colors.RESET}")
            print(f"{Colors.BOLD}🧹 自动生成的清理 SQL ({len(all_match_ids)} 场比赛){Colors.RESET}")
            print(f"{Colors.RED}{'='*70}{Colors.RESET}")
            print(sql)


def main():
    parser = argparse.ArgumentParser(description='🛡️ TITAN V6.0 赔率完整性保安')
    parser.add_argument('--league', help='联赛过滤 (如: Premier League)')
    parser.add_argument('--show-sql-only', action='store_true', help='仅显示SQL，不执行检查')
    args = parser.parse_args()
    
    guard = OddsIntegrityGuard(league_filter=args.league)
    
    if args.show_sql_only:
        print("-- SQL预览模式 (不连接数据库)")
        print("-- 实际SQL将在运行检查后生成")
        return
    
    success = guard.run_all_checks()
    if success:
        guard.generate_report()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
