"""
    Main workflow for building the packages.
"""
from pathlib import Path
from typing import Tuple, List, Optional, Any

from conan.api.conan_api import ConanAPI
from conan.api.model import RecipeReference, Remote, ListPattern, PackagesList
from conan.api.output import ConanOutput
from conan.internal.errors import NotFoundException
from conan.internal.graph.graph import DepsGraph, BINARY_BUILD
from conan.internal.model.profile import Profile

from cci_build.conan_centre_index import find_cci_conanfile
from cci_build.conan_client import ConanClient
from cci_build.error.exception import PackageFileError
from cci_build.model.context import Context
from cci_build.model.settings.types import PackageEntry
from cci_build.package_parser import load_package_file
from cci_build.profile_matcher import include_rules


def make_revision(ref: RecipeReference) -> str:
    """
        Make a conan search revision based on a recipe reference.
    """
    pattern_str = f"{ref.name}/{ref.version if ref.version else '*'}"
    return pattern_str + (f"@{ref.user}/{ref.channel}" if ref.user and ref.channel else "#*")


def list_select(conan: ConanClient, search_pattern: ListPattern, remote: Optional[Remote]) -> bool:
    """
        Select a list of conan recipes.
    """
    try:
        return conan.api.list.select(search_pattern, remote=remote)
    except NotFoundException:
        # Eat the exception (the specific error is not reported)
        return False


class Workflow:
    """
        Run a conan workflow to build all missing packages in a jFrog Artifactory repository.

        see:
           - https://docs.conan.io/2/reference/commands/graph/info.html
           - https://docs.conan.io/2/reference/extensions/python_api/GraphAPI.html
    """

    def __init__(self, api: ConanAPI, logger: ConanOutput):
        self.profile_build: Optional[Profile] = None
        self.profile_host: Optional[Profile] = None
        self.conan = ConanClient(api)
        self.api = api
        self.log = logger

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

        # Load the configuration file which describes packages in the local CCI that need to be built
        pkgs = load_package_file(Path(ctx.packages_filename))
        self.log.info(f"Found {len(pkgs)} packages")
        for pkg in pkgs:
            self.log.info(f"Processing package '{pkg.name}:{pkg.version if pkg.version else "*"}'")

        if ctx.remote:
            remote = self.api.remotes.get(ctx.remote)
            remotes = [remote] if remote else []

            #
            # Using the local CCI, map the desired packages to the exact recipe and version to be built
            # and filter which packages should be included based on the profile filter criteria.
            #
            refs = self.filter_package_names(ctx, pkgs)

            self.create_remote_recipe(refs, ctx, remote)
            graph = self.build_package_graph(refs, ctx, remotes)
            self.install_and_upload_missing(graph, remote, remotes)
        else:
            raise NotFoundException("No remote configured")


    def filter_package_names(self, ctx: Context, pkgs: list[PackageEntry]) -> List[Tuple[RecipeReference, Path]]:
        """
            Given the list of packages to build, filter them based on the host profile.
        """
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
            self, packages: List[Tuple[RecipeReference, Path]], context: Context, remotes: List[Remote]) -> DepsGraph:
        """
            For each of the packages, add it to the package graph.
        """
        requires = [ref for ref, _ in packages]
        deps_graph = self.api.graph.load_graph_requires(
            requires,
            tool_requires=None,
            profile_host=self.profile_host, profile_build=self.profile_build,
            lockfile=None,
            remotes=remotes,
            update=True)
        # Stop now if there was an error
        deps_graph.report_graph_error()

        # mark only remote-missing binaries for build (replaces make_build_graph/make_one)
        self.api.graph.analyze_binaries(deps_graph, build_mode=["missing"], remotes=remotes, update=True)

        return deps_graph

    def create_remote_recipe(self, refs: List[Tuple[RecipeReference, Path]], context: Context, remote: Remote):
        """
            Upload all recipes that don't exist at the remote.

            Note: this creates a recipe in the remote, but none of the binaries.
        """
        for ref, conanfile_path in refs:
            search_pattern = ListPattern(make_revision(ref))
            self.log.info(f'Searching for recipe "{make_revision(ref)}"')
            remote_check = list_select(self.conan, search_pattern, remote=remote)
            if not remote_check:

                local_recipes = list_select(self.conan, search_pattern, remote=None)
                if not local_recipes:
                    self.log.info(f'Exporting recipe "{str(ref)}"')
                    clean_conanfile_path = str(Path(conanfile_path).resolve().absolute())

                    exported_ref, conanfile_obj = self.conan.api.export.export(
                        path=clean_conanfile_path,
                        name=ref.name,
                        version=ref.version,
                        user=ref.user,
                        channel=ref.channel)

                self.log.info(f'Upload recipe "{str(ref)}"')
                self.conan.api.upload.upload_full(
                    package_list=local_recipes,
                    remote=remote,
                    enabled_remotes=[remote],
                    dry_run=False)
            else:
                self.log.info(f'Recipe "{str(ref)}" present at remote "{remote.name}"')


    def install_and_upload_missing(self, graph: DepsGraph, remote: Remote, remotes: list[Remote] | list[Any]):
        """
            Locally build those binaries (for the given profile) that are missing at the remote.
        """
        install_error = self.api.install.install_binaries(deps_graph=graph, remotes=remotes, return_install_error=True)

        built = PackagesList()
        for node in graph.nodes:
            # a completed build has a package revision; a failed one does not
            if node.binary == BINARY_BUILD and node.pref.revision:
                built.add_ref(node.ref)
                built.add_pref(node.pref)
        if built:
            self.api.upload.upload_full(
                built, remote, enabled_remotes=remotes, check_integrity=True, dry_run=False)
        if install_error is not None:
            raise install_error
