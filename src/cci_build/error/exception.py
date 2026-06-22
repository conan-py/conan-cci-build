class CacheSyncError(Exception):
    pass


class PackageFileError(CacheSyncError):
    pass


class RecipeNotFoundError(CacheSyncError):
    pass


class ConanAdapterError(CacheSyncError):
    pass