from typing import TypedDict


class VersionInfo(TypedDict):
    """

    """
    folder: str


class Config(TypedDict):
    """
        The structure of a `config.yml` in a conan centre index
    """
    versions: dict[str, VersionInfo]
