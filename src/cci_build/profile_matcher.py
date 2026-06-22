from fnmatch import fnmatch
from typing import Optional, List

from cci_build.model.settings.types import ProfileRule, PackageEntry


def include( pkg: PackageEntry, profile: str) -> bool:
    return include_rules(pkg.profiles, profile)

def include_rules(rules : List[ProfileRule], profile: str) -> bool:
    """
        Given a host profile, check if a given package should be built.

        Rules:
           - no listed profiles, means match all profiles
           - an exclamation prefix on a rule excludes those profiles
    """
    if not rules:
        # if no filter rules are provided, then the package is built for
        # all profiles, so it is a match.
        return True

    # Find the first matching rule, or default to do not build
    for rule in rules:
        # check if the rule is a negative check (i.e. do not built this package).
        #
        if not rule.include:
            if fnmatch(profile, rule.pattern):
                return False # a positive match means that the package is not built
        elif fnmatch(profile, rule.pattern):
            return True # the rule positively matches the profile, so the package is built

    return False
