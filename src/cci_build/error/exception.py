"""
    Exceptions
"""
from conan.errors import ConanException


class PackageFileError(ConanException):
    """
        A conan error that is raised when a package file is not found.
    """


class RecipeNotFoundError(ConanException):
    """
      A conan error that is raised when a recipe is not found.
    """
