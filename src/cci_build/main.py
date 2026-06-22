import argparse
from pathlib import Path
from .extension import run
from .model.context import Context


def main():
    p = argparse.ArgumentParser("conan-cci-build")

    p.add_argument("--cci-root", required=True)
    p.add_argument("--remote", required=True)
    p.add_argument("--host-profile", required=True)
    p.add_argument("--build-profile", required=True)
    p.add_argument("file")

    args = p.parse_args()

    config = Context(
        cci_root=Path(args.cci_root),
        remote=args.remote,
        host_profile=args.host_profile,
        build_profile=args.build_profile,
        packages_filename=args.file,
    )

    run(config)