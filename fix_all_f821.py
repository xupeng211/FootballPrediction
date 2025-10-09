#!/usr/bin/env python3
"""
批量修复所有 F821 (undefined name) 错误
"""

import os
import re
import subprocess
from pathlib import Path


def add_import(content, import_statement):
    """添加导入语句到文件内容"""
    lines = content.split("\n")

    # 检查是否已经存在该导入
    for line in lines:
        if import_statement in line:
            return content

    # 找到合适的插入位置
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.strip().startswith(("import ", "from ")):
            insert_pos = i
            break

    # 插入新的导入
    lines.insert(insert_pos, import_statement)
    return "\n".join(lines)


def fix_undefined_names_in_file(filepath):
    """修复单个文件中的未定义名称"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 定义常见未定义名称和对应的导入
        name_to_import = {
            # 标准库
            "time": "import time",
            "asyncio": "import asyncio",
            "timedelta": "from datetime import timedelta",
            "datetime": "from datetime import datetime",
            "date": "from datetime import date",
            "timezone": "from datetime import timezone",
            "utcnow": "from datetime import datetime, timezone",
            "json": "import json",
            "re": "import re",
            "os": "import os",
            "sys": "import sys",
            "pathlib": "from pathlib import Path",
            "Path": "from pathlib import Path",
            "collections": "import collections",
            "defaultdict": "from collections import defaultdict",
            "Counter": "from collections import Counter",
            "logging": "import logging",
            "logger": "import logging",
            "subprocess": "import subprocess",
            "hashlib": "import hashlib",
            "hmac": "import hmac",
            "base64": "import base64",
            "secrets": "import secrets",
            "uuid": "import uuid",
            "random": "import random",
            "math": "import math",
            "statistics": "import statistics",
            "decimal": "from decimal import Decimal",
            "fractions": "from fractions import Fraction",
            "itertools": "import itertools",
            "functools": "import functools",
            "operator": "import operator",
            "copy": "import copy",
            "pickle": "import pickle",
            "csv": "import csv",
            "xml": "import xml",
            "yaml": "import yaml",
            "configparser": "import configparser",
            "argparse": "import argparse",
            "threading": "import threading",
            "queue": "import queue",
            "multiprocessing": "import multiprocessing",
            "concurrent": "import concurrent",
            "socket": "import socket",
            "urllib": "import urllib",
            "http": "import http",
            "email": "import email",
            "mimetypes": "import mimetypes",
            "tempfile": "import tempfile",
            "shutil": "import shutil",
            "glob": "import glob",
            "fnmatch": "import fnmatch",
            # SQLAlchemy
            "create_engine": "from sqlalchemy import create_engine",
            "select": "from sqlalchemy import select",
            "update": "from sqlalchemy import update",
            "delete": "from sqlalchemy import delete",
            "insert": "from sqlalchemy import insert",
            "and_": "from sqlalchemy import and_",
            "or_": "from sqlalchemy import or_",
            "not_": "from sqlalchemy import not_",
            "func": "from sqlalchemy import func",
            "text": "from sqlalchemy import text",
            "Column": "from sqlalchemy import Column",
            "Integer": "from sqlalchemy import Integer",
            "String": "from sqlalchemy import String",
            "Float": "from sqlalchemy import Float",
            "Boolean": "from sqlalchemy import Boolean",
            "DateTime": "from sqlalchemy import DateTime",
            "Date": "from sqlalchemy import Date",
            "ForeignKey": "from sqlalchemy import ForeignKey",
            "Table": "from sqlalchemy import Table",
            "MetaData": "from sqlalchemy import MetaData",
            "Session": "from sqlalchemy.orm import Session",
            "sessionmaker": "from sqlalchemy.orm import sessionmaker",
            "relationship": "from sqlalchemy.orm import relationship",
            "declarative_base": "from sqlalchemy.orm import declarative_base",
            # Pandas
            "pd": "import pandas as pd",
            "DataFrame": "from pandas import DataFrame",
            "Series": "from pandas import Series",
            "read_csv": "from pandas import read_csv",
            "read_json": "from pandas import read_json",
            "read_excel": "from pandas import read_excel",
            # NumPy
            "np": "import numpy as np",
            "array": "from numpy import array",
            "arange": "from numpy import arange",
            "linspace": "from numpy import linspace",
            "zeros": "from numpy import zeros",
            "ones": "from numpy import ones",
            "random": "from numpy import random",
            # 测试相关
            "pytest": "import pytest",
            "Mock": "from unittest.mock import Mock",
            "MagicMock": "from unittest.mock import MagicMock",
            "AsyncMock": "from unittest.mock import AsyncMock",
            "patch": "from unittest.mock import patch",
            "mock": "from unittest import mock",
            # FastAPI
            "FastAPI": "from fastapi import FastAPI",
            "APIRouter": "from fastapi import APIRouter",
            "HTTPException": "from fastapi import HTTPException",
            "Depends": "from fastapi import Depends",
            "Query": "from fastapi import Query",
            "Path": "from fastapi import Path",
            "Body": "from fastapi import Body",
            "Header": "from fastapi import Header",
            "Cookie": "from fastapi import Cookie",
            "Form": "from fastapi import Form",
            "File": "from fastapi import File",
            "UploadFile": "from fastapi import UploadFile",
            "Request": "from fastapi import Request",
            "Response": "from fastapi import Response",
            "status": "from fastapi import status",
            # Pydantic
            "BaseModel": "from pydantic import BaseModel",
            "Field": "from pydantic import Field",
            "validator": "from pydantic import validator",
            "root_validator": "from pydantic import root_validator",
            # Redis
            "redis": "import redis",
            "Redis": "from redis import Redis",
            # 项目特定
            "DatabaseManager": "from src.database.connection import DatabaseManager",
            "RepoConfig": "from src.database.models.config import RepoConfig",
            "SystemMonitor": "from src.monitoring.system_monitor import SystemMonitor",
            "BaseService": "from src.services.base import BaseService",
            "get_logger": "from src.core.logging import get_logger",
            "KeyManager": "from src.utils.key_manager import KeyManager",
            "ErrorHandler": "from src.core.error_handler import ErrorHandler",
        }

        # 检查文件中使用了哪些未定义的名称
        imports_to_add = set()

        # 获取当前文件的错误
        result = subprocess.run(
            ["ruff", "check", "--select=F821", filepath, "--output-format=concise"],
            capture_output=True,
            text=True,
        )

        for line in result.stdout.split("\n"):
            if line:
                # 提取未定义的名称
                match = re.search(r"Undefined name `([^`]+)`", line)
                if match:
                    undefined_name = match.group(1)
                    if undefined_name in name_to_import:
                        imports_to_add.add(name_to_import[undefined_name])

        # 添加导入
        for import_stmt in sorted(imports_to_add):
            content = add_import(content, import_stmt)

        # 写回文件
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """主函数"""
    # 获取所有有 F821 错误的文件
    result = subprocess.run(
        ["ruff", "check", "--select=F821", "--output-format=concise"],
        capture_output=True,
        text=True,
    )

    files = set()
    for line in result.stdout.split("\n"):
        if line:
            filepath = line.split(":")[0]
            if os.path.exists(filepath):
                files.add(filepath)

    print(f"找到 {len(files)} 个需要修复的文件")
    print("=" * 60)

    fixed_count = 0
    for filepath in sorted(files):
        print(f"\n处理: {filepath}")
        if fix_undefined_names_in_file(filepath):
            print("  ✅ 已修复")
            fixed_count += 1
        else:
            print("  - 无需修复")

    print("=" * 60)
    print(f"\n✅ 修复了 {fixed_count} 个文件")

    # 验证修复结果
    print("\n验证修复结果...")
    result = subprocess.run(
        ["ruff", "check", "--select=F821"], capture_output=True, text=True
    )

    remaining = (
        len([l for l in result.stdout.split("\n") if l]) if result.stdout.strip() else 0
    )
    print(f"剩余 {remaining} 个 F821 错误")

    if remaining > 0:
        print("\n前 20 个错误:")
        errors = result.stdout.split("\n")[:20]
        for error in errors:
            if error:
                print(f"  {error}")


if __name__ == "__main__":
    main()
