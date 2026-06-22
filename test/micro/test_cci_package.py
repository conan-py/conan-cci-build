from typing import Optional, List, Type

import pytest

from cci_build.conan_centre_index import find_cci_conanfile
from cci_build.error.exception import RecipeNotFoundError
from resources import sample_cci_path


class TestCciPackage:

    @pytest.mark.parametrize(
        "package_name, version, expected_version, expected_conanfile_path, expected_exception",
        [
            ("bogus", "1.0.0", None, None, RecipeNotFoundError),  # Unknown package
            ("lz4", None, "1.10.0", "recipes/lz4/all/conanfile.py", None),  # latest version of lz4
            ("lz4", "1.9.4", "1.9.4", "recipes/lz4/all/conanfile.py", None),  # an old version
            ("zlib", "1.3.2", "1.3.2", "recipes/zlib/all/conanfile.py", None),  # exact latest
            ("zlib", "999.9.9",  None, None, RecipeNotFoundError),  # invalid version

            ("sample",  None, "2.10.0", "recipes/sample/all/conanfile.py", None),  # multi-folder latest
            ("sample", "2.9.4", "2.9.4", "recipes/sample/all/conanfile.py", None),  # multi-folder exact 'all' folder
            ("sample", "1.9.4", "1.9.4", "recipes/sample/1.0.0/conanfile.py", None),  # multi-folder, old folder
        ])
    def test_bulk_generation(
            self,
            package_name : str,
            version: Optional[str],
            expected_version: str,
            expected_conanfile_path: str,
            expected_exception: Optional[Type [Exception]] ):
        if expected_exception:
            with pytest.raises(expected_exception):
              _, _ = find_cci_conanfile(sample_cci_path, package_name, version)
        else:
            v, cf = find_cci_conanfile(sample_cci_path, package_name, version)
            assert expected_version == v
            full_expected_path =sample_cci_path / expected_conanfile_path if expected_conanfile_path else None
            assert full_expected_path == cf
