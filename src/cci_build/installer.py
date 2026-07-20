"""
    A script to install the cci-build command into Conan.
"""
import logging
import os
import shutil
from importlib.resources import files, as_file
from pathlib import Path

log = logging.getLogger(__name__)

def get_conan_home() -> Path:
    """
        Resolve Conan 2 home directory.

        This is the root directory where Conan stores:
            - cache
            - extensions
            - configuration
            - remotes

        Resolution order:
            1. CONAN_HOME environment variable (if set)
            2. Default platform-specific location (~/.conan2)

        Returns:
            Path to Conan home directory.
    """

    # 1. Explicit override (highest priority)
    env_home = os.environ.get("CONAN_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()

    # 2. Default Conan 2 home directory
    # Conan 2 standard default is ~/.conan2 unless overridden
    return Path.home() / ".conan2"



def main():
    """
       Entry
    """
    conan_home = get_conan_home()
    target_dir = conan_home / "extensions" / "commands"
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / "cmd_cci_build.py"

    resource = files("cci_build_extensions.commands").joinpath("cmd_cci_build.py")
    with as_file(resource) as src:
        shutil.copyfile(src, destination)

    log.info(f"Installed Conan extension to: {destination}")
