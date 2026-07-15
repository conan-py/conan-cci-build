"""
    Entrypoint for the cci-build (called from the conan extension command)
"""
import argparse
from pathlib import Path

from cci_build.workflow import Workflow
from conan.api.conan_api import ConanAPI
from conan.cli.command import conan_command

from cci_build.model.context import Context


def cci_build_command(_conan_api: ConanAPI, parser, *args):
    """
        Build Conan Center Index packages using a custom utility pipeline.
    """
    # Conan provides its own pre-configured argparse instance via 'parser'
    parser.add_argument("--cci-root", required=True, help="Path to the CCI root directory.")
    parser.add_argument("--remote", required=True, help="Conan remote target.")
    parser.add_argument("--host-profile", required=True, help="Host profile name or path.")
    parser.add_argument("--build-profile", required=True, help="Build profile name or path.")
    parser.add_argument("file", help="The packages file to process.")

    # Parse the arguments forwarded from Conan's command line interface
    parsed_args = parser.parse_args(*args)

    # Initialize your existing Context object
    config = Context(
        cci_root=Path(parsed_args.cci_root),
        remote=parsed_args.remote,
        host_profile=parsed_args.host_profile,
        build_profile=parsed_args.build_profile,
        packages_filename=parsed_args.file,
        channel=None,
        user=None
    )

    workflow = Workflow()
    workflow.run(config)
