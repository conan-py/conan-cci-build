"""
  POCO types
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass(frozen=True)
class PackageRef:
    """
        A reference to a package to be built.
    """
    name: str
    """ the name of the package to be built"""
    version: Optional[str] = None
    """ the version of the package to build """


@dataclass(frozen=True)
class ProfileRule:
    """ A rule to determine whether a profile should be included in a build """
    include: bool
    pattern: str


@dataclass(frozen=True)
class PackageEntry(PackageRef):
    """ A description of a single package to build, that will be uploaded to the Conan jFrog Artifactory repository """

    profiles: List[ProfileRule] = field(default_factory=list)
    """ The list of profiles that this package should be built for """
