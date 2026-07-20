"""
    A conan extension command entry point that thunks through to the cc-build module.
"""
import argparse

from conan.api.conan_api import ConanAPI
from conan.cli.command import conan_command


@conan_command(group="Custom commands")
def cci_build(conan_api: ConanAPI, parser: argparse.ArgumentParser, *args):
    """
        Build Conan Center Index packages using a custom utility pipeline.

        Run the following to install/use this command in developer mode:
            > conan config install .
            > conan cci-build --help
    """

    # Load the cc-build module here so that install problems are
    # reported to the caller.
    #
    # pylint: disable=import-outside-toplevel
    from cci_build.main import cci_build_command

    return cci_build_command(conan_api, parser, *args)
