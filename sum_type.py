# type: ignore
"""
Sum type. Abandon all hope ye who enter here.
"""

from context_manager_patma import register
from typing import Any, Callable, Iterator, Tuple, Type, TypeVar, overload


class _EmbellishedBase:
    _constructor_name: str


def embellished(name, definition):
    class EmbellishedMeta(type):
        def __repr__(self):
            return f"embellished({self._constructor_name!r}, {definition!r})"

    class Embellished(_EmbellishedBase, metaclass=EmbellishedMeta):
        _constructor_name = name
        def __repr__(self):
            return f"prop<:{self._constructor_name} :: {definition!r})>({self})"

    return Embellished


def make_constructor(name, definition):
    # Metametaclass!
    class __make_base_meta__(type):
        def __instancecheck__(self, instance):
            return (
                isinstance(instance, _EmbellishedBase)
                and instance._constructor_name == name
            )

        def __repr__(self):
            return name

    class __make_base__(type, metaclass=__make_base_meta__):
        def __instancecheck__(self, instance):
            return (
                isinstance(instance, _EmbellishedBase)
                and instance._constructor_name == name
            )

    if isinstance(definition, type):
        class __make__(__make_base__):
            def __new__(self, x):
                if isinstance(x, definition):
                    return x
                # otherwise, try to coerce the value
                e = embellished(name, definition)
                return type(type.__name__ + "*", (definition, e, ), {})(x)
    elif isinstance(definition, tuple):
        class __make__(__make_base__):
            def __new__(self, *args):
                if len(args) != len(definition):
                    raise TypeError(
                        "Incorrect argument count for tuple constructor"
                    )
                e = embellished(name, definition)

                def _repr(self):
                    return f"{name}({', '.join(map(repr, self))})"
                e.__repr__ = _repr

                def _eq(self, other):
                    if not isinstance(other, tuple):
                        return NotImplemented
                    if not hasattr(other, "_constructor_name"):
                        return False
                    return self._constructor_name == other._constructor_name
                e.__eq__ = _eq

                T = type(type.__name__ + "*", (e, tuple), {})
                return T(
                    make_constructor(f"{name}.{i}", t)(x)
                    for i, (t, x) in enumerate(zip(definition, args))
                )

    return __make__


class SumTypeProperty:
    def __init__(self, parent_dict, name):
        self.parent_dict = parent_dict
        self.name = name
        self.definition = None

    def __call__(self, *definition):
        self.definition = definition
        key = self.name.split(".")[1]
        self.parent_dict[key] = make_constructor(self.name, definition)

    def __repr__(self):
        return f"<:{self.name} :: {self.definition}>"


class SumTypeDict(dict):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __missing__(self, key):
        if key[0].isupper():
            new_property = SumTypeProperty(self, self.name + "." + key)
            self["__adt_props__"][key] = new_property
            return new_property
        else:
            raise KeyError(key)


class SumTypeMeta(type):
    def __prepare__(name, *args, **kwargs):
        dict_ = SumTypeDict(name)
        adt_props = dict_["__adt_props__"] = {}
        return dict_

    def __instancecheck__(self, instance):
        return (
            isinstance(instance, _EmbellishedBase)
            and instance._constructor_name.split(".")[0] == self.__name__
        )

    def __getattr__(cls, attr: str) -> Any:
        ...

    def __repr__(self):
        return f"{self.__name__} {self.__adt_props__}"


class SumType(metaclass=SumTypeMeta):
    def __iter__(self) -> Iterator[Any]:
        ...

    def __getitem__(self, index: int) -> Any:
        ...