from typing import Optional, List

import pytest

from cci_build.package_parser import parse_profile_rule
from cci_build.profile_matcher import include_rules


class TestProfileMatcher:

    @pytest.mark.parametrize(
        "rules, profile, result",
        [
            (None, "abc", True),  # no profiles listed, default is a match
            ([], "abc", True),  # empty package list
            (["!linux-clang-x64-debug", ], "abc", False),
            (["!linux-clang-x64-debug", "*"], "abc", True),
            (["!linux-clang*", "*"], "linux-clang-x64-debug", False),
            (["!linux-clang*", "*"], "windows-clang-x64-debug", True),
            (["*"], "windows-clang-x64-debug", True),
            (["android-clang-x64-debug", "linux-clang-x64-debug"], "windows-clang-x64-debug", False),
        ])
    def test_bulk_generation(self, rules: Optional[List[str]], profile: str, result: bool):
        matches = include_rules([parse_profile_rule(r) for r in rules] if rules is not None else [], profile)
        assert matches == result
