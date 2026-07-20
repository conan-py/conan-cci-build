"""
    Trivial setup.py to package for publishing the module to pypi.
"""
from setuptools import setup, find_packages

setup(
    name="conan-cci-build",
    version="0.1.0",
    package_dir={
        "": "src",
        "cci_build_extensions": "extensions",
    },
    packages=find_packages(where="src") + [
        "cci_build_extensions",
        "cci_build_extensions.commands",
    ],
    python_requires=">=3.13",
    install_requires=[
        "conan>=2.25,<3.0",
        "packaging>=26.2",
    ],
    package_data={
        "cci_build_extensions.commands": ["cmd_cci_build.py"],
    },
    entry_points={
        "console_scripts": [
            "conan-cci-build-install = cci_build.installer:main",
        ],
    },
)
