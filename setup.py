#!/usr/bin/env python3
"""Setup configuration for Dialectus CLI."""

from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="dialectus-cli",
    version="0.1.0",
    description="Command-line interface for the Dialectus AI debate system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/psarno/dialectus-cli",
    author="psarno",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="ai, debate, cli, artificial intelligence, argumentation",
    packages=find_packages(),
    python_requires=">=3.10, <4",
    install_requires=[
        "rich>=14.1.0",
        "click>=8.2.1", 
        "pydantic>=2.11.0",
        "pyyaml>=6.0.0",
    ],
    entry_points={
        "console_scripts": [
            "dialectus=cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/psarno/dialectus-cli/issues",
        "Source": "https://github.com/psarno/dialectus-cli/",
    },
)