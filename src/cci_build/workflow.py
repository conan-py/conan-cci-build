import logging
from pathlib import Path
from typing import Tuple, List, Optional, Any

from conan.internal.errors import NotFoundException
from conan.internal.graph.graph import Node, RECIPE_VIRTUAL, RECIPE_CONSUMER, DepsGraph
from conan.internal.graph.install_graph import InstallGraph

from cci_build.conan_centre_index import find_cci_conanfile
from cci_build.conan_client import ConanClient
from cci_build.error.exception import PackageFileError
from cci_build.model.context import Context
from cci_build.model.settings.types import PackageEntry
from cci_build.package_parser import load_package_file
from conan.api.output import ConanOutput
from cci_build.profile_matcher import include_rules

from conan.api.conan_api import ConanAPI
from conan.api.model import RecipeReference, Remote, ListPattern
from conan.internal.model.profile import Profile

def make_revision(ref: RecipeReference) -> str:
    pattern_str = f"{ref.name}/{ref.version if ref.version else '*'}"
    return pattern_str + (f"@{ref.user}/{ref.channel}" if ref.user and ref.channel else "#*")

def list_select(conan :ConanClient, search_pattern :ListPattern, remote: Optional[Remote]) -> bool:
    try:
        return  conan.api.list.select(search_pattern, remote=remote)

    except NotFoundException as e:
       return False

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

        remote = self.api.remotes.get(ctx.remote) if ctx.remote else None
        remotes = [remote] if remote else []

        self.create_remote_recipe(refs, ctx, remote)

        graphs = self.build_package_graph(refs, ctx, remotes)

        xx = self.make_build_graph(graphs, ctx, remotes)

        ordered_build_graph = self.api.graph.subgraph(xx).topological_sort()

        """      

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

    def build_package_graph(
            self, packages: List[Tuple[RecipeReference, Path]], context: Context, remotes: List[Remote]) -> List[DepsGraph]:
        """
            For each of the packages, add it to the package graph.
        """

        graphs = []
        for ref, conanfile in packages:
            self.log.info(f"Building graph '{str(ref)}'")
            clean_conanfile_path = str(Path(conanfile).resolve().absolute())
            deps_graph = self.conan.api.graph.load_graph_consumer(
                path=clean_conanfile_path,
                name=ref.name,
                version=ref.version,
                user=ref.user,
                channel=ref.channel,
                remotes=remotes,
                lockfile=None,
                update=True,  # update the remote if the recipie doesn't exist
                profile_host=self.profile_host,
                profile_build=self.profile_build)

            # Stop now if there was an error
            deps_graph.report_graph_error()

            graphs.append(deps_graph)

        return graphs

    def make_one(self, graph: DepsGraph, context: Context, remotes: List[Remote]) -> InstallGraph:

        class DummyProfileArgs:
            def __getattr__(self, name):
                return None

        self.log.info(f"Graph {graph.nodes[0].name}")

        # Go to the remote and check if the binaries are present. It is important
        # to note that the recipe must exist at the remote.
        self.conan.api.graph.analyze_binaries(graph, build_mode=["missing"], remotes=remotes)

        # Create an install graph from the dependency graph.
        return self.conan.api.graph.build_order(graph, profile_args=DummyProfileArgs())


    def create_remote_recipe(self, refs: List[Tuple[RecipeReference, Path]], context: Context, remote: Remote):
        for ref, conanfile_path in refs:
            search_pattern = ListPattern(make_revision(ref))
            self.log.info(f'Searching for recipe "{ make_revision(ref) }"')
            remote_check = list_select(self.conan, search_pattern, remote=remote)
            if not remote_check:

                local_recipes = list_select(self.conan, search_pattern, remote=None)
                if not local_recipes:
                    self.log.info(f'Exporting recipe "{ str(ref) }"')
                    clean_conanfile_path = str(Path(conanfile_path).resolve().absolute())

                    exported_ref, conanfile_obj = self.conan.api.export.export(
                        path=clean_conanfile_path,
                        name=ref.name,
                        version=ref.version,
                        user=ref.user,
                        channel=ref.channel)

                self.log.info(f'Upload recipe "{ str(ref) }"')
                self.conan.api.upload.upload_full(
                    package_list=local_recipes,
                    remote=remote,
                    enabled_remotes=[remote],
                    dry_run=False)
            else:
                self.log.info(f'Recipe "{str(ref)}" present at remote "{remote.name}"')

    def make_build_graph(self, graphs: List[DepsGraph], context: Context, remotes: List[Remote]):
        """
            Create an order graph of the packages to be built.
        """

        install_graphs = [self.make_one(g, context, remotes)for g in graphs]

        if len(install_graphs) > 0:
            merged_build_order = install_graphs[0]
            for ig in install_graphs[1:]:
                merged_build_order.merge(ig)
        else:
            merged_build_order = []


    def get_matrix_build_order(self, package_list, profile_host_path, profile_build_path=None):
        # 1. Load profiles for the specific matrix node

        # 4. Analyze binaries against remotes/cache to mark build status
        self.api.graph.analyze_binaries(deps_graph, build_mode=["missing"])

        # 5. Extract the ordered matrix build steps
        # This groups packages into sequential lists ("levels") that can be safely built in parallel
        build_order = self.api.graph.get_build_order(deps_graph)
        return build_order



