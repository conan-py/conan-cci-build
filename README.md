# [Conan CCI Build](https://github.com/conan-py/conan-cci-build)

Populate a Conan 2 Artifactory remote from a local Conan Center Index checkout.

# Usage

This [module](https://pypi.org/project/conan-cci-build/) is used along with conan to build packages. The following is an 
example workflow to use this python module.

Notes:
  - Using a python virtual environment is an example way to use this.
  - the `conan-cci-build-install` command is required to install the package into the conan configuration

```shell
python -m venv .venv
source .venv/Scripts/activate
pip install conan conan-cci-build
conan config install <path to conan config>
conan-cci-build-install 
conan cci-build --remote <name> --cci-root <path to cci recipes> --host-profile <profile> --build-profile <profile> <conanfile.txt>
```


# Links

- https://pypi.org/project/conan-cci-build/
- https://github.com/conan-io/conan-center-index
- https://github.com/conan-io/conan-extensions
- https://blog.conan.io/2024/04/23/Introducing-local-recipes-index-remote.html