"""Setup for edx-sga XBlock."""

import os
from setuptools import setup, find_packages

setup(
    name='edx-score-grade-api',
    version='0.1.23',
    description='edx-score-grade-api Score Grade API',
    license='Affero GNU General Public License v3 (GPLv3)',
    url="https://github.com/kotky/edx-score-api",
    author="Josip Kotarac",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "django>=1.8",
        'djangorestframework>=3.2.0',
    ],
)
