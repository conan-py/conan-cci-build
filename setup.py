from setuptools import setup, find_packages

setup(
    name="conan-cci-build",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.13",
    install_requires=["conan>=2.25,<3.0"],

    entry_points={
        "console_scripts": [
            "conan-cci-build-install = cci_build.installer:main",
        ],
    },
)
