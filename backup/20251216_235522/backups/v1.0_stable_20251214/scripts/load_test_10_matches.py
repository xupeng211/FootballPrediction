#!/usr/bin/env python3
"""
10场比赛极限负载测试脚本
10 Matches Load Test Script

基于 backfill_full_history.py 的极限测试版本，仅处理前10个比赛
用于验证数据库创建和并发采集的稳定性
"""

import asyncio
import json
import logging
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("load_test_10_matches.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 设置环境变量
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/football_prediction')

class LoadTestRunner:
    """10场比赛负载测试运行器"""
    
    def __init__(self):
        self.collector = None
        self.test_results = {
            'total_matches': 10,
            'successful_matches': 0,
            'failed_matches': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
    
    async def setup(self):
        """设置测试环境"""
        logger.info("🔧 初始化测试环境...")
        
        # 初始化数据库
        from src.database.async_manager import initialize_database
        initialize_database()
        logger.info("✅ 数据库初始化完成")
        
        # 创建采集器
        from src.collectors.fotmob_api_collector import SuperGreedyFotMobCollector
        self.collector = SuperGreedyFotMobCollector()
        logger.info("✅ 采集器创建完成")
    
    async def get_test_matches(self) -> List[str]:
        """获取测试用的比赛ID"""
        # 使用一些知名的近期比赛ID进行测试
        test_match_ids = [
            "4044733", "4044734", "4044735", "4044736", "4044737",
            "4044738", "4044739", "4044740", "4044741", "4044742"
        ]
        
        logger.info(f"📋 选择测试比赛ID: {test_match_ids}")
        return test_match_ids
    
    async def run_load_test(self):
        """运行10场比赛负载测试"""
        logger.info("🚀 开始10场比赛极限负载测试...")
        
        self.test_results['start_time'] = datetime.now()
        
        # 获取测试比赛
        test_matches = await self.get_test_matches()
        
        # 创建并发任务
        tasks = [
            self.process_match(match_id)
            for match_id in test_matches
        ]
        
        # 执行并发任务
        logger.info(f"⚡ 开始并发处理 {len(tasks)} 场比赛...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        for i, result in enumerate(results):
            match_id = test_matches[i]
            
            if isinstance(result, Exception):
                logger.error(f"❌ 比赛 {match_id} 处理失败: {result}")
                self.test_results['failed_matches'] += 1
                self.test_results['errors'].append({
                    'match_id': match_id,
                    'error': str(result)
                })
            else:
                logger.info(f"✅ 比赛 {match_id} 处理成功")
                self.test_results['successful_matches'] += 1
        
        self.test_results['end_time'] = datetime.now()
        
        # 输出结果
        await self.print_test_results()
    
    async def process_match(self, match_id: str) -> bool:
        """处理单个比赛"""
        try:
            # 使用采集器获取比赛数据
            match_data = await self.collector.get_match_details(match_id)
            
            if not match_data:
                raise ValueError(f"无法获取比赛 {match_id} 的数据")
            
            # 保存到数据库
            from src.database.async_manager import get_db_session
            from sqlalchemy import text
            
            async with get_db_session() as session:
                # 检查比赛是否已存在
                existing = await session.execute(
                    text("SELECT id FROM matches WHERE fotmob_id = :match_id"),
                    {"match_id": match_id}
                )
                if existing.fetchone():
                    logger.info(f"⚠️ 比赛 {match_id} 已存在，跳过")
                    return True
                
                # 创建新比赛记录
                from src.database.models import Match
                match = Match(
                    fotmob_id=match_id,
                    home_team_name=match_data.get('home_team', {}).get('name', 'Unknown'),
                    away_team_name=match_data.get('away_team', {}).get('name', 'Unknown'),
                    match_date=datetime.now(),
                    status='completed'
                )
                
                session.add(match)
                await session.commit()
                
            logger.info(f"✅ 比赛 {match_id} 数据保存成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 处理比赛 {match_id} 时出错: {e}")
            raise
    
    async def print_test_results(self):
        """打印测试结果"""
        duration = self.test_results['end_time'] - self.test_results['start_time']
        
        logger.info("
" + "="*50)
        logger.info("📊 10场比赛负载测试结果报告")
        logger.info("="*50)
        logger.info(f"⏱️ 测试时间: {self.test_results['start_time']} - {self.test_results['end_time']}")
        logger.info(f"⏱️ 总耗时: {duration}")
        logger.info(f"📋 总比赛数: {self.test_results['total_matches']}")
        logger.info(f"✅ 成功处理: {self.test_results['successful_matches']}")
        logger.info(f"❌ 失败处理: {self.test_results['failed_matches']}")
        success_rate = (self.test_results['successful_matches'] / self.test_results['total_matches'] * 100)
        logger.info(f"📈 成功率: {success_rate:.1f}%")
        
        if self.test_results['errors']:
            logger.info("
❌ 错误详情:")
            for error in self.test_results['errors']:
                logger.info(f"  比赛 {error['match_id']}: {error['error']}")
        
        logger.info("="*50)

async def main():
    """主函数"""
    logger.info("🎯 启动10场比赛极限负载测试")
    
    try:
        # 创建测试运行器
        runner = LoadTestRunner()
        
        # 设置测试环境
        await runner.setup()
        
        # 运行测试
        await runner.run_load_test()
        
        logger.info("🎉 测试完成!")
        
    except Exception as e:
        logger.error(f"❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
