import logging
from pathlib import Path
from typing import Tuple, List, Optional

from cci_build.conan_centre_index import find_cci_conanfile
from cci_build.conan_client import ConanClient
from cci_build.error.exception import PackageFileError
from cci_build.model.context import Context
from cci_build.package_parser import load_package_file
from cci_build.profile_matcher import include_rules

from conan.api.conan_api import ConanAPI
from conan.api.model import RecipeReference
from conan.internal.model.profile import Profile

log = logging.getLogger(__name__)

class Workflow:
    def __init__(self):
        self.profile_build: Optional[Profile] = None
        self.profile_host: Optional[Profile] = None
        self.conan = ConanClient()
        self.api = ConanAPI()

    def run(self, ctx: Context) -> None:
        """
            Perform a minimal build of one host (target) profile. The inputs
            to the process are:
               - the local package list configuration file
               - a local filesystem copy of a CCI

            The state is help in:
               - a jFrog Artifactory repository

            The pre-requisites are:
               - this script
               - conan installed and configured with profiles
               - a conan remote configured and authenticated to the Artifactory repository

        """
        self.profile_host = self.api.profiles.get_profile([ctx.host_profile])
        if self.profile_host is None:
            raise ModuleNotFoundError(f"No profile found for '{ctx.host_profile}'")

        self.profile_host.options.update(options_values=custom_options)

        self.profile_build = self.api.profiles.get_profile(
            [ctx.build_profile]) if ctx.build_profile else self.api.profiles.get_default_build()
        if self.profile_build is None:
            raise ModuleNotFoundError(f"No profile found for '{ctx.build_profile}'")

        # Load the configuration file describes which packages in the local CCI need to be built
        pkgs = load_package_file(Path(ctx.packages_filename))

        # Using the local CCI, map the desired packages to the exact recipe and version to be built
        refs = []
        for pkg in pkgs:

            # Check if the profile rules in the configuration file allow this 'host' profile
            if include_rules(pkg.profiles, ctx.host_profile):

                # Given the package/profile/version needs to be present, resolve the package
                # and the version in the CCI.
                version, conanfile = find_cci_conanfile(ctx.cci_root, pkg.name, pkg.version)
                if version:
                    ref = RecipeReference(name=pkg.name, version=version)
                    refs.append(ref)
                else:
                    log.error("Can not determine version for package '%s'", pkg.name)
                    raise PackageFileError()
            else:
                log.info("Skipping package '%s' as it does not match the host profile", pkg.name)

        # 2. Create a virtual dependency root graph containing all target packages
        # This mimics a 'conanfile.txt' requiring your entire list
        deps_graph = self.api.graph.load_graph_requires(
            requires=[p.ref for p in refs],
            tool_requires=None,
            profile_host=self.profile_host,
            profile_build=self.profile_build,
            lockfile=None,
            remotes=self.api.remotes.list(),
            update=False
        )

        root_conanfile = self.api.graph.load_root_virtual(
            requires=refs,
            profile_host=self.profile_host,
            profile_build=self.profile_build
        )

        # 3. Resolve the full dependency graph and identify missing binaries
        # --build=missing is specified to determine what actually needs compiling
        deps_graph = self.api.graph.load_graph_consumer(
            root_conanfile,
            build_mode=["missing"],
            update=False
        )

    def get_matrix_build_order(self, package_list, profile_host_path, profile_build_path=None):

        # 1. Load profiles for the specific matrix node



        # 4. Analyze binaries against remotes/cache to mark build status
        self.api.graph.analyze_binaries(deps_graph, build_mode=["missing"])

        # 5. Extract the ordered matrix build steps
        # This groups packages into sequential lists ("levels") that can be safely built in parallel
        build_order = api.graph.get_build_order(deps_graph)
        return build_order

    # Example Usage
    if __name__ == "__main__":
        targets = ["zlib/1.3.1", "openssl/3.2.1", "libcurl/8.6.0"]

        # Levels represent chronological steps; packages within the same level have no mutual dependencies
        levels = get_matrix_build_order(targets, profile_host_path="default")

        for idx, level in enumerate(levels):
            print(f"--- Build Level {idx} (Can execute concurrently) ---")
            for item in level:
                # item.ref contains the package recipe reference requiring compilation
                print(f"  Compile: {item.ref} (ID: {item.package_id})")

    def _run_one(self, conanfile: str, version: str, options: List[Tuple[str, str]]  ctx: Context

    ) -> None:
    # if not self.matcher.include(pkg, ctx.host_profile):
    #     return
    #
    # recipe = self.cci.resolve(ctx.cci_root, pkg)

    if self.conan.binary_exists(pkg.ref, ctx.remote):
        return

    built = self.conan.create(recipe, ctx.host_profile, ctx.build_profile)
    self.conan.upload(built, ctx.remote)
