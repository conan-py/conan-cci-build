from typing import Callable, Any


class ProfileNode:
    """
    Lazy proxy over a Conan profile.

    Every attribute access extends the lookup path.
    Conversion to str/bool/int/etc performs the actual lookup.
    """

    def __init__(self,
                 resolver: Callable[[tuple[str, ...]], Any],
                 path: tuple[str, ...] = ()):
        self._resolver = resolver
        self._path = path

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return ProfileNode(self._resolver, self._path + (name,))

    def __getitem__(self, name):
        if isinstance(name, str) and name.startswith('_'):
            raise KeyError(name)
        return ProfileNode(self._resolver, self._path + (name,))


    @property
    def value(self):
        return self._resolver(self._path)

    def __str__(self):
        value = self.value
        if value is self:
            return ""
        return "" if value is None else str(value)

    def __repr__(self):
        val = self.value
        return repr(val) if val is not self else "ProfileNode()"

    def __bool__(self):
        val = self.value
        return bool(val) if val is not self else False

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other
