import logging
from pathlib import Path
from typing import Tuple, List, Optional, Any

from conan.internal.graph.graph import Node, RECIPE_VIRTUAL, RECIPE_CONSUMER

from cci_build.conan_centre_index import find_cci_conanfile
from cci_build.conan_client import ConanClient
from cci_build.error.exception import PackageFileError
from cci_build.model.context import Context
from cci_build.model.settings.types import PackageEntry
from cci_build.package_parser import load_package_file
from conan.api.output import ConanOutput
from cci_build.profile_matcher import include_rules

from conan.api.conan_api import ConanAPI
from conan.api.model import RecipeReference
from conan.internal.model.profile import Profile



class Workflow:
    def __init__(self):
        self.profile_build: Optional[Profile] = None
        self.profile_host: Optional[Profile] = None
        self.conan = ConanClient()
        self.api = ConanAPI()
        self.log = ConanOutput()

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

        self.profile_build = self.api.profiles.get_profile(
            [ctx.build_profile]) if ctx.build_profile else self.api.profiles.get_default_build()
        if self.profile_build is None:
            raise ModuleNotFoundError(f"No profile found for '{ctx.build_profile}'")

        # Load the configuration file describes which packages in the local CCI that need to be built
        pkgs = load_package_file(Path(ctx.packages_filename))
        self.log.info(f"Found {len(pkgs)} packages")
        for pkg in pkgs:
            self.log.info(f"Processing package '{pkg.name}:{pkg.version if pkg.version else "*"}'")

        #
        # Using the local CCI, map the desired packages to the exact recipe and version to be built
        # and filter which packages should be included based on the profile filter criteria.
        #
        refs = self.filter_package_names(ctx, pkgs)

        # 2. Create a virtual dependency root graph containing all target packages
        # This mimics a 'conanfile.txt' requiring your entire list
        #
        #  see:
        #    - https://docs.conan.io/2/reference/commands/graph/info.html
        #    - https://docs.conan.io/2/reference/extensions/python_api/GraphAPI.html
        graph = self.build_package_graph(refs, ctx)

        xx = self.make_build_graph(graph, ctx)

        ordered_build_graph = graph.subgraph(xx).topological_sort()


        """
        deps_graph = self.api.graph.load_graph_requires(
            requires=[f"{r.name}/{r.version}" for r in refs],
            tool_requires=[],
            profile_host=self.profile_host,
            profile_build=self.profile_build,
            lockfile=None,
            remotes=[self.api.remotes.get(ctx.remote)],
            update=False
        )

        x = self.api.graph.analyze_binaries(deps_graph, build_mode=["missing"],             remotes=[self.api.remotes.get(ctx.remote)])

        # root_conanfile = self.api.graph.load_root_virtual(
        #     requires=refs,
        #     profile_host=self.profile_host,
        #     profile_build=self.profile_build
        # )

        # 3. Resolve the full dependency graph and identify missing binaries
        # --build=missing is specified to determine what actually needs compiling
        deps_graph = self.api.graph.load_graph_consumer(
            root_conanfile,
            build_mode=["missing"],
            update=False
        )
        """

    def filter_package_names(self, ctx: Context, pkgs: list[PackageEntry]) -> List[Tuple[RecipeReference, Path]]:
        refs = []
        for pkg in pkgs:

            # Check if the profile rules in the configuration file allow this 'host' profile
            if include_rules(pkg.profiles, ctx.host_profile):

                # Given the package/profile/version needs to be present, resolve the package
                # and the version in the CCI.
                version, conanfile = find_cci_conanfile(ctx.cci_root, pkg.name, pkg.version)
                if version:
                    ref = RecipeReference(name=pkg.name, version=version, user=ctx.user, channel=ctx.channel)
                    refs.append((ref, conanfile,))
                    self.log.info(f"Found CCI reference '{ref.name}:{ref.version}'")
                else:
                    self.log.error("Can not determine version for package '%s'", pkg.name)
                    raise PackageFileError()
            else:
                self.log.info("Skipping package '%s' as it does not match the host profile", pkg.name)
        return refs

    def build_package_graph(self, packages : List[Tuple[RecipeReference, Path]], context:Context):
        """
            For each of the packages, add it to the package graph.
        """

        graphs = []
        for ref, conanfile in packages:
            clean_conanfile_path = str(Path(conanfile).resolve().absolute())
            deps_graph = self.conan.api.graph.load_graph_consumer(
                # path=str(conanfile),
                path=clean_conanfile_path,
                name=ref.name,
                version = ref.version,
                user=ref.user,
                channel=ref.channel,
                remotes=[self.api.remotes.get(context.remote)],
                lockfile=None,
                update=False,
                profile_host=self.profile_host,
                profile_build=self.profile_build)

            graphs.append(deps_graph)

        # Merge all graphs into one
        return self.conan.api.graph.merge_graphs(graphs)

    def make_build_graph(self, graph, context:Context):
        """
            Create an order graph of the packages to be built.
        """

        build_list = []
        for node in graph.nodes:
            if node.recipe == RECIPE_VIRTUAL:
                continue

            if node.recipe == RECIPE_CONSUMER:
                continue

            self.conan.api.graph.analyze_binaries(
                graph=node.graph,
                remotes=[artifactory_remote]
            )

            if node.binary == "Build":
                build_list.append(node)

    def get_matrix_build_order(self, package_list, profile_host_path, profile_build_path=None):

        # 1. Load profiles for the specific matrix node

        # 4. Analyze binaries against remotes/cache to mark build status
        self.api.graph.analyze_binaries(deps_graph, build_mode=["missing"])

        # 5. Extract the ordered matrix build steps
        # This groups packages into sequential lists ("levels") that can be safely built in parallel
        build_order = api.graph.get_build_order(deps_graph)
        return build_order

    # # Example Usage
    # if __name__ == "__main__":
    #     targets = ["zlib/1.3.1", "openssl/3.2.1", "libcurl/8.6.0"]
    #
    #     # Levels represent chronological steps; packages within the same level have no mutual dependencies
    #     levels = get_matrix_build_order(targets, profile_host_path="default")
    #
    #     for idx, level in enumerate(levels):
    #         print(f"--- Build Level {idx} (Can execute concurrently) ---")
    #         for item in level:
    #             # item.ref contains the package recipe reference requiring compilation
    #             print(f"  Compile: {item.ref} (ID: {item.package_id})")
    #
    # def _run_one(self, conanfile: str, version: str, options: List[Tuple[str, str]]  ctx: Context
    #
    # ) -> None:
    # # if not self.matcher.include(pkg, ctx.host_profile):
    # #     return
    # #
    # # recipe = self.cci.resolve(ctx.cci_root, pkg)
    #
    # if self.conan.binary_exists(pkg.ref, ctx.remote):
    #     return
    #
    # built = self.conan.create(recipe, ctx.host_profile, ctx.build_profile)
    # self.conan.upload(built, ctx.remote)

"""
from conan.api.conan_api import ConanAPI
from conans.client.graph.graph import Node


HOST_PROFILE = "profiles/linux-gcc13"
BUILD_PROFILE = "profiles/build"

CCI_PATH = Path("/work/conan-center-index")
REMOTE = "artifactory"

ROOT_PACKAGES = [
    "zlib/1.3.1",
    "fmt/11.0.2",
    "openssl/3.5.0",
]


conan = ConanAPI()


# ----------------------------------------------------------------------
# Configure remotes / profiles
# ----------------------------------------------------------------------

host_profile = conan.profiles.get_profile([HOST_PROFILE])
build_profile = conan.profiles.get_profile([BUILD_PROFILE])

remotes = conan.remotes.list()
artifactory_remote = next(r for r in remotes if r.name == REMOTE)


# ----------------------------------------------------------------------
# Build a graph from recipes in the local CCI checkout
# ----------------------------------------------------------------------

graphs = []

for ref in ROOT_PACKAGES:

    deps_graph = conan.graph.load_graph_consumer(
        path=CCI_PATH / "recipes",
        name=ref,
        profile_host=host_profile,
        profile_build=build_profile,
    )

    graphs.append(deps_graph)


# Merge all graphs into one
full_graph = conan.graph.merge_graphs(graphs)


# ----------------------------------------------------------------------
# Determine which packages already have binaries
# ----------------------------------------------------------------------

packages_to_build = []

for node in full_graph.nodes:

    if node.recipe == Node.RECIPE_VIRTUAL:
        continue

    if node.recipe == Node.RECIPE_CONSUMER:
        continue

    conan.graph.analyze_binaries(
        graph=node.graph,
        remotes=[artifactory_remote]
    )

    if node.binary == "Build":
        packages_to_build.append(node)


# ----------------------------------------------------------------------
# Build dependency graph of packages needing binaries
# ----------------------------------------------------------------------

build_graph = full_graph.subgraph(packages_to_build)

ordered_nodes = build_graph.topological_sort()


# ----------------------------------------------------------------------
# Build in dependency order
# ----------------------------------------------------------------------

for node in ordered_nodes:

    print(f"Building {node.ref}")

    conan.create.create(
        path=node.recipe_folder,
        profile_host=host_profile,
        profile_build=build_profile,
    )


# ----------------------------------------------------------------------
# Upload
# ----------------------------------------------------------------------

for node in ordered_nodes:

    print(f"Uploading {node.ref}")

    conan.upload.upload(reference=node.ref, remote=REMOTE, packages="*", confirm=True)


"""