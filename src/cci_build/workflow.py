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
from cci_build.package_parser import load_package_string
from cci_build.profile_matcher import include_rules
from cci_build.template.render import render_packages_file


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
        t = render_packages_file(Path(ctx.packages_filename), self.profile_build, self.profile_host)
        pkgs = load_package_string(t)
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

            self.sync_recipies(refs, remote)
            graph = self.build_package_graph(refs, remotes)
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

    def sync_recipies(self, refs: List[Tuple[RecipeReference, Path]], remote: Remote):
        """
            Export all recipies unconditionally into the local conan cache
            from the CCI recipes.
        """
        to_upload = PackagesList()
        for ref, conanfile_path in refs:
            clean_conanfile_path = str(Path(conanfile_path).resolve().absolute())

            # 1. Always export from the CCI -> local cache (computes the fresh rrev)
            self.log.info(f'Exporting recipe "{ref}" from CCI')
            exported_ref, _ = self.conan.api.export.export(
                path=clean_conanfile_path,
                name=ref.name, version=str(ref.version),
                user=ref.user, channel=ref.channel)

            # 2. Re-select the exact exported revision from the cache
            pattern = ListPattern(exported_ref.repr_notime())  # name/version@user/channel#rrev
            pkg_list = self.conan.api.list.select(pattern, remote=None)
            self.log.info(f'Will upload recipes "{exported_ref.repr_notime()}" to "{remote.name}"')
            to_upload.merge(pkg_list)

        # 3. Upload all recipes revision to the remote BEFORE any resolution.
        #    upload_full skips it if the rrev is already upstream.
        if to_upload:
            self.log.info(f'Uploading recipes to "{remote.name}"')
            self.conan.api.upload.upload_full(package_list=to_upload, remote=remote, enabled_remotes=[remote])

    def build_package_graph(self, packages: List[Tuple[RecipeReference, Path]], remotes: List[Remote]) -> DepsGraph:
        """
            For each of the packages, add it to the package graph.
        """
        self.log.info(f"Load graph required for {len(packages)} packages")
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
        self.log.info(f"Analyzing graph dependencies")
        self.api.graph.analyze_binaries(deps_graph, build_mode=["missing"], remotes=remotes, update=True)

        return deps_graph


    def install_and_upload_missing(self, graph: DepsGraph, remote: Remote, remotes: list[Remote] | list[Any]):
        """
            Locally build those binaries (for the given profile) that are missing at the remote.
        """
        self.log.info(f"Building missing packages")
        install_error = self.api.install.install_binaries(deps_graph=graph, remotes=remotes, return_install_error=True)

        built = PackagesList()
        for node in graph.nodes:
            # a completed build has a package revision; a failed one does not
            if node.binary == BINARY_BUILD and node.pref.revision:
                built.add_ref(node.ref)
                built.add_pref(node.pref)
        if built:
            self.log.info(f"Upload packages")
            self.api.upload.upload_full(
                built, remote, enabled_remotes=remotes, check_integrity=True, dry_run=False)
        else:
            self.log.info(f"No new packages to build")

        if install_error is not None:
            raise install_error
