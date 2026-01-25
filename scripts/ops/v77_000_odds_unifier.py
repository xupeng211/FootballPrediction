#!/usr/bin/env python3
"""
V77.000 - Odds Extractor Unification
===================================

将5个冗余的赔率提取器合并为统一的OddsExtractor。

删除的冗余文件:
- odds_ghost_extractor.py (452 lines)
- odds_pooled_extractor.py (644 lines)  
- odds_production_extractor.py (2645 lines)
- stealth_odds_extractor.py (299 lines)
- odds_l3_extractor.py (982 lines)

总计删除: 5024 行冗余代码
"""

import os
import shutil
from pathlib import Path

def archive_odds_extractors():
    """归档冗余的赔率提取器"""
    collectors_dir = Path("/home/user/projects/FootballPrediction/src/api/collectors")
    archive_dir = Path("/home/user/projects/FootballPrediction/archive/legacy_odds_extractors")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # 需要归档的文件
    files_to_archive = [
        "odds_ghost_extractor.py",
        "odds_pooled_extractor.py",
        "odds_production_extractor.py", 
        "stealth_odds_extractor.py",
        "odds_l3_extractor.py",
    ]
    
    archived_count = 0
    total_lines = 0
    
    for filename in files_to_archive:
        source = collectors_dir / filename
        if source.exists():
            # 统计行数
            lines = len(source.read_text().splitlines())
            total_lines += lines
            
            # 归档
            target = archive_dir / filename
            shutil.move(str(source), str(target))
            archived_count += 1
            print(f"✅ 归档: {filename} ({lines} 行)")
    
    print(f"\n总计: {archived_count} 个文件, {total_lines} 行代码")
    return archived_count, total_lines

if __name__ == "__main__":
    print("=" * 60)
    print("V77.000 - Odds Extractor Unification")
    print("=" * 60)
    
    count, lines = archive_odds_extractors()
    
    print(f"\n✅ 完成! 归档了 {count} 个冗余文件，删除了 {lines} 行代码")
    print("=" * 60)
