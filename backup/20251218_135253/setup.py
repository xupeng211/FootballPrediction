from setuptools import find_packages, setup

setup(
    name="football-prediction",
    version="0.1.0",
    # 指定src目录为包根目录
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        # 依赖在requirements.txt中定义
    ],
    python_requires=">=3.11",
    # 添加项目描述和元信息
    description="Football Prediction System with AI Analysis",
    long_description_content_type="text/markdown",
    author="FootballPrediction Team",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
)
