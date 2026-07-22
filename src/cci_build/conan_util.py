"""
    Miscellaneous Conan utilities
"""
from typing import Optional

from conan.api.model import RecipeReference, Remote, ListPattern, PackagesList
from conan.internal.errors import NotFoundException

from cci_build.conan_client import ConanClient


def make_revision(ref: RecipeReference) -> str:
    """
        Make a conan search revision based on a recipe reference.
    """
    pattern_str = f"{ref.name}/{ref.version if ref.version else '*'}"
    return pattern_str + (f"@{ref.user}/{ref.channel}" if ref.user and ref.channel else "#*")


def list_select(conan: ConanClient, search_pattern: ListPattern, remote: Optional[Remote]) -> Optional[PackagesList]:
    """
        Select a list of conan recipes.
    """
    try:
        return conan.api.list.select(search_pattern, remote=remote)
    except NotFoundException:
        # Eat the exception (the specific error is not reported)
        return None
