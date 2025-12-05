#!/usr/bin/env python3
"""Football Prediction SDK 安装配置."""

import os

from setuptools import find_packages, setup


# 读取README文件
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, encoding="utf-8") as f:
            return f.read()
    return "Football Prediction Python SDK"


# 读取requirements文件
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        with open(requirements_path, encoding="utf-8") as f:
            return [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    return ["requests>=2.25.0", "python-dateutil>=2.8.0"]


setup(
    name="football-prediction-sdk",
    version="1.0.0",
    author="Claude Code",
    author_email="support@football-prediction.com",
    description="足球比赛结果预测系统 - 官方Python SDK",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/football-prediction/python-sdk",
    project_urls={
        "Documentation": "https://docs.football-prediction.com/sdk/python",
        "Source": "https://github.com/football-prediction/python-sdk",
        "Tracker": "https://github.com/football-prediction/python-sdk/issues",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.10",
            "pytest-asyncio>=0.18",
            "ruff>=0.1.0",
            "mypy>=0.812",
            "pre-commit>=2.0",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=0.5",
            "myst-parser>=0.15",
        ],
        "performance": [
            "aiohttp>=3.8.0",
            "uvloop>=0.16.0",
        ],
    },
    py_modules=["football_prediction_sdk"],
    entry_points={
        "console_scripts": [
            "football-prediction=football_prediction_sdk.cli:main",
        ],
    },
    keywords=[
        "football",
        "soccer",
        "prediction",
        "api",
        "sdk",
        "machine learning",
        "sports analytics",
        "prediction model",
        "betting",
        "odds",
    ],
    include_package_data=True,
    zip_safe=False,
)
