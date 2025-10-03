from setuptools import find_packages, setup
import os

setup(
    name = os.getenv("SETUP_NAME_4"),
    version="0.1.0",
    # 指定src目录为包根目录
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        # 依赖在requirements.txt中定义
    ],
    python_requires = os.getenv("SETUP_PYTHON_REQUIRES_11"),
    # 添加项目描述和元信息
    description = os.getenv("SETUP_DESCRIPTION_12"),
    long_description_content_type = os.getenv("SETUP_LONG_DESCRIPTION_CONTENT_TYPE_14"),
    author = os.getenv("SETUP_AUTHOR_15"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
)
