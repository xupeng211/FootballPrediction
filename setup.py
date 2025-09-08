"""Setup configuration for FootballPrediction"""

from setuptools import find_packages, setup

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

setup(
    name="footballprediction",
    version="0.1.0",
    description="基于机器学习的足球比赛结果预测系统，覆盖全球主要赛事",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    package_dir={"": "."},
    install_requires=requirements,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
