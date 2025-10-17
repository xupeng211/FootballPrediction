#!/usr/bin/env python3
"""
测试响应工具
"""

import pytest
from datetime import datetime


def test_success_response():
    """测试成功响应"""

    def success(data=None, message="Success"):
        """创建成功响应"""
        return {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

    resp = success({"id": 1})
    assert resp["status"] == "success"
    assert resp["data"]["id"] == 1
    assert "timestamp" in resp


def test_error_response():
    """测试错误响应"""

    def error(message, code=400):
        """创建错误响应"""
        return {
            "status": "error",
            "message": message,
            "code": code,
            "timestamp": datetime.now().isoformat(),
        }

    resp = error("Bad Request", 400)
    assert resp["status"] == "error"
    assert resp["message"] == "Bad Request"
    assert resp["code"] == 400


def test_created_response():
    """测试创建响应"""

    def created(data):
        """创建资源创建成功响应"""
        return {
            "status": "created",
            "message": "Resource created successfully",
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

    resp = created({"id": 123, "name": "Test"})
    assert resp["status"] == "created"
    assert resp["data"]["id"] == 123


def test_not_found_response():
    """测试未找到响应"""

    def not_found(resource="Resource"):
        """创建未找到响应"""
        return {
            "status": "not_found",
            "message": f"{resource} not found",
            "timestamp": datetime.now().isoformat(),
        }

    resp = not_found("User")
    assert resp["status"] == "not_found"
    assert "User not found" in resp["message"]


def test_validation_error_response():
    """测试验证错误响应"""

    def validation_error(errors):
        """创建验证错误响应"""
        return {
            "status": "validation_error",
            "message": "Validation failed",
            "errors": errors,
            "timestamp": datetime.now().isoformat(),
        }

    errors = {"email": "Invalid email format", "age": "Must be a number"}
    resp = validation_error(errors)
    assert resp["status"] == "validation_error"
    assert resp["errors"]["email"] == "Invalid email format"


def test_paginated_response():
    """测试分页响应"""

    def paginated(data, page, per_page, total):
        """创建分页响应"""
        return {
            "status": "success",
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            },
            "timestamp": datetime.now().isoformat(),
        }

    items = [{"id": i} for i in range(1, 11)]
    resp = paginated(items, 1, 10, 25)
    assert resp["pagination"]["page"] == 1
    assert resp["pagination"]["total"] == 25
    assert resp["pagination"]["pages"] == 3
