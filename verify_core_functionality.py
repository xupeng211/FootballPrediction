#!/usr/bin/env python3
"""
核心功能验证脚本
Core Functionality Verification Script

用于验证当前版本的核心预测功能是否正常工作。
"""

import asyncio
import json
import sys
from datetime import datetime
from fastapi.testclient import TestClient
from src.main import app

def test_core_functionality():
    """测试核心功能"""
    print("🔍 开始验证核心预测功能...")

    client = TestClient(app)
    results = {
        "总测试数": 0,
        "通过数": 0,
        "失败数": 0,
        "详情": []
    }

    # 测试1: 健康检查
    print("\n1️⃣ 测试健康检查端点...")
    results["总测试数"] += 1
    try:
        response = client.get("/api/v1/predictions/health")
        if response.status_code == 200:
            results["通过数"] += 1
            results["详情"].append("✅ 健康检查: 通过")
            print(f"   ✅ 健康检查: {response.json()}")
        else:
            results["失败数"] += 1
            results["详情"].append(f"❌ 健康检查: 状态码 {response.status_code}")
    except Exception as e:
        results["失败数"] += 1
        results["详情"].append(f"❌ 健康检查: 异常 {str(e)}")

    # 测试2: 获取预测
    print("\n2️⃣ 测试获取预测...")
    results["总测试数"] += 1
    try:
        response = client.get("/api/v1/predictions/12345")
        if response.status_code == 200:
            data = response.json()
            results["通过数"] += 1
            results["详情"].append("✅ 获取预测: 通过")
            print(f"   ✅ 获取预测: {data}")
        else:
            results["失败数"] += 1
            results["详情"].append(f"❌ 获取预测: 状态码 {response.status_code}")
    except Exception as e:
        results["失败数"] += 1
        results["详情"].append(f"❌ 获取预测: 异常 {str(e)}")

    # 测试3: 创建预测
    print("\n3️⃣ 测试创建预测...")
    results["总测试数"] += 1
    try:
        response = client.post("/api/v1/predictions/12345/predict")
        if response.status_code == 201:
            data = response.json()
            results["通过数"] += 1
            results["详情"].append("✅ 创建预测: 通过")
            print(f"   ✅ 创建预测: {data}")
        else:
            results["失败数"] += 1
            results["详情"].append(f"❌ 创建预测: 状态码 {response.status_code}")
    except Exception as e:
        results["失败数"] += 1
        results["详情"].append(f"❌ 创建预测: 异常 {str(e)}")

    # 测试4: 批量预测
    print("\n4️⃣ 测试批量预测...")
    results["总测试数"] += 1
    try:
        batch_request = {
            "match_ids": [12345, 12346, 12347],
            "model_version": "default"
        }
        response = client.post("/api/v1/predictions/batch", json=batch_request)
        if response.status_code == 200:
            data = response.json()
            results["通过数"] += 1
            results["详情"].append("✅ 批量预测: 通过")
            print(f"   ✅ 批量预测: 成功 {data.get('success_count', 0)}/{data.get('total', 0)}")
        else:
            results["失败数"] += 1
            results["详情"].append(f"❌ 批量预测: 状态码 {response.status_code}")
    except Exception as e:
        results["失败数"] += 1
        results["详情"].append(f"❌ 批量预测: 异常 {str(e)}")

    # 测试5: 验证预测
    print("\n5️⃣ 测试验证预测...")
    results["总测试数"] += 1
    try:
        response = client.post("/api/v1/predictions/12345/verify?actual_result=home")
        if response.status_code == 200:
            data = response.json()
            results["通过数"] += 1
            results["详情"].append("✅ 验证预测: 通过")
            print(f"   ✅ 验证预测: {data}")
        else:
            results["失败数"] += 1
            results["详情"].append(f"❌ 验证预测: 状态码 {response.status_code}")
    except Exception as e:
        results["失败数"] += 1
        results["详情"].append(f"❌ 验证预测: 异常 {str(e)}")

    # 输出结果总结
    print("\n" + "="*50)
    print("📊 核心功能验证结果")
    print("="*50)
    print(f"总测试数: {results['总测试数']}")
    print(f"通过数: {results['通过数']}")
    print(f"失败数: {results['失败数']}")
    print(f"成功率: {results['通过数']/results['总测试数']*100:.1f}%")

    print("\n📋 详细结果:")
    for detail in results["详情"]:
        print(f"   {detail}")

    # 整体评估
    success_rate = results['通过数']/results['总测试数']
    if success_rate >= 0.8:
        print("\n🎉 核心功能验证: 优秀！系统已准备好进行用户测试")
        return True
    elif success_rate >= 0.6:
        print("\n✅ 核心功能验证: 良好！系统基本可用，建议修复剩余问题")
        return True
    else:
        print("\n⚠️  核心功能验证: 需要改进！系统尚未达到基本可用标准")
        return False

if __name__ == "__main__":
    success = test_core_functionality()
    sys.exit(0 if success else 1)