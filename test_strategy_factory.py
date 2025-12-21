#!/usr/bin/env python3
"""测试策略工厂功能"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.core.strategy_factory import (
        get_strategy_engine, get_strategy_mode, get_strategy_info,
        switch_to_live_mode, switch_to_sandbox_mode,
        is_live_mode, is_sandbox_mode
    )

    print("🧪 测试策略工厂功能")
    print("=" * 50)

    # 测试初始模式
    print(f"📋 当前模式: {get_strategy_mode()}")
    print(f"🧪 沙盒模式: {is_sandbox_mode()}")
    print(f"🔥 实战模式: {is_live_mode()}")

    # 获取策略信息
    info = get_strategy_info()
    print(f"\n📊 策略信息:")
    print(f"   模式: {info['mode']}")
    print(f"   实战模式: {info['is_live']}")
    print(f"   最大单场: {info['risk_parameters']['max_single_bet_pct']:.1%}")
    print(f"   每日限制: {info['risk_parameters']['max_daily_bets']}次")

    # 测试模式切换
    print(f"\n🔄 测试模式切换...")
    
    switch_to_live_mode()
    print(f"切换后模式: {get_strategy_mode()} (实战: {is_live_mode()})")
    
    switch_to_sandbox_mode()
    print(f"切换后模式: {get_strategy_mode()} (沙盒: {is_sandbox_mode()})")

    # 测试策略引擎
    print(f"\n⚙️ 测试策略引擎...")
    engine = get_strategy_engine()
    print(f"引擎模式: {engine.mode.value}")
    print(f"资金状态: {engine.portfolio.current_capital}")

    print("\n✅ 策略工厂测试完成!")

except ImportError as e:
    print(f"❌ 导入错误: {e}")
except Exception as e:
    print(f"❌ 测试失败: {e}")
