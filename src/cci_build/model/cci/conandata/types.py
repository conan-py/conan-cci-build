from typing import Optional, Dict, List, TypedDict


class SourceInfo(TypedDict):
    """Stores source archive download data for a given version."""
    url: str | List[str]  # Can be a single fallback string or list of mirrors
    sha256: str
    # Optional entries occasionally seen in older/specialised recipes
    md5: Optional[str]

class PatchInfo(TypedDict):
    """Defines a single patch modification to apply to downloaded sources."""
    patch_file: str
    description: str
    patch_type: Optional[str]      # e.g., "official", "bugfix", "portability"
    patch_source: Optional[str]    # Link to an upstream PR or issue tracker
    # Optional directory path offsets used by conan.tools.files.patch
    base_path: Optional[str]

class ConanDataLayout(TypedDict):
    """The full typed specification mirroring a standard `conandata.yml` file."""
    sources: Dict[str, SourceInfo]
    """ A map of package version -> Source Info """
    patches: Optional[Dict[str, List[PatchInfo]]]
