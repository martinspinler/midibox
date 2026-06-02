from __future__ import annotations

from typing import Any, Callable, Optional, TypeVar


def clamp(val: int, lower: int, upper: int) -> int:
    return lower if val < lower else upper if val > upper else val


T = TypeVar('T')


class CheckedProp[T]:
    def __init__(self, name: str, default: T, validator: Callable[[Any, T], T], initial: Optional[T] = None) -> None:
        self.name: str = name
        self.validator = validator
        self.default = default
        self.initial = initial if initial is not None else default

        def getter(cph: Any) -> T:
            return getattr(cph, f'_{name}')
        def setter(cph: Any, val: T) -> None:
            return cph._on_checkedprop_change(self, val)

        self.prop = property(getter, setter)


class BoolProp(CheckedProp[bool]):
    def __init__(self, name: str, default: bool = False) -> None:
        def validator(s: Any, v: bool) -> bool:
            return True if v else False

        super().__init__(name, default, validator)


class IntProp(CheckedProp[int]):
    def __init__(self, name: str, default: int = 0, min: int = 0, max: int = 127) -> None:
        def validator(s: Any, v: int) -> int:
            return clamp(v, min, max)
        super().__init__(name, default, validator)


class UIntProp(IntProp):
    pass


class SIntProp(IntProp):
    def __init__(self, name: str) -> None:
        super().__init__(name, min=-64, max=63)


class UInt14Prop(IntProp):
    def __init__(self, name: str) -> None:
        super().__init__(name, max=16383)


class VirtualProp(CheckedProp):
    """UI prop with no register backing — excluded from C header by gen_regs.py."""
    pass
