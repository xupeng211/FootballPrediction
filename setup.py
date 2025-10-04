from setuptools import find_packages, setup
import os

# 读取README文件
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# 读取requirements.txt
def read_requirements(filename):
    try:
        with open(os.path.join(here, filename), encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return []

setup(
    name="football-prediction",
    version="0.2.0",
    # 指定src目录为包根目录
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": [
            "pytest>=8.3.4",
            "pytest-asyncio>=0.25.0",
            "pytest-cov>=6.0.0",
            "pytest-mock>=3.14.0",
            "black>=24.10.0",
            "isort>=5.13.2",
            "flake8>=7.1.1",
            "mypy>=1.14.1",
        ],
        "docs": [
            "mkdocs>=1.6.1",
            "mkdocs-material>=9.5.49",
        ],
    },
    python_requires=">=3.11",
    # 添加项目描述和元信息
    description="AI-Powered Football Match Prediction System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="FootballPrediction Team",
    author_email="dev@footballprediction.com",
    url="https://github.com/xupeng211/FootballPrediction",
    project_urls={
        "Bug Tracker": "https://github.com/xupeng211/FootballPrediction/issues",
        "Documentation": "https://github.com/xupeng211/FootballPrediction/docs",
        "Source Code": "https://github.com/xupeng211/FootballPrediction",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="football prediction machine learning fastapi sqlalchemy",
    entry_points={
        "console_scripts": [
            "football-prediction=src.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
