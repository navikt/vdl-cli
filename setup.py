from setuptools import find_packages, setup

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="vdl-cli",
    version="0.1.21",
    description=("CLI tool for helping with daily tasks in Virksomhetsdatalaget"),
    packages=find_packages(include=("vdc/*,")),
    package_data={"vdc": ["banner.txt"]},
    author="NAV IT Virksomhetsdatalaget",
    author_email="virksomhetsdatalaget@nav.no",
    url="https://github.com/navikt/vdl-regnskapsdata/tree/main/vdl-cli",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "click",
        "pyyaml",
        "jinja2",
        "alive-progress",
        "snowflake-connector-python[secure-local-storage,pandas]>=3.0.0",
        "xlsxwriter",
    ],
    extras_require={
        "all": [],
        "dev": [
            "black",
            "isort",
            "pytest",
        ],
    },
    python_requires=">=3.11",
    entry_points="""
        [console_scripts]
        vdc=vdc.main:cli
        o=vdc.main:open
    """,
)
