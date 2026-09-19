"""
    Teamcity service message support.

    Each of these methods supress the output of Teamcity service messages if the
    code is not running on a build pipeline. This is checked by checking for the
    'TEAMCITY_VERSION' environment variable.

    see:
      - https://www.jetbrains.com/help/teamcity/service-messages.html
"""
import os

def teamcity_build_statistic(log, key: str, value: str) -> None:
    """
        Log a TeamCity service message to publish a build statistic.
    """
    log.info(f"Build statistic '{key}': {value}")

    if "TEAMCITY_VERSION" in os.environ:
        print(f"##teamcity[buildStatisticValue key='{_escape_teamcity_value(key)}' value='{_escape_teamcity_value(value)}']")


def publish_teamcity_artifact(log, name: str, path: str) -> None:
    """
        Log a TeamCity message to publish a build artefact.
    """
    log.info(f"Publishing artifact '{name}' from path: {path}")

    if "TEAMCITY_VERSION" in os.environ:
        # TeamCity syntax: ##teamcity[publishArtifacts '<path> => <target>']
        print(f"##teamcity[publishArtifacts '{_escape_teamcity_value(path)} => {_escape_teamcity_value(name)}']")


# Define the translation table once at the module level
_TC_ESCAPE_TABLE = str.maketrans({
    '|': '||',
    "'": "|'",
    '[': '|[',
    ']': '|]',
    '\n': '|n',
    '\r': '|r'
})

def _escape_teamcity_value(value: str) -> str:
    """
        Escape names/values/messages that are to be put into TeamCity service messages.
    """
    if not isinstance(value, str):
        value = str(value)
    return value.translate(_TC_ESCAPE_TABLE)

