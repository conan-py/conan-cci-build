import re
from io import TextIOWrapper
from pathlib import Path
from typing import List, Optional

from .error.exception import PackageFileError
from cci_build.model.settings.types import PackageEntry, ProfileRule

# LINE = re.compile(r"^\s*([a-zA-Z0-9_.+-]+/[a-zA-Z0-9_.+-]+)(?:\s*\[(.+)\])?\s*$")
LINE_REGEX = re.compile(
    r"""
    ^
    
    (?: 
        \s*                          # Ignore leading whitespace
    
        (?P<name> [a-zA-Z0-9_.+-]+ )
        
        # An optional version
        (?: \s* / \s* (?P<version>[\w.+-]+ ) )?
    
        \s*
        (?:
            (?: p | profiles ) = 
            (?P<profiles> !? [\w.+*-]+ (?: , \s* !? [\w.+*-]+ )* )
        )?

    )?
    \s*    # allow trailing whitespace
    
    
    (?: \# .* )?  # ignore comments    
    
    $
    """,
    re.VERBOSE,
)




def parse_line(line: str) -> Optional[PackageEntry]:
    """
    """
    m = LINE_REGEX.match(line)
    if not m:
        raise PackageFileError(f"Invalid line '{line}'")

    name = m.group("name")
    if name is not None:
        version = m.group("version")
        profiles = m.group("profiles").split(",") if m.group("profiles") else []

        profile_rules = []
        for r in [x.strip() for x in profiles]:
            profile_rules.append(parse_profile_rule(r))

        return PackageEntry(name=name, version=version, profiles=profile_rules)
    return None


def parse_profile_rule(rule_str: str) -> ProfileRule:
    if not rule_str.startswith("!"):
        return ProfileRule(include=True, pattern=rule_str)
    else:
        return ProfileRule(include=False, pattern=rule_str[1:])


def parse_lines(stream: TextIOWrapper) -> List[PackageEntry]:
    return [
        entry
        for a_line in stream
        if (entry := parse_line(a_line.strip())) is not None
    ]


def load_package_file(path: Path) -> List[PackageEntry]:
    with open(path) as f:
        return parse_lines(f)
