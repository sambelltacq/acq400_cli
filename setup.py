#!/usr/bin/env python3
"""
Setup script for acq400_cli package.
"""

from setuptools import setup, find_packages
import os

def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "ACQ400 Command Line Interface"


def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="acq400_cli",
    version="0.1.0",
    author="D-tacq",
    author_email="support@d-tacq.co.uk",
    description="ACQ400 Command Line Interface",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="http://eigg/GIT/Software/?p=acq400_cli",
    packages=find_packages(),
    classifiers=[],
    python_requires=">=3.6",
    install_requires=read_requirements(),
    extras_require={},
    entry_points={
        "console_scripts": [
            "acq400_cli=acq400_cli.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)