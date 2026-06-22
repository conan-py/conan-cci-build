from pathlib import Path
from typing import Iterable

from conan.api.conan_api import ConanAPI
from conan.api.output import ConanOutput

from cci_build.error.exception import ConanAdapterError


class ConanClient:
    """
        Thin wrapper over Conan 2 public API.
    """

    def __init__(self) -> None:
        try:
            self.api = ConanAPI()
        except Exception as e:
            raise ConanAdapterError(str(e))

    def binary_exists(self, ref: str, remote: str) -> bool:
        """
        Uses Conan list against remote.
        """

        try:
            result = self.api.list.select(ref, remote=remote)
            return bool(result) and len(result) > 0
        except Exception:
            return False

    def create(self, recipe: Path, host: str, build: str) -> list[str]:
        """
        Executes in-process create using Conan API.
        """

        try:
            graph = self.api.graph.load_graph(
                path=str(recipe),
                name=None,
                version=None,
                args=[f"-pr:h={host}", f"-pr:b={build}", "--build=missing"],
            )

            self.api.graph.analyze_binaries(graph)
            self.api.graph.build(graph)

            return [str(node.ref) for node in graph.nodes.values() if node.binary_package]

        except Exception as e:
            raise ConanAdapterError(f"Create failed: {e}")

    def upload(self, refs: Iterable[str], remote: str) -> None:
        try:
            for ref in refs:
                self.api.upload.upload_full(ref, remote=remote, only_recipe=False, only_package=True)
        except Exception as e:
            raise ConanAdapterError(f"Upload failed: {e}")
