from pathlib import Path
from typing import TypedDict, Optional, Tuple

import os
import yaml
from pathlib import Path
from packaging.version import parse as parse_version

from cci_build.error.exception import RecipeNotFoundError
from cci_build.model.cci.conandata.types import ConanDataLayout
from cci_build.model.cci.config.types import Config, VersionInfo


def make_cci_recipie_package_config_filename(recipe_dir: Path) -> Path:
    return recipe_dir / "config.yml"


def make_cci_recipie_package_conanfile_filename(conanfile_folder_name, recipe_dir: Path) -> Path:
    return recipe_dir / conanfile_folder_name / "conanfile.py"


def make_cci_recipie_package_conandata_filename(conanfile_folder_name, recipe_dir: Path) -> Path:
    return recipe_dir / conanfile_folder_name / "conandata.yml"


def make_cci_recipe_package_path(cci_root: Path, package_name: str) -> Path:
    return Path(cci_root) / "recipes" / package_name


def read_package_config_yaml(config_path: Path) -> Config:
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    return config_data


def read_conandata_yaml(config_path: Path) -> ConanDataLayout:
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
        if config_data.get("sources"):
            return config_data
    return None


def find_cci_conanfile(cci_root: Path, package_name: str, version: Optional[str]) -> Tuple[str, Path]:
    """
        Finds the exact conanfile.py path for a given package version
        based on standard Conan Center Index (CCI) layout specifications.

        :argument cci_root: The root directory of the local copy of a CCI.
        :argument package_name: The name of the package to find.
        :argument version: An optional version of the package to find, otherwise None will be translated to latest.

        Return the conanfile.py path and the exact version to be built.
    """
    recipe_dir = make_cci_recipe_package_path(cci_root, package_name)
    config_path = make_cci_recipie_package_config_filename(recipe_dir)

    if config_path.exists():
        config_data = read_package_config_yaml(config_path)

        # Standard CCI layout groups everything under the 'versions' node
        v, info = find_config_version(config_data.get("versions", {}), version)
        if v and info and "folder" in info:

            # Pull the targeted folder (frequently 'all', or specific folders like '1.x.x')
            conanfile_folder_name = info.get("folder")
            conanfile_path = make_cci_recipie_package_conanfile_filename(conanfile_folder_name, recipe_dir)
            if conanfile_path.exists():

                conandata_path = make_cci_recipie_package_conandata_filename(conanfile_folder_name, recipe_dir)
                if conandata_path.exists():
                    conandata = read_conandata_yaml(conandata_path)
                    if conandata:
                        return v, conanfile_path
                    raise FileNotFoundError(f"Package '{package_name}/{v}' not found in conandata")
                raise FileNotFoundError(f"Expected conandata.yml missing at: {conandata_path}")
            raise FileNotFoundError(f"Expected conanfile.py missing at: {conanfile_path}")
        raise RecipeNotFoundError(f"Recipe '{package_name}/{version if not None else 'latest'}' not found config.yml.")
    raise RecipeNotFoundError(f"Package '{package_name}' or its config.yml not found in CCI path.")


def find_config_version(
        versions: dict[str, VersionInfo],
        version: Optional[str]) -> Tuple[Optional[str], Optional[VersionInfo]]:
    """
        Given a `Config.yml` set of versions available, select the version information
        for that version. If no version is specified, then select the latest/newest version.

        Use standard PEP 440 version parsing rules to compare version numbers.

        return A valid ConanCentreVersionInfo or None if there is no matching version
    """
    if version:
        specific_version = versions.get(version)
        return (version, specific_version) if specific_version else (None, None,)
    else:
        max_version = max(versions.keys(), key=parse_version)
        return (max_version, versions.get(max_version),) if max_version else (None, None,)
