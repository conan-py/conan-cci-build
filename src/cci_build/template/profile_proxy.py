from conan.internal.model.profile import Profile

from cci_build.template.profile_node import ProfileNode


class ProfileProxy(ProfileNode):
    """
        Proxy a single conan profile as jinja template values
    """

    def __init__(self, profile: Profile):
        self._profile = profile
        super().__init__(self.resolve)

    def resolve(self, path):
        """
            Resolve a jinja path into a value.
        """
        if not path:
            return self

        root = path[0]

        if root == "settings":
            return self._resolve_settings(path[1:])

        if root == "options":
            return self._resolve_options(path[1:])

        if root == "conf":
            return self._resolve_conf(path[1:])

        if root == "buildenv":
            return self._resolve_buildenv(path[1:])

        if root == "runenv":
            return self._resolve_runenv(path[1:])

        raise KeyError(".".join(path))

    def _resolve_settings(self, path):
        """
            The settings object is a simple dictionary with dot-separated string keys.
        """

        if not path:
            return self._profile.settings
        return self._profile.settings.get(".".join(path))

    def _resolve_options(self, path):

        if len(path) != 1:
            raise KeyError(path)

        return self._profile.options.get(path[0])

    def _resolve_conf(self, path):
        return self._profile.conf.get(".".join(path))

    def _resolve_buildenv(self, path):
        if len(path) != 1:
            raise KeyError(path)

        return self._profile.buildenv.get(path[0])

    def _resolve_runenv(self, path):
        if len(path) != 1:
            raise KeyError(path)
        return self._profile.runenv.get(path[0])
