import os
import pathlib

from setuptools import find_packages, setup

HOME_DIR = pathlib.Path(__file__).parent
path = HOME_DIR / "README.md"

# The text of the README file
long_desc = ""
if os.path.isfile(path):
    long_desc = path.read_text()

setup(
    name="bigtesty",
    version="0.1.0a8",
    entry_points='''
        [console_scripts]
        bigtesty=bigtesty.cli.main:run
    ''',
    install_requires=[
        "pulumi-gcp==7.24.0",
        "google-cloud-bigquery==3.23.1",
        "typer[all]==0.12.3",
        "pytest==8.2.1",
        "deepdiff==7.0.1",
        "toolz==0.12.1"
    ],
    description="BigTesty is an integration testing framework for BigQuery",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    url="https://github.com/tosun-si/bigtesty",
    author="Mazlum TOSUN",
    author_email="mazlum.tosun@gmail.com",
    packages=find_packages(),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"
    ],
    python_requires='>=3.9.19',
)
