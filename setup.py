#!/usr/bin/env python
import os

from setuptools import find_packages, setup

requirements = [
    "sqlalchemy",
]
with open("requirements_test.txt", encoding="utf-8") as f:
    for line in f:
        if "txt" not in line and "#" not in line:
            requirements.append(line)

with open("version", encoding="utf-8") as f:
    __version__ = f.read()

setup(
    author="Jan Bouwhuis",
    name="ha-elro-connects",
    version=__version__,
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=requirements,
    license="MIT license",
    url="https://github.com/jbouwh/ha-elro-connects",
    author_email="jan@jbsoft.nl",
    description="Add Elro Connects alarm devices to Home Assistant",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pytest",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={
        "pytest11": ["homeassistant = pytest_homeassistant_custom_component.plugins"]
    },
)
