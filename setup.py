import pathlib

from setuptools import find_packages, setup

HOME_DIR = pathlib.Path(__file__).parent

# The text of the README file
README = (HOME_DIR / "README.md").read_text()

setup(
    name="bigtesty",
    version="0.1.0",
    entry_points='''
        [console_scripts]
        bigtesty=bigtesty.cli.main:run
    ''',
    install_requires=[
        "pulumi-gcp==6.67.0",
        "google-cloud-bigquery==3.7.0",
        "typer[all]==0.9.0",
        "pytest==7.2.1",
        "deepdiff==6.3.0",
        "toolz==0.12.0"
    ],
    description="BigTesty is an integration testing framework for BigQuery",
    long_description=README,
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
    python_requires='>=3.9.18',
)