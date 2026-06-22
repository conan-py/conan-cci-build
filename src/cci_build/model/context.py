from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Context:
    """
        A top level state to hold command line arguments and program state.
    """

    cci_root: Path
    """ A filesystem Path to the root of the CCI project """

    remote: str
    """ The name of a configured (and authenticated) of a jFrog Artifactory package repository to use"""

    build_profile: str
    """ The profile used for building the package """

    host_profile: str

    packages_filename: str
