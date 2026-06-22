from dataclasses import dataclass


# @dataclass(frozen=True)
# class PackageRequest:
#     """ Meta data of a single package to be built """
#
#     name: str
#     """ The name of the package to be built """
#
#     version: str
#     """ A specific semantic version of the package to be built """
#
#     rules: list[str]
#     """ A list of matching profile tags, used to determine if a package will be built  """
#
#     @property
#     def ref(self) -> str:
#         return f"{self.name}/{self.version}"
