from io import StringIO
from typing import List

import pytest

from cci_build.model.settings.types import PackageEntry, ProfileRule
from cci_build.package_parser import parse_lines


class TestParsePackageList:
    """
        Test that the list of packages from the conan centre index (CCI) that are
        to be built can be parsed.

        The input file is a line-based set of packages, with optional versions,
        conan profiles and build options
    """

    @pytest.mark.parametrize(
        "input_str, expected_config",
        [
            ("", []),
            (
                    """
                    
                    # This is a comment
                    
                    """,
                    []
            ),
            ("# comment", []),
            (" # comment", []),
            ("#", []),
            ("bob", [PackageEntry(name="bob")]),
            ("bob/1.2.3", [PackageEntry(name="bob", version="1.2.3")]),
            ("bob/1.2.3 profiles=linux*",
             [PackageEntry("bob", version="1.2.3", profiles=[ProfileRule(include=True, pattern="linux*")])]),

            ("bob/1.2.3 p=linux*",
             [PackageEntry("bob", version="1.2.3", profiles=[ProfileRule(include=True, pattern="linux*")])]),

            ("bob/1.2.3 p=!linux*",
             [PackageEntry("bob", version="1.2.3", profiles=[ProfileRule(include=False, pattern="linux*")])]),

            ("bob/1.2.3 p=linux*,windows*",
             [PackageEntry("bob",
                           version="1.2.3",
                           profiles=[ProfileRule(include=True, pattern="linux*"),
                                     ProfileRule(include=True, pattern="windows*")])]),
        ])
    def test_parse_packages(
            self,
            input_str: str,
            expected_config: List[PackageEntry]) -> None:
        """
            Use StringIO to simulate a file-like object, and parse the lines
        """
        with StringIO(input_str) as io:
            config = parse_lines(io)

        assert expected_config == config
