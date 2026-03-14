#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Octopus_mem - AI Agent记忆系统
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="octopus-mem",
    version="0.1.0",
    author="AlataChan",
    author_email="alata@example.com",
    description="AI Agent记忆系统 - Skill + Memory索引架构",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AlataChan/Octopus_mem",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "black>=23.0.0",
            "flake8>=6.0.0",
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
        "semantic": [
            "sentence-transformers>=2.2.0",
            "chromadb>=0.4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "octopus-mem=octopus_mem.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)