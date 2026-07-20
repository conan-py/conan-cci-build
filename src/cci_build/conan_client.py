"""
    Wrap the ConanAPI
"""
from pathlib import Path

from conan.api.conan_api import ConanAPI
from conan.api.model import Remote, ListPattern
from conan.internal.errors import NotFoundException


class ConanClient:
    """
        Thin wrapper over Conan 2 public API.
    """

    def __init__(self, api: ConanAPI) -> None:
        self.api = api

    def binary_exists(self, ref: ListPattern, remote: Remote) -> bool:
        """
            Uses Conan list against remote.
        """

        try:
            result = self.api.list.select(ref, remote=remote)
            return bool(result)
        except NotFoundException:
            return False

    def create(self, recipe: Path, host: str, build: str) -> list[str]:
        """
            Executes in-process create using Conan API.
        """

        graph = self.api.graph.load_graph(
            path=str(recipe),
            name=None,
            version=None,
            args=[f"-pr:h={host}", f"-pr:b={build}", "--build=missing"],
        )

        self.api.graph.analyze_binaries(graph)
        self.api.graph.build(graph)

        return [str(node.ref) for node in graph.nodes.values() if node.binary_package]
