"""
    POCO models describing data in a CCI 'config.yml' file.


    example:
       versions:
          "1.2.3":
            folder: "all"
          "2.0.0":
            folder: "all"
          "old_version":
            folder: "1.x"


    see:
      - https://github.com/conan-io/conan-center-index/blob/master/docs/adding_packages/folders_and_files.md
"""
from typing import TypedDict


class VersionInfo(TypedDict):
    """
       Info about a version in a 'config.yml' file
    """
    folder: str
    """ The folder name of the version """


class Config(TypedDict):
    """
        The structure of a `config.yml` in a conan centre index
    """
    versions: dict[str, VersionInfo]
