from setuptools import find_packages, setup

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
    packages=find_packages(),
)
